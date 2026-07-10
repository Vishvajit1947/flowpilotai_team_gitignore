# 024 – Executive Agent

## Objective
Implement the Executive Agent — a LangGraph node that handles escalated submissions (low confidence from other agents), executive-level strategic content (board reports, KPI summaries, market analysis), and unknown intent submissions. It generates a high-level executive brief with strategic recommendations.

## Scope
- `app/agents/executive_agent.py` — executive agent node function
- Executive brief generation: key themes, strategic implications, recommended decisions
- Escalation handling: explains why the submission was escalated
- Handles both high-confidence executive content and low-confidence escalations
- Priority classification for executive attention

## Out of Scope
- Other agents (021–023)
- LangGraph workflow (025)

## Functional Requirements
1. Detect whether submission is an escalation or genuine executive content.
2. For escalations: explain the original intent, confidence, and why it was escalated.
3. For executive content: extract themes, metrics, strategic recommendations.
4. Generate 3 priority levels for recommended decisions: `immediate`, `short_term`, `long_term`.
5. Identify key stakeholders who should be looped in.
6. Complete within 20 seconds.

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with `gpt-4o`
- `response_format={"type":"json_object"}`
- Access to `escalated` and `routing_reason` from state to contextualize processing

## Folder Structure
```
backend/
└── app/
    └── agents/
        └── executive_agent.py
```

## Files To Create

### `app/agents/executive_agent.py`
```python
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
from langchain_openai import ChatOpenAI
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
    original_intent = state.get("detected_intent", "unknown")
    confidence_score = state.get("confidence_score", 0.0) or 0.0
    routing_reason = state.get("routing_reason", "")

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


async def _generate_executive_brief(
    text: str,
    is_escalation: bool,
    original_intent: str,
    confidence_score: float,
    routing_reason: str,
) -> dict[str, Any]:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=20,
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
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=20.0)
    try:
        return json.loads(response.content)
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
```

## Existing Files To Modify
None.

## API Contracts
LangGraph node — not an HTTP endpoint.

## Request Examples
```python
# Escalation case (low confidence)
state = {
    "content": "can you help me understand the thingy",
    "escalated": True,
    "detected_intent": "sales_lead",
    "confidence_score": 0.2,
    "routing_reason": "Low confidence (0.20) for 'sales_lead'. Escalated to executive agent.",
}

# Genuine executive content
state = {
    "content": "Q3 Board Update: Revenue $12.4M (+18% YoY), Churn 2.3%, NPS 64. Key risk: enterprise churn in APAC.",
    "escalated": False,
    "detected_intent": "executive_summary",
    "confidence_score": 0.91,
}
```

## Response Examples
```json
{
  "agent_response": {
    "agent_type": "executive",
    "structured_data": {
      "content_type": "kpi_review",
      "priority": "high",
      "key_metrics": [
        {"metric": "Revenue", "value": "$12.4M", "context": "+18% YoY growth"},
        {"metric": "Churn", "value": "2.3%", "context": "Within acceptable range"},
        {"metric": "NPS", "value": "64", "context": "Strong customer satisfaction"}
      ],
      "recommended_decisions": {
        "immediate": ["Address APAC enterprise churn risk"],
        "short_term": ["Review APAC customer success coverage"],
        "long_term": ["Expand APAC CS team"]
      }
    }
  }
}
```

## Database Tables
No direct DB interaction.

## Business Logic
- Escalated submissions: GPT-4o is told this is an escalation and told the original intent + confidence. It generates an escalation brief with recommended_handler.
- Temperature `0.2` (slightly higher than finance/intent) for richer strategic narrative.
- `recommended_decisions` split into 3 time horizons for executive action planning.

## Validation Rules
- `priority` must be `"critical"`, `"high"`, `"medium"`, or `"low"`.
- `recommended_decisions` must be a dict with three keys.
- `confidence` clamped to [0.0, 1.0].

## Error Handling
| Scenario | Behavior |
|----------|----------|
| GPT-4o timeout | `_fallback_response(is_escalation, original_intent)` |
| JSON parse failure | `_fallback_response()` |
| Invalid priority | Defaults to `"medium"` |

## Test Cases
1. Escalated submission → `escalation_context.was_escalated = True`.
2. Board update → `content_type = "board_update"`, priority ≥ "high".
3. KPI review → `key_metrics` list populated.
4. Low confidence escalation → `recommended_handler` is set.
5. Fallback on timeout → minimal data, `"manual_review"` recommended_handler.
6. `recommended_decisions` has all 3 keys.

## Acceptance Criteria
- [ ] Escalated submissions include escalation context
- [ ] Executive content generates strategic brief with metrics
- [ ] Three-horizon decision framework populated
- [ ] `priority` classification correct
- [ ] Fallback on failure

## Definition of Done
- All test cases pass
- No mypy errors
- System prompt tested with board updates, KPI reviews, and escalated low-confidence submissions
