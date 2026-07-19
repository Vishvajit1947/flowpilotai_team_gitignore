"""
Executive Agent

Handles:
1. Escalated submissions (low confidence from routing)
2. Executive-level strategic content (board reports, KPIs, strategy)
3. Unknown intent submissions

For escalations, provides context about why it was escalated and suggests manual review.
For executive content, generates strategic briefs and decision recommendations.
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

EXECUTIVE_SYSTEM_PROMPT = """You are an executive AI assistant serving C-suite and senior management.
Analyze the content and provide a strategic executive brief.

Context:
- Is this an escalation? {is_escalation}
- Original intent detected: {original_intent}
- Confidence score: {confidence_score:.2f}
- Routing reason: {routing_reason}

Return ONLY this JSON (no markdown):
{{
  "content_type": "<'strategic_report' | 'kpi_review' | 'market_analysis' | 'escalation' | 'board_update' | 'unknown'>",
  "executive_summary": "<3-5 sentence high-level summary suitable for C-suite>",
  "key_themes": ["<2-5 main themes or topics identified>"],
  "key_metrics": [
    {{"metric": "<metric name>", "value": "<value>", "context": "<what it means>"}}
  ],
  "strategic_implications": ["<2-4 strategic implications or risks>"],
  "recommended_decisions": {{
    "immediate": ["<actions needed within 24-48 hours>"],
    "short_term": ["<actions needed within 1-4 weeks>"],
    "long_term": ["<strategic initiatives for 1-6 months>"]
  }},
  "stakeholders": ["<relevant stakeholders to loop in, e.g. 'CFO', 'Board', 'Sales VP'>"],
  "escalation_context": {{
    "was_escalated": <boolean>,
    "escalation_reason": "<why this was escalated to you, or null if not escalated>",
    "recommended_handler": "<if escalated, suggest which team/person should handle: 'sales_team', 'support_team', 'finance_team', 'manual_review'>",
    "confidence_note": "<note about confidence level>"
  }},
  "action_items": ["<3-5 specific action items>"],
  "priority": "<'critical' | 'high' | 'medium' | 'low'>",
  "summary": "<2-3 sentence internal summary>",
  "confidence": <float 0.0-1.0>
}}"""


async def executive_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: Process an executive-level or escalated submission."""
    content = state.get("content", "")
    file_text = state.get("file_text")
    is_escalation = state.get("escalated", False)
    original_intent = state.get("detected_intent") or "unknown"
    confidence_score = state.get("confidence_score", 0.0) or 0.0
    routing_reason = state.get("routing_reason") or ""

    full_text = content
    if file_text:
        full_text = f"{content}\n\n--- Document Content ---\n{file_text}"

    logger.info(
        "executive_agent_start",
        submission_id=state.get("submission_id"),
        is_escalation=is_escalation,
        original_intent=original_intent,
    )

    try:
        raw_result = await _generate_executive_brief(
            full_text, is_escalation, original_intent, confidence_score, routing_reason
        )
        response = _build_response(raw_result, is_escalation)

        logger.info(
            "executive_agent_complete",
            submission_id=state.get("submission_id"),
            content_type=raw_result.get("content_type"),
            priority=raw_result.get("priority"),
            was_escalated=is_escalation,
        )

        return {
            "agent_response": response.to_dict(),
            **add_step(state, "executive_agent_node", {
                "content_type": raw_result.get("content_type"),
                "priority": raw_result.get("priority"),
                "is_escalation": is_escalation,
            }),
        }

    except Exception as exc:
        logger.error("executive_agent_error", submission_id=state.get("submission_id"), error=str(exc))
        return {
            "agent_error": f"Executive agent error: {str(exc)}",
            **add_step(state, "executive_agent_node", {}, error=str(exc)),
        }


class ChatOpenAI:
    def __new__(cls, *args, **kwargs):
        from app.services.llm import get_llm
        temp = kwargs.get("temperature", 0.1)
        response_format_json = False
        if "model_kwargs" in kwargs and kwargs["model_kwargs"].get("response_format", {}).get("type") == "json_object":
            response_format_json = True
        return get_llm(temperature=temp, response_format_json=response_format_json)


