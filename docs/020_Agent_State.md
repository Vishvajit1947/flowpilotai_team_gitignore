# 020 – Agent State

## Objective
Define the shared LangGraph state schema used by all agents in the FlowPilot AI workflow. This state object is passed between nodes in the graph and carries all information from initial submission through intent detection, routing, and final agent response.

## Scope
- `app/agents/state.py` — `AgentState` TypedDict definition
- `app/agents/types.py` — shared agent enums and response models
- State evolution diagram (fields added at each workflow stage)
- Reducer functions for state merging

## Out of Scope
- Graph construction (025)
- Individual agent implementations (021–024)
- Database persistence (handled in workflow 025)

## Functional Requirements
1. `AgentState` must carry all data from submission through workflow completion.
2. State must be serializable (JSON-compatible types only).
3. Each workflow stage adds fields without modifying previous fields.
4. State must store the final agent response and any errors.
5. State must track processing steps for audit/debugging.

## Technical Requirements
- LangGraph `TypedDict` state
- Python `typing` module (TypedDict, Annotated, Optional, List, Dict, Any)
- LangGraph `operator.add` reducer for list accumulation
- All fields must have defaults to allow partial construction

## Folder Structure
```
backend/
└── app/
    └── agents/
        ├── __init__.py
        ├── state.py      # AgentState TypedDict
        └── types.py      # Shared types and response models
```

## Files To Create

### `app/agents/types.py`
```python
"""
Shared types for the FlowPilot AI agent system.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from app.db.models.inbox import AgentType, WorkflowStatus


@dataclass
class AgentResponse:
    """Structured response from any specialized agent."""
    agent_type: AgentType
    summary: str                         # One-paragraph human-readable summary
    structured_data: dict[str, Any]      # Agent-specific structured output
    action_items: list[str]              # Recommended next actions
    confidence: float                    # Agent's own confidence in its response
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "summary": self.summary,
            "structured_data": self.structured_data,
            "action_items": self.action_items,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowStep:
    """Record of a single step in the workflow execution."""
    step_name: str
    status: str           # "started" | "completed" | "failed"
    data: dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_name": self.step_name,
            "status": self.status,
            "data": self.data,
            "error": self.error,
        }
```

### `app/agents/state.py`
```python
"""
LangGraph Agent State

The AgentState TypedDict is the shared state object passed between
all nodes in the LangGraph workflow graph. Fields are added progressively
as the workflow executes.

State evolution:
  Submission →
    [intent_node] adds: detected_intent, intent_reasoning →
    [confidence_node] adds: confidence_score →
    [router_node] adds: assigned_agent, escalated, routing_reason →
    [agent_node] adds: agent_response, agent_error →
    [persist_node] updates DB
"""
import operator
from typing import Annotated, Any, Optional, TypedDict
from app.db.models.inbox import AgentType


class AgentState(TypedDict, total=False):
    """
    Shared state for the FlowPilot AI LangGraph workflow.
    All fields are optional (total=False) because state is built incrementally.
    """

    # ── Input (set at workflow start) ─────────────────────────────────────────
    submission_id: str           # UUID string of InboxSubmission
    user_id: str                 # UUID string of the user
    content: str                 # Original user text
    file_url: Optional[str]      # Supabase Storage URL (if file uploaded)
    file_text: Optional[str]     # OCR-extracted text from file

    # ── Intent Detection (set by intent_node) ─────────────────────────────────
    detected_intent: Optional[str]     # "sales_lead" | "customer_support" | etc.
    intent_reasoning: Optional[str]    # GPT-4o's one-sentence explanation
    intent_from_cache: bool            # True if result came from cache

    # ── Confidence Scoring (set by confidence_node) ───────────────────────────
    confidence_score: Optional[float]  # 0.0 – 1.0

    # ── Routing (set by router_node) ──────────────────────────────────────────
    assigned_agent: Optional[AgentType]
    escalated: bool
    routing_reason: Optional[str]
    confidence_tier: Optional[str]     # "low" | "medium" | "high"

    # ── Agent Response (set by the specific agent node) ───────────────────────
    agent_response: Optional[dict[str, Any]]   # AgentResponse.to_dict()
    agent_error: Optional[str]                  # Error message if agent failed

    # ── Audit Trail (accumulated across nodes using operator.add reducer) ─────
    steps: Annotated[list[dict[str, Any]], operator.add]

    # ── Final Status ──────────────────────────────────────────────────────────
    final_status: Optional[str]   # "completed" | "failed"
    error_message: Optional[str]  # Top-level error for failed workflows


# ─── State Builder Helpers ────────────────────────────────────────────────────

def initial_state(
    submission_id: str,
    user_id: str,
    content: str,
    file_url: Optional[str] = None,
) -> AgentState:
    """
    Construct the initial AgentState from a new submission.
    Only the input fields are set; all processing fields default to None/empty.
    """
    return AgentState(
        submission_id=submission_id,
        user_id=user_id,
        content=content,
        file_url=file_url,
        file_text=None,
        detected_intent=None,
        intent_reasoning=None,
        intent_from_cache=False,
        confidence_score=None,
        assigned_agent=None,
        escalated=False,
        routing_reason=None,
        confidence_tier=None,
        agent_response=None,
        agent_error=None,
        steps=[],
        final_status=None,
        error_message=None,
    )


def add_step(state: AgentState, step_name: str, data: dict[str, Any], error: Optional[str] = None) -> dict:
    """
    Return a state update dict that appends a step to the audit trail.
    Usage: return { **add_step(state, "intent_node", {...}), "detected_intent": "sales_lead" }
    """
    from app.agents.types import WorkflowStep
    step = WorkflowStep(
        step_name=step_name,
        status="failed" if error else "completed",
        data=data,
        error=error,
    )
    return {"steps": [step.to_dict()]}


def state_to_result(state: AgentState) -> dict[str, Any]:
    """
    Convert final AgentState to the JSON stored in inbox_submissions.result.
    """
    return {
        "detected_intent": state.get("detected_intent"),
        "confidence_score": state.get("confidence_score"),
        "assigned_agent": state.get("assigned_agent").value if state.get("assigned_agent") else None,
        "escalated": state.get("escalated", False),
        "routing_reason": state.get("routing_reason"),
        "agent_response": state.get("agent_response"),
        "steps": state.get("steps", []),
    }
```

