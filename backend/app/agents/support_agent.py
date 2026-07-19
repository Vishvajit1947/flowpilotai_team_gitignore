"""
Support Agent

Processes customer support submissions: bug reports, feature requests,
account issues, and general inquiries.
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

SUPPORT_SYSTEM_PROMPT = """You are an expert customer support AI for a SaaS platform.
Analyze the support message and classify, assess, and respond appropriately.

Return ONLY this JSON (no markdown):
{
  "issue_type": "<'bug' | 'feature_request' | 'account_issue' | 'billing' | 'general_inquiry'>",
  "severity": "<'critical' | 'high' | 'medium' | 'low'>",
  "product_area": "<affected area, e.g. 'authentication', 'dashboard', 'API', 'billing'>",
  "customer_impact": "<brief description of how this impacts the customer>",
  "root_cause_hypothesis": "<most likely cause based on available info>",
  "response_draft": "<professional, empathetic customer-facing response, 2-4 sentences>",
  "internal_notes": "<what the support team should investigate internally>",
  "action_items": ["<3-5 specific steps for the support team>"],
  "sla_recommendation": "<recommended response time, e.g. '1 hour', '4 hours', '24 hours', '3 business days'>",
  "escalate_to_engineering": <boolean>,
  "summary": "<2-3 sentence internal summary>",
  "confidence": <float 0.0-1.0>
}

Severity guide:
- critical: Service completely down, data loss, security breach
- high: Major feature broken, significant user impact, workaround difficult
- medium: Feature partially broken, workaround available
- low: Minor issue, cosmetic, or general question

SLA guide:
- critical: 1 hour
- high: 4 hours
- medium: 24 hours
- low: 3 business days"""


async def support_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: Process a customer support submission."""
    content = state.get("content", "")
    file_text = state.get("file_text")

    full_text = content
    if file_text:
        full_text = f"{content}\n\n--- Attached Document ---\n{file_text}"

    logger.info(
        "support_agent_start",
        submission_id=state.get("submission_id"),
        content_length=len(content),
    )

    try:
        raw_result = await _analyze_support_issue(full_text)
        response = _build_response(raw_result)

        logger.info(
            "support_agent_complete",
            submission_id=state.get("submission_id"),
            issue_type=raw_result.get("issue_type"),
            severity=raw_result.get("severity"),
        )

        return {
            "agent_response": response.to_dict(),
            **add_step(state, "support_agent_node", {
                "issue_type": raw_result.get("issue_type"),
                "severity": raw_result.get("severity"),
                "product_area": raw_result.get("product_area"),
            }),
        }

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error("support_agent_error", submission_id=state.get("submission_id"), error=str(exc), exc_type=type(exc).__name__, traceback=tb)
        return {
            "agent_error": f"Support agent error: {type(exc).__name__}: {str(exc)}",
            **add_step(state, "support_agent_node", {"traceback": tb}, error=str(exc)),
        }


class ChatOpenAI:
    def __new__(cls, *args, **kwargs):
        from app.services.llm import get_llm
        temp = kwargs.get("temperature", 0.1)
        response_format_json = False
        if "model_kwargs" in kwargs and kwargs["model_kwargs"].get("response_format", {}).get("type") == "json_object":
            response_format_json = True
        return get_llm(temperature=temp, response_format_json=response_format_json)


async def _analyze_support_issue(text: str) -> dict[str, Any]:
    is_mock = settings.is_mock_mode
    if is_mock:
        text_lower = text.lower()
        
        area = "general"
        if "login" in text_lower or "oauth" in text_lower or "auth" in text_lower or "sign-in" in text_lower:
            area = "authentication"
        elif "slow" in text_lower or "latency" in text_lower or "performance" in text_lower:
            area = "performance"
        elif "payment" in text_lower or "billing" in text_lower or "invoice" in text_lower:
            area = "billing"
            
        severity = "medium"
        if any(k in text_lower for k in ["broken", "crash", "blocking", "urgent", "critical", "down", "error"]):
            severity = "critical"
            
        issue_type = "bug" if any(k in text_lower for k in ["bug", "error", "broken", "crash", "issue"]) else "inquiry"
        
        return {
            "issue_type": issue_type,
            "severity": severity,
            "product_area": area,
            "customer_impact": "Disrupting client critical business workflows" if severity == "critical" else "Minor usability impact",
            "root_cause_hypothesis": f"Simulated issue analysis for {area} category in mock mode.",
            "response_draft": f"Thank you for contacting support. We have triaged this as a {severity} level {area} {issue_type}. Our engineering team is looking into this and will provide updates shortly.",
            "internal_notes": f"Verify {area} status logs for matching errors reported in query.",
            "action_items": [
                "Inspect callback server logs",
                "Trace system redirection routes",
                "Draft customer support update message"
            ],
            "sla_recommendation": "1 hour" if severity == "critical" else "24 hours",
            "escalate_to_engineering": severity == "critical",
            "summary": f"Mock support request related to {area} with {severity} severity: '{text[:60]}...'",
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
        SystemMessage(content=SUPPORT_SYSTEM_PROMPT),
        HumanMessage(content=f"Support request:\n\n{truncated}"),
    ]
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=90.0)

    raw = response.content
    if not isinstance(raw, str):
        raw = str(raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_response()


def _build_response(data: dict[str, Any]) -> AgentResponse:
    valid_severities = {"critical", "high", "medium", "low"}
    severity = data.get("severity", "medium")
    if severity not in valid_severities:
        severity = "medium"

    valid_types = {"bug", "feature_request", "account_issue", "billing", "general_inquiry"}
    issue_type = data.get("issue_type", "general_inquiry")
    if issue_type not in valid_types:
        issue_type = "general_inquiry"

    action_items = data.get("action_items", [])
    if not isinstance(action_items, list):
        action_items = [str(action_items)]

    confidence = float(data.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    return AgentResponse(
        agent_type=AgentType.support,
        summary=data.get("summary", "Support issue processed."),
        structured_data={
            "issue_type": issue_type,
            "severity": severity,
            "product_area": data.get("product_area", "Unknown"),
            "customer_impact": data.get("customer_impact", ""),
            "root_cause_hypothesis": data.get("root_cause_hypothesis", ""),
            "response_draft": data.get("response_draft", ""),
            "internal_notes": data.get("internal_notes", ""),
            "sla_recommendation": data.get("sla_recommendation", "24 hours"),
            "escalate_to_engineering": bool(data.get("escalate_to_engineering", False)),
        },
        action_items=action_items[:5],
        confidence=confidence,
        metadata={"severity": severity, "issue_type": issue_type},
    )


def _fallback_response() -> dict[str, Any]:
    return {
        "issue_type": "general_inquiry",
        "severity": "medium",
        "product_area": "Unknown",
        "customer_impact": "Unable to determine automatically",
        "root_cause_hypothesis": "Manual review required",
        "response_draft": "Thank you for reaching out. Our support team will review your request and get back to you shortly.",
        "internal_notes": "Automated analysis failed — manual triage required.",
        "action_items": ["Manually review submission", "Contact customer for clarification"],
        "content_type": "support",
        "sla_recommendation": "24 hours",
        "escalate_to_engineering": False,
        "summary": "Support request received. Manual review needed.",
        "confidence": 0.3,
    }
