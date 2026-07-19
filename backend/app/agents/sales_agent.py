"""
Sales Agent

Processes sales-related submissions: new leads, opportunities, pricing inquiries.
Extracts structured CRM data and generates action plans using GPT-4o.
"""
import json
import asyncio
import structlog
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState, add_step
from app.agents.types import AgentResponse
from app.core.config import settings
from app.db.models.inbox import AgentType

logger = structlog.get_logger(__name__)

SALES_SYSTEM_PROMPT = """You are an expert sales intelligence AI for a B2B SaaS company.
Analyze the given sales-related message and extract actionable CRM data.

Return ONLY this JSON structure (no markdown):
{
  "company_name": "<company name or 'Unknown'>",
  "contact_name": "<person's name or 'Unknown'>",
  "contact_email": "<email or null>",
  "deal_size_estimate": "<estimated deal value in USD as string, e.g. '$50,000' or 'Unknown'>",
  "product_interest": "<what product/service they're interested in>",
  "urgency": "<'hot' | 'warm' | 'cold'>",
  "lead_score": <integer 0-100>,
  "pain_points": ["<list of identified pain points>"],
  "action_items": ["<3-5 specific next actions to advance this deal>"],
  "summary": "<2-3 sentence summary of this opportunity>",
  "follow_up_timeline": "<recommended timeline, e.g. 'Within 24 hours'>",
  "confidence": <float 0.0-1.0>
}

Lead scoring guide:
- 80-100: Large deal ($100k+), decision maker involved, high urgency, clear budget
- 60-79: Medium deal, influencer contact, moderate urgency
- 40-59: Small deal or early stage, unclear budget
- 20-39: Low qualification, limited info
- 0-19: Poorly defined or unlikely to convert

Urgency guide:
- hot: Must respond within 24 hours (demo request, competitive situation, end of quarter)
- warm: Respond within 1 week (general interest, evaluation phase)
- cold: Respond within 1 month (early research, no timeline)"""