## Existing Files To Modify
None.

## API Contracts
Internal state schema — not an HTTP endpoint.

## Request Examples
```python
from app.agents.state import initial_state, add_step

# Initialize
state = initial_state(
    submission_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="user-uuid",
    content="New enterprise lead from Acme Corp",
    file_url=None,
)

# After intent node
state.update({
    "detected_intent": "sales_lead",
    "intent_reasoning": "Message discusses a new enterprise prospect",
    **add_step(state, "intent_node", {"intent": "sales_lead"}),
})
```

## Response Examples
```python
# Final state
{
    "submission_id": "550e8400...",
    "user_id": "user-uuid...",
    "content": "New enterprise lead from Acme Corp...",
    "file_url": None,
    "file_text": None,
    "detected_intent": "sales_lead",
    "intent_reasoning": "Message discusses new enterprise prospect",
    "intent_from_cache": False,
    "confidence_score": 0.88,
    "assigned_agent": AgentType.sales,
    "escalated": False,
    "routing_reason": "High confidence (0.88) for 'sales_lead'.",
    "confidence_tier": "high",
    "agent_response": {
        "agent_type": "sales",
        "summary": "High-value enterprise lead...",
        "structured_data": {"company": "Acme Corp", "deal_size": "$500k"},
        "action_items": ["Schedule demo", "Send proposal"],
        "confidence": 0.92,
    },
    "steps": [
        {"step_name": "intent_node", "status": "completed", "data": {...}},
        {"step_name": "confidence_node", "status": "completed", "data": {...}},
        {"step_name": "router_node", "status": "completed", "data": {...}},
        {"step_name": "sales_agent_node", "status": "completed", "data": {...}},
    ],
    "final_status": "completed",
    "error_message": None,
}
```

## Database Tables
State is not persisted directly — workflow (025) extracts fields and updates `inbox_submissions`.

## Business Logic
1. `steps` field uses `operator.add` reducer — LangGraph merges lists by concatenation.
2. All non-list fields are last-write-wins (standard LangGraph behavior).
3. `state_to_result()` extracts only the public fields for DB storage (excludes raw content to save space).
4. `total=False` on TypedDict allows partial construction at each step.

## Validation Rules
- `submission_id` and `user_id` must be UUID strings.
- `confidence_score` should be in [0.0, 1.0] (enforced by confidence scoring service).
- `final_status` must be `"completed"` or `"failed"`.

## Error Handling
- If a node fails, it should set `agent_error` and `final_status = "failed"` and `error_message`.
- Partial state is acceptable — not all fields need to be set.

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
LangGraph manages state internally. Persistence is handled by the workflow (025).

## Loading States
Not applicable.

## Empty States
- `steps = []` on initial state — audit trail starts empty.

## Edge Cases
- Node updates must use dict returns (not mutating the input state) — LangGraph merges returned dicts.
- `operator.add` reducer for `steps` means each node appends by returning `{"steps": [new_step]}`.
- `assigned_agent` is an `AgentType` enum in-memory but stored as string in DB.
- Accessing `state.get("key")` is safer than `state["key"]` since all fields are optional.

## Test Cases
1. `initial_state(...)` creates state with all fields set.
2. `initial_state(...).get("detected_intent")` returns `None`.
3. `add_step(state, "test_node", {})` returns `{"steps": [dict]}`.
4. Multiple `add_step` calls accumulate in `steps` list via `operator.add`.
5. `state_to_result(state)` returns only public fields (no raw content).
6. `state_to_result` with `None` assigned_agent returns `"assigned_agent": None`.
7. `AgentResponse.to_dict()` returns all fields as JSON-serializable types.

## Acceptance Criteria
- [ ] `AgentState` TypedDict covers all workflow fields
- [ ] `initial_state()` initializes all fields with correct defaults
- [ ] `add_step()` helper appends to steps list correctly
- [ ] `state_to_result()` produces correct DB-ready dict
- [ ] `operator.add` reducer works with LangGraph state merging

## Definition of Done
- All test cases pass
- No mypy errors
- State schema matches all nodes' expected input/output fields
- `AgentResponse` and `WorkflowStep` dataclasses are JSON-serializable
