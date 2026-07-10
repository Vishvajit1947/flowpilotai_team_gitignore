# 022 – Support Agent

## Objective
Implement the Support Agent — a LangGraph node that processes customer support submissions (bug reports, feature requests, complaints, account issues) using GPT-4o, classifies the issue, assesses severity, generates a response draft, and returns a structured `AgentResponse`.

## Scope
- `app/agents/support_agent.py` — support agent node function
- Issue classification: `bug`, `feature_request`, `account_issue`, `billing`, `general_inquiry`
- Severity assessment: `critical`, `high`, `medium`, `low`
- Response draft generation
- SLA recommendation based on severity

## Out of Scope
- Ticketing system integration (not in v1)
- Email sending
- Other agents (021, 023, 024)

## Functional Requirements
1. Classify issue type into one of 5 categories.
2. Assess severity level (critical/high/medium/low).
3. Generate a customer-facing response draft.
4. Recommend SLA target based on severity.
5. Extract affected product area and customer impact description.
6. Generate 3–5 internal action items for the support team.
7. Complete within 20 seconds.

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with `gpt-4o`
- `response_format={"type":"json_object"}`
- Async LangGraph node

## Folder Structure
```
backend/
└── app/
    └── agents/
        └── support_agent.py
```

## Files To Create

### `app/agents/support_agent.py`
```python
"""
Support Agent

Processes customer support submissions: bug reports, feature requests,
account issues, and general inquiries.
"""
import json
import asyncio
import structlog
from typing import Any
from langchain_openai import ChatOpenAI
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
        logger.error("support_agent_error", submission_id=state.get("submission_id"), error=str(exc))
        return {
            "agent_error": f"Support agent error: {str(exc)}",
            **add_step(state, "support_agent_node", {}, error=str(exc)),
        }


async def _analyze_support_issue(text: str) -> dict[str, Any]:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=20,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    truncated = text[:6000]
    messages = [
        SystemMessage(content=SUPPORT_SYSTEM_PROMPT),
        HumanMessage(content=f"Support request:\n\n{truncated}"),
    ]
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=20.0)
    try:
        return json.loads(response.content)
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
        "sla_recommendation": "24 hours",
        "escalate_to_engineering": False,
        "summary": "Support request received. Manual review needed.",
        "confidence": 0.3,
    }
```

## Existing Files To Modify
None.

## API Contracts
LangGraph node — not an HTTP endpoint.

## Request Examples
```python
state = {
    "submission_id": "uuid",
    "content": "Users can't log in since the deploy at 3pm. Error: 'Invalid JWT signature'. Affecting all enterprise accounts.",
}
result = await support_agent_node(state)
```

## Response Examples
```json
{
  "agent_response": {
    "agent_type": "support",
    "summary": "Critical authentication bug affecting all enterprise accounts since recent deploy.",
    "structured_data": {
      "issue_type": "bug",
      "severity": "critical",
      "product_area": "authentication",
      "sla_recommendation": "1 hour",
      "escalate_to_engineering": true
    },
    "action_items": [
      "Immediately roll back the 3pm deploy",
      "Check JWT signing key rotation logs",
      "Notify affected enterprise customers",
      "Create P0 incident ticket"
    ]
  }
}
```

## Database Tables
No direct DB interaction.

## Business Logic
- `escalate_to_engineering: true` on `critical` and `high` severity bugs.
- SLA follows severity guide; support team must respond within SLA window.
- `response_draft` is written to be sent directly to the customer (professional, empathetic).

## Validation Rules
- `severity` clamped to allowed values; defaults to `"medium"`.
- `issue_type` clamped to allowed values; defaults to `"general_inquiry"`.
- `confidence` clamped to [0.0, 1.0].

## Error Handling
| Scenario | Behavior |
|----------|----------|
| GPT-4o timeout | `_fallback_response()` |
| JSON parse failure | `_fallback_response()` |
| Invalid severity value | Defaults to `"medium"` |
| Exception in node | Sets `agent_error` |

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
Reads: `content`, `file_text`, `submission_id`
Writes: `agent_response`, `agent_error`, `steps`

## Loading States
Not applicable.

## Empty States
- No content: fallback response with `"manual review required"` notes.

## Edge Cases
- Bug described with stack trace in `file_text`: included in analysis via full_text concatenation.
- Feature request with high urgency language: classified as `feature_request`, not `bug`.
- Content in non-English: GPT-4o handles; response_draft generated in English.

## Test Cases
1. Authentication bug → `severity="critical"`, `escalate_to_engineering=True`.
2. Feature request → `issue_type="feature_request"`, `severity="low"` or `"medium"`.
3. Billing dispute → `issue_type="billing"`.
4. JSON parse failure → fallback response used.
5. `confidence` clamped to [0.0, 1.0].
6. `severity="catastrophic"` from GPT-4o → replaced with `"medium"`.
7. `steps` contains one entry after node execution.

## Acceptance Criteria
- [ ] Classifies all 5 issue types
- [ ] Severity assessment with SLA recommendation
- [ ] `response_draft` is customer-facing and professional
- [ ] `escalate_to_engineering` flag set correctly for critical/high bugs
- [ ] Fallback response on GPT-4o failure

## Definition of Done
- All test cases pass
- No mypy errors
- System prompt tested against bug reports, feature requests, and billing issues
