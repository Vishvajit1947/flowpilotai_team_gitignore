# 021 – Sales Agent

## Objective
Implement the Sales Agent — a LangGraph node that processes sales-related submissions (new leads, opportunities, pricing inquiries) using GPT-4o, extracts structured CRM data, generates a prioritized action plan, and returns a complete `AgentResponse`.

## Scope
- `app/agents/sales_agent.py` — sales agent node function
- Structured extraction: company name, contact, deal size, urgency, lead score
- Action item generation: demo scheduling, proposal triggers, follow-up timeline
- Lead scoring algorithm (0–100)
- Integration as a LangGraph node

## Out of Scope
- CRM API integration (not in v1)
- Email sending (not in v1)
- Other agents (022–024)

## Functional Requirements
1. Extract structured CRM data from submission content.
2. Score the lead from 0–100 based on extracted signals.
3. Generate 3–5 specific action items tailored to the lead.
4. Classify urgency: `hot` (respond < 24h), `warm` (< 1 week), `cold` (> 1 week).
5. Return `AgentResponse` with all extracted data in `structured_data`.
6. Complete processing within 20 seconds.

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with `gpt-4o`
- `response_format={"type":"json_object"}`
- Pydantic model for extracting structured output
- Async function compatible with LangGraph node signature

## Folder Structure
```
backend/
└── app/
    └── agents/
        └── sales_agent.py
```

## Files To Create

### `app/agents/sales_agent.py`
```python
"""
Sales Agent

Processes sales-related submissions: new leads, opportunities, pricing inquiries.
Extracts structured CRM data and generates action plans using GPT-4o.
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


async def _extract_sales_data(text: str) -> dict[str, Any]:
    """Call GPT-4o to extract structured sales data."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=20,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    truncated = text[:6000]
    messages = [
        SystemMessage(content=SALES_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this sales message:\n\n{truncated}"),
    ]

    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=20.0)
    raw = response.content

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
```

## Existing Files To Modify
None.

## API Contracts
LangGraph node — not an HTTP endpoint.

### Node Signature
```python
async def sales_agent_node(state: AgentState) -> dict[str, Any]:
    """Returns partial state update dict."""
```

### Structured Data Output Schema
```json
{
  "company_name": "Acme Corp",
  "contact_name": "John Smith",
  "contact_email": "john@acme.com",
  "deal_size_estimate": "$250,000",
  "product_interest": "Enterprise plan with SSO",
  "urgency": "hot",
  "lead_score": 87,
  "pain_points": ["Scaling issues", "No unified dashboard"],
  "follow_up_timeline": "Within 24 hours"
}
```

## Request Examples
```python
# Called by LangGraph workflow
state = {
    "submission_id": "uuid",
    "content": "We have a new enterprise lead from Acme Corp. John Smith, CTO, wants a demo next Tuesday. Deal potentially worth $250k.",
    "file_text": None,
}
result = await sales_agent_node(state)
```

## Response Examples
```python
{
    "agent_response": {
        "agent_type": "sales",
        "summary": "High-value enterprise lead from Acme Corp CTO requesting a demo, potential $250k deal.",
        "structured_data": {
            "company_name": "Acme Corp",
            "contact_name": "John Smith",
            "deal_size_estimate": "$250,000",
            "urgency": "hot",
            "lead_score": 87,
            ...
        },
        "action_items": [
            "Schedule demo for next Tuesday",
            "Send enterprise pricing proposal",
            "Create tailored demo environment",
            "Brief your SE team on Acme Corp's tech stack",
        ],
        "confidence": 0.92,
    },
    "steps": [{"step_name": "sales_agent_node", "status": "completed", ...}]
}
```

## Database Tables
No direct DB interaction — state is persisted by the workflow (025).

## Business Logic
- Lead score 80–100: `hot` urgency, requires same-day response
- Lead score 60–79: `warm`, respond within a week
- Lead score < 40: `cold`, standard follow-up timeline
- Action items capped at 5 to keep output focused
- GPT temperature `0.1` for slight creativity in action suggestions while maintaining consistency

## Validation Rules
- `lead_score`: clamped to [0, 100]
- `confidence`: clamped to [0.0, 1.0]
- `action_items`: list, max 5 items
- `urgency`: must be `"hot"`, `"warm"`, or `"cold"` — fallback to `"warm"` if invalid

## Error Handling
| Scenario | Behavior |
|----------|----------|
| GPT-4o timeout | Returns fallback response with `confidence=0.3` |
| JSON parse failure | Returns `_fallback_response()` |
| Missing fields in GPT-4o output | Defaults applied per field |
| Exception in node | Sets `agent_error`, appends failed step |

## UI Behavior
Not applicable — backend agent.

## Component Breakdown
Not applicable.

## State Management
Reads from `AgentState`: `content`, `file_text`, `submission_id`
Returns updates to: `agent_response`, `agent_error`, `steps`

## Loading States
Not applicable.

## Empty States
- Empty content: `_fallback_response()` handles it with default values.

## Edge Cases
- Content with no company name: `company_name = "Unknown"`.
- Multiple contacts mentioned: GPT-4o picks the most prominent.
- Deal size in non-USD currency: returned as-is in string format.
- No urgency signals: defaults to `"warm"`.
- `action_items` returned as string instead of list: coerced to single-item list.

## Test Cases
1. High-value lead with all details → `lead_score ≥ 75`, `urgency = "hot"`.
2. Vague inquiry with no budget → `lead_score < 40`.
3. JSON parse failure → `_fallback_response()` values returned.
4. GPT-4o timeout → `agent_error` set in state.
5. `lead_score = 150` from GPT-4o → clamped to 100.
6. `action_items` is a string → coerced to list.
7. Response has `agent_response.agent_type == "sales"`.
8. `steps` list has one entry after node execution.

## Acceptance Criteria
- [ ] Extracts company name, contact, deal size, urgency
- [ ] Lead score calculated and clamped to [0, 100]
- [ ] 3–5 action items generated
- [ ] Fallback response used on GPT-4o failure
- [ ] `agent_error` set on exception
- [ ] Compatible with LangGraph node signature

## Definition of Done
- All test cases pass (mock OpenAI in tests)
- No mypy errors
- System prompt tested against 5+ real sales message examples