async def sales_agent_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Process a sales lead submission.

    Input state fields used:
        - content: User's text submission
        - file_text: Optional OCR text from document

    Output state fields added:
        - agent_response: AgentResponse.to_dict()
        - agent_error: str (if failed)
        - steps: appended with sales_agent step
    """
    content = state.get("content", "")
    file_text = state.get("file_text")

    full_text = content
    if file_text:
        full_text = f"{content}\n\n--- Attached Document ---\n{file_text}"

    logger.info(
        "sales_agent_start",
        submission_id=state.get("submission_id"),
        content_length=len(content),
    )

    try:
        raw_result = await _extract_sales_data(full_text)
        response = _build_response(raw_result)

        logger.info(
            "sales_agent_complete",
            submission_id=state.get("submission_id"),
            lead_score=raw_result.get("lead_score"),
            urgency=raw_result.get("urgency"),
        )

        return {
            "agent_response": response.to_dict(),
            **add_step(state, "sales_agent_node", {
                "lead_score": raw_result.get("lead_score"),
                "urgency": raw_result.get("urgency"),
                "company": raw_result.get("company_name"),
            }),
        }

    except Exception as exc:
        logger.error(
            "sales_agent_error",
            submission_id=state.get("submission_id"),
            error=str(exc),
        )
        return {
            "agent_error": f"Sales agent error: {str(exc)}",
            **add_step(state, "sales_agent_node", {}, error=str(exc)),
        }


class ChatOpenAI:
    def __new__(cls, *args, **kwargs):
        from app.services.llm import get_llm
        temp = kwargs.get("temperature", 0.1)
        response_format_json = False
        if "model_kwargs" in kwargs and kwargs["model_kwargs"].get("response_format", {}).get("type") == "json_object":
            response_format_json = True
        return get_llm(temperature=temp, response_format_json=response_format_json)


async def _extract_sales_data(text: str) -> dict[str, Any]:
    """Call GPT-4o to extract structured sales data."""
    is_mock = settings.is_mock_mode
    if is_mock:
        text_lower = text.lower()
        import re
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text_lower)
        email = email_match.group(0) if email_match else "sjenkins@acmecorp.com"
        
        company = "Acme Corporation"
        if "acme" in text_lower:
            company = "Acme Corporation"
        elif "globex" in text_lower:
            company = "Globex Corp"
        elif "hooli" in text_lower:
            company = "Hooli"
        elif "stark" in text_lower:
            company = "Stark Industries"
        elif "meta" in text_lower:
            company = "Meta Platforms"
        elif email_match:
            # guess company from email domain
            domain = email.split('@')[1].split('.')[0]
            company = domain.capitalize()
            
        name = "Sarah Jenkins"
        if email_match:
            parts = email.split('@')[0].split('.')
            if len(parts) >= 2:
                name = f"{parts[0].capitalize()} {parts[1].capitalize()}"
            else:
                name = parts[0].capitalize()
                
        return {
            "company_name": company,
            "contact_name": name,
            "contact_email": email,
            "deal_size_estimate": "$25,000" if "large" in text_lower or "enterprise" in text_lower or "licenses" in text_lower else "$5,000",
            "product_interest": "Developer License Subscription",
            "urgency": "hot" if "urgent" in text_lower or "soon" in text_lower or "asap" in text_lower else "medium",
            "lead_score": 90 if "buy" in text_lower or "pricing" in text_lower or "quote" in text_lower else 70,
            "pain_points": ["Looking for standard system capabilities", "Requires integration support"],
            "action_items": [
                f"Schedule a 30-minute product demonstration with {name}",
                f"Draft and send custom pricing proposal for {company}",
                "Log sales inquiry in CRM tracker"
            ],
            "summary": f"High-intent sales lead from {name} ({company}) requesting details.",
            "follow_up_timeline": "Within 24 hours",
            "confidence": 0.95
        }

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,  # type: ignore[call-arg]
        request_timeout=90,  # type: ignore[call-arg]
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    truncated = text[:6000]
    messages = [
        SystemMessage(content=SALES_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this sales message:\n\n{truncated}"),
    ]

    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=90.0)
    raw = response.content
    if not isinstance(raw, str):
        raw = str(raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("sales_json_parse_failed", raw=raw[:200])
        return _fallback_response(text)


def _build_response(data: dict[str, Any]) -> AgentResponse:
    """Convert raw GPT-4o output to AgentResponse."""
    lead_score = int(data.get("lead_score", 50))
    lead_score = max(0, min(100, lead_score))
    confidence = float(data.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    action_items = data.get("action_items", [])
    if not isinstance(action_items, list):
        action_items = [str(action_items)]

    return AgentResponse(
        agent_type=AgentType.sales,
        summary=data.get("summary", "Sales lead processed."),
        structured_data={
            "company_name": data.get("company_name", "Unknown"),
            "contact_name": data.get("contact_name", "Unknown"),
            "contact_email": data.get("contact_email"),
            "deal_size_estimate": data.get("deal_size_estimate", "Unknown"),
            "product_interest": data.get("product_interest", "Unknown"),
            "urgency": data.get("urgency", "warm"),
            "lead_score": lead_score,
            "pain_points": data.get("pain_points", []),
            "follow_up_timeline": data.get("follow_up_timeline", "Within 1 week"),
        },
        action_items=action_items[:5],
        confidence=confidence,
        metadata={"raw_lead_score": lead_score},
    )


def _fallback_response(text: str) -> dict[str, Any]:
    """Return minimal structured data when JSON parse fails."""
    return {
        "company_name": "Unknown",
        "contact_name": "Unknown",
        "contact_email": None,
        "deal_size_estimate": "Unknown",
        "product_interest": "Unknown",
        "urgency": "warm",
        "lead_score": 30,
        "pain_points": [],
        "action_items": ["Review submission manually", "Contact submitter for more details"],
        "summary": "Sales-related content detected. Manual review recommended.",
        "follow_up_timeline": "Within 1 week",
        "confidence": 0.3,
    }