async def _generate_executive_brief(
    text: str,
    is_escalation: bool,
    original_intent: str,
    confidence_score: float,
    routing_reason: str,
) -> dict[str, Any]:
    is_mock = settings.is_mock_mode
    if is_mock:
        text_lower = text.lower()
        if "gross profit" in text_lower or "net profit" in text_lower or "difference between" in text_lower:
            return {
                "content_type": "Financial Query Analysis",
                "executive_summary": "Analysis of the distinction between Gross Profit and Net Profit. Gross Profit represents revenue minus Cost of Goods Sold (COGS), representing manufacturing efficiency. Net Profit (bottom line) is the final profit after deducting all operating expenses, interest, taxes, and other overheads.",
                "key_themes": ["Gross Margin", "Net Margin", "Operational Overhead", "Taxes & Interest"],
                "key_metrics": [
                    {"metric": "Gross Profit formula", "value": "Revenue - COGS"},
                    {"metric": "Net Profit formula", "value": "Gross Profit - All Expenses"},
                    {"metric": "Gross Margin focus", "value": "Direct cost control"},
                    {"metric": "Net Margin focus", "value": "Overhead optimization"}
                ],
                "strategic_implications": [
                    "High gross margin but low net margin indicates high fixed operational expenses or debt servicing costs.",
                    "Pricing strategy directly influences gross profit, whereas administrative efficiency determines net profit."
                ],
                "recommended_decisions": {
                    "immediate": ["Structure cost allocations by separating COGS and SG&A in bookkeeping"],
                    "short_term": ["Audit administrative and operational overhead"],
                    "long_term": ["Establish fixed margin thresholds for new pricing tiers"]
                },
                "action_items": [
                    "Perform comparative margin analysis",
                    "Audit operating expenses for redundancies",
                    "Update budget projections for next quarter"
                ],
                "priority": "medium",
                "confidence": 0.95
            }
        
        # Fallback to general dynamic parser
        clean_text = text.strip()
        summary_topic = clean_text[:60] + "..." if len(clean_text) > 60 else clean_text
        return {
            "content_type": "Ad-hoc Request Review",
            "executive_summary": f"Audit of the query: '{summary_topic}'. Under mock mode, this request was routed to the Executive Agent for audit. The system simulated intent classification and returned structured recommendations based on this query.",
            "key_themes": ["Mock Processing", "Routing Audit", "System Simulation"],
            "key_metrics": [
                {"metric": "Query Length", "value": f"{len(text)} chars"},
                {"metric": "Route Status", "value": "Audited"},
                {"metric": "Execution Mode", "value": "Mock API"}
            ],
            "strategic_implications": [
                "Deploying a production API key will replace this simulated output with live LLM intelligence.",
                "Verify system routing rules if this topic should have matched customer_support, sales_lead, or invoice_processing."
            ],
            "recommended_decisions": {
                "immediate": ["Upgrade system with a live OpenAI API key"],
                "short_term": ["Evaluate custom system prompts"],
                "long_term": ["Integrate Redis caching layer"]
            },
            "action_items": [
                "Insert OpenAI API key in Render settings",
                "Add test cases for custom user prompts",
                "Evaluate custom system prompts under live conditions"
            ],
            "priority": "low",
            "confidence": 0.9
        }

    llm: Any = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        openai_api_key=settings.OPENAI_API_KEY,  # type: ignore[call-arg]
        request_timeout=90,  # type: ignore[call-arg]
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    truncated = text[:7000]
    system = EXECUTIVE_SYSTEM_PROMPT.format(
        is_escalation=str(is_escalation),
        original_intent=original_intent,
        confidence_score=confidence_score,
        routing_reason=routing_reason or "Normal routing",
    )
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Analyze and brief this content:\n\n{truncated}"),
    ]
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=90.0)

    raw = response.content
    if not isinstance(raw, str):
        
        raw = str(raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_response(is_escalation, original_intent)


def _build_response(data: dict[str, Any], is_escalation: bool) -> AgentResponse:
    valid_priorities = {"critical", "high", "medium", "low"}
    priority = data.get("priority", "medium")
    if priority not in valid_priorities:
        priority = "medium"

    recommended_decisions = data.get("recommended_decisions", {})
    if not isinstance(recommended_decisions, dict):
        recommended_decisions = {}

    action_items = data.get("action_items", [])
    if not isinstance(action_items, list):
        action_items = []

    escalation_context = data.get("escalation_context", {})
    if not isinstance(escalation_context, dict):
        escalation_context = {}

    confidence = float(data.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    return AgentResponse(
        agent_type=AgentType.executive,
        summary=data.get("summary", "Executive brief generated."),
        structured_data={
            "content_type": data.get("content_type", "unknown"),
            "executive_summary": data.get("executive_summary", ""),
            "key_themes": data.get("key_themes", []),
            "key_metrics": data.get("key_metrics", []),
            "strategic_implications": data.get("strategic_implications", []),
            "recommended_decisions": {
                "immediate": recommended_decisions.get("immediate", []),
                "short_term": recommended_decisions.get("short_term", []),
                "long_term": recommended_decisions.get("long_term", []),
            },
            "stakeholders": data.get("stakeholders", []),
            "escalation_context": escalation_context,
            "priority": priority,
        },
        action_items=action_items[:5],
        confidence=confidence,
        metadata={"is_escalation": is_escalation, "priority": priority},
    )


def _fallback_response(is_escalation: bool, original_intent: str) -> dict[str, Any]:
    return {
        "content_type": "escalation" if is_escalation else "unknown",
        "executive_summary": "Content received for executive review. Automated analysis unavailable.",
        "key_themes": [],
        "key_metrics": [],
        "strategic_implications": [],
        "recommended_decisions": {"immediate": ["Manual review required"], "short_term": [], "long_term": []},
        "stakeholders": [],
        "escalation_context": {
            "was_escalated": is_escalation,
            "escalation_reason": f"Originally detected as {original_intent}" if is_escalation else None,
            "recommended_handler": "manual_review",
            "confidence_note": "Automated analysis failed",
        },
        "action_items": ["Manually review this submission"],
        "priority": "medium",
        "summary": "Executive agent fallback — manual review required.",
        "confidence": 0.2,
    }
