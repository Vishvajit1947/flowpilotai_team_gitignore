# 025 – LangGraph Workflow

## Objective
Build the complete LangGraph state graph that orchestrates the full AI processing pipeline: OCR extraction → intent detection → confidence scoring → agent routing → specialized agent execution → database persistence. This is the core workflow engine of FlowPilot AI.

## Scope
- `app/agents/workflow.py` — LangGraph `StateGraph` definition and execution function
- All nodes: `ocr_node`, `intent_node`, `confidence_node`, `router_node`, agent dispatch, `persist_node`
- Conditional edges for agent routing
- Error handling and fallback paths
- `run_inbox_workflow()` public API called by background task (016)

## Out of Scope
- Individual agent implementations (021–024)
- Individual service implementations (017–019)
- OCR service implementation (027)
- Database schema (004)

## Functional Requirements
1. Graph accepts an `InboxSubmission` ORM object and a DB session.
2. Graph executes all nodes in order, passing `AgentState` through.
3. If submission has a `file_url`, OCR node extracts text before intent detection.
4. After routing, the correct agent node is selected via conditional edge.
5. After agent execution, `persist_node` updates the DB record.
6. On any unhandled exception, status is set to `failed`.
7. Full workflow completes in under 60 seconds under normal conditions.

## Technical Requirements
- `langgraph` 0.1.14+
- `StateGraph` with `AgentState` TypedDict
- Conditional edges using `should_run_ocr` and `select_agent` functions
- Each node returns a partial state dict (LangGraph merges automatically)
- All nodes are `async`

## Folder Structure
```
backend/
└── app/
    └── agents/
        ├── state.py       # From 020
        ├── types.py       # From 020
        ├── sales_agent.py     # From 021
        ├── support_agent.py   # From 022
        ├── finance_agent.py   # From 023
        ├── executive_agent.py # From 024
        └── workflow.py        # THIS FILE
```

## Files To Create

### `app/agents/workflow.py`
```python
"""
LangGraph Workflow for FlowPilot AI

Pipeline:
  START → [ocr?] → intent → confidence → router → [agent] → persist → END

Nodes:
  ocr_node:         Extract text from uploaded file (conditional — only if file_url set)
  intent_node:      Detect intent using GPT-4o (017)
  confidence_node:  Score confidence (018)
  router_node:      Route to appropriate agent (019)
  sales_node:       Sales agent (021)
  support_node:     Support agent (022)
  finance_node:     Finance agent (023)
  executive_node:   Executive agent (024)
  persist_node:     Write results to DB
"""
import structlog
from typing import Any, Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState, initial_state, state_to_result, add_step
from app.agents.sales_agent import sales_agent_node
from app.agents.support_agent import support_agent_node
from app.agents.finance_agent import finance_agent_node
from app.agents.executive_agent import executive_agent_node
from app.db.models.inbox import InboxSubmission, WorkflowStatus, AgentType
from app.services.intent_detection import detect_intent
from app.services.confidence_scoring import compute_confidence
from app.services.agent_router import route

logger = structlog.get_logger(__name__)


# ─── Node Functions ───────────────────────────────────────────────────────────

async def ocr_node(state: AgentState) -> dict[str, Any]:
    """Extract text from uploaded file using OCR service."""
    file_url = state.get("file_url")
    if not file_url:
        return {}  # No file — skip (guarded by conditional edge)

    try:
        from app.services.ocr_service import extract_text_from_url
        file_text = await extract_text_from_url(file_url)
        return {
            "file_text": file_text,
            **add_step(state, "ocr_node", {"chars_extracted": len(file_text)}),
        }
    except Exception as exc:
        logger.warning("ocr_node_failed", error=str(exc), file_url=file_url)
        # Non-fatal — workflow continues without file_text
        return {
            "file_text": None,
            **add_step(state, "ocr_node", {}, error=str(exc)),
        }


async def intent_node(state: AgentState) -> dict[str, Any]:
    """Detect intent from content."""
    content = state.get("content", "")
    file_text = state.get("file_text")

    try:
        result = await detect_intent(content, file_context=file_text)
        return {
            "detected_intent": result.intent,
            "intent_reasoning": result.reasoning,
            "intent_from_cache": result.from_cache,
            **add_step(state, "intent_node", {
                "intent": result.intent,
                "from_cache": result.from_cache,
            }),
        }
    except Exception as exc:
        logger.error("intent_node_failed", error=str(exc))
        return {
            "detected_intent": "unknown",
            "intent_reasoning": f"Error: {str(exc)}",
            "intent_from_cache": False,
            **add_step(state, "intent_node", {}, error=str(exc)),
        }


async def confidence_node(state: AgentState) -> dict[str, Any]:
    """Compute confidence score for detected intent."""
    content = state.get("content", "")
    intent = state.get("detected_intent", "unknown")
    file_text = state.get("file_text")

    try:
        score = await compute_confidence(content, intent, file_context=file_text)
        return {
            "confidence_score": score,
            **add_step(state, "confidence_node", {"score": score, "intent": intent}),
        }
    except Exception as exc:
        logger.error("confidence_node_failed", error=str(exc))
        return {
            "confidence_score": 0.5,
            **add_step(state, "confidence_node", {}, error=str(exc)),
        }


async def router_node(state: AgentState) -> dict[str, Any]:
    """Route to appropriate agent based on intent and confidence."""
    intent = state.get("detected_intent", "unknown")
    confidence = state.get("confidence_score", 0.5) or 0.5

    try:
        decision = route(intent, confidence)
        return {
            "assigned_agent": decision.agent_type,
            "escalated": decision.escalated,
            "routing_reason": decision.reason,
            "confidence_tier": decision.confidence_tier,
            **add_step(state, "router_node", {
                "agent": decision.agent_type.value,
                "escalated": decision.escalated,
                "tier": decision.confidence_tier,
            }),
        }
    except Exception as exc:
        logger.error("router_node_failed", error=str(exc))
        return {
            "assigned_agent": AgentType.executive,
            "escalated": True,
            "routing_reason": f"Routing error: {str(exc)}",
            "confidence_tier": "low",
            **add_step(state, "router_node", {}, error=str(exc)),
        }


async def persist_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    """Persist workflow results to the database."""
    from sqlalchemy import select
    import uuid as _uuid

    submission_id = state.get("submission_id")
    if not submission_id:
        return {"final_status": "failed", "error_message": "No submission_id in state"}

    try:
        result = await db.execute(
            select(InboxSubmission).where(
                InboxSubmission.id == _uuid.UUID(submission_id)
            )
        )
        submission = result.scalar_one()

        agent_error = state.get("agent_error")
        if agent_error:
            submission.status = WorkflowStatus.failed
            submission.error_message = agent_error
            final_status = "failed"
        else:
            submission.status = WorkflowStatus.completed
            submission.detected_intent = state.get("detected_intent")
            submission.confidence_score = state.get("confidence_score")
            submission.assigned_agent = state.get("assigned_agent")
            submission.result = state_to_result(state)
            submission.error_message = None
            final_status = "completed"

        await db.commit()
        logger.info(
            "workflow_persisted",
            submission_id=submission_id,
            status=final_status,
        )

        return {
            "final_status": final_status,
            **add_step(state, "persist_node", {"final_status": final_status}),
        }

    except Exception as exc:
        logger.error("persist_node_failed", submission_id=submission_id, error=str(exc))
        try:
            await db.rollback()
        except Exception:
            pass
        return {
            "final_status": "failed",
            "error_message": f"Persistence error: {str(exc)}",
        }


# ─── Conditional Edge Functions ───────────────────────────────────────────────

def should_run_ocr(state: AgentState) -> Literal["ocr_node", "intent_node"]:
    """Conditional: run OCR only if file_url is present."""
    if state.get("file_url"):
        return "ocr_node"
    return "intent_node"


def select_agent(state: AgentState) -> Literal["sales_node", "support_node", "finance_node", "executive_node"]:
    """Conditional: select agent node based on routing decision."""
    agent = state.get("assigned_agent")
    if agent == AgentType.sales:
        return "sales_node"
    if agent == AgentType.support:
        return "support_node"
    if agent == AgentType.finance:
        return "finance_node"
    return "executive_node"


# ─── Graph Construction ───────────────────────────────────────────────────────

def build_workflow_graph(db: AsyncSession) -> StateGraph:
    """
    Build and compile the LangGraph workflow.
    `db` is passed via closure to the persist_node.
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("ocr_node", ocr_node)
    graph.add_node("intent_node", intent_node)
    graph.add_node("confidence_node", confidence_node)
    graph.add_node("router_node", router_node)
    graph.add_node("sales_node", sales_agent_node)
    graph.add_node("support_node", support_agent_node)
    graph.add_node("finance_node", finance_agent_node)
    graph.add_node("executive_node", executive_agent_node)
    graph.add_node("persist_node", lambda s: persist_node(s, db))

    # Entry point
    graph.set_entry_point("ocr_check")
    graph.add_node("ocr_check", lambda s: {})  # passthrough node for conditional branch

    # Edges
    graph.add_conditional_edges(
        "ocr_check",
        should_run_ocr,
        {"ocr_node": "ocr_node", "intent_node": "intent_node"},
    )
    graph.add_edge("ocr_node", "intent_node")
    graph.add_edge("intent_node", "confidence_node")
    graph.add_edge("confidence_node", "router_node")
    graph.add_conditional_edges(
        "router_node",
        select_agent,
        {
            "sales_node": "sales_node",
            "support_node": "support_node",
            "finance_node": "finance_node",
            "executive_node": "executive_node",
        },
    )
    for agent_node_name in ("sales_node", "support_node", "finance_node", "executive_node"):
        graph.add_edge(agent_node_name, "persist_node")
    graph.add_edge("persist_node", END)

    return graph.compile()


# ─── Public API ───────────────────────────────────────────────────────────────

async def run_inbox_workflow(
    submission: InboxSubmission,
    db: AsyncSession,
) -> None:
    """
    Run the full AI workflow for a given InboxSubmission.
    Called by the background task in inbox.py (016).

    Updates submission status to 'processing' first, then runs the graph.
    """
    import uuid as _uuid

    # Mark as processing
    submission.status = WorkflowStatus.processing
    await db.commit()

    logger.info(
        "workflow_start",
        submission_id=str(submission.id),
        user_id=str(submission.user_id),
        has_file=bool(submission.file_url),
    )

    # Build initial state
    state = initial_state(
        submission_id=str(submission.id),
        user_id=str(submission.user_id),
        content=submission.content,
        file_url=submission.file_url,
    )

    # Execute graph
    try:
        workflow = build_workflow_graph(db)
        final_state = await workflow.ainvoke(state)
        logger.info(
            "workflow_complete",
            submission_id=str(submission.id),
            final_status=final_state.get("final_status"),
        )
    except Exception as exc:
        logger.error(
            "workflow_graph_error",
            submission_id=str(submission.id),
            error=str(exc),
        )
        # Last-resort: mark as failed
        from sqlalchemy import select
        try:
            res = await db.execute(
                select(InboxSubmission).where(InboxSubmission.id == submission.id)
            )
            sub = res.scalar_one()
            sub.status = WorkflowStatus.failed
            sub.error_message = f"Workflow error: {str(exc)}"
            await db.commit()
        except Exception:
            pass
```

## Existing Files To Modify
- `app/api/v1/endpoints/inbox.py` (016) — `_run_workflow` already imports `run_inbox_workflow`

## API Contracts
### `run_inbox_workflow(submission, db)`
```python
async def run_inbox_workflow(
    submission: InboxSubmission,
    db: AsyncSession,
) -> None:
    """Mutates submission via DB. No return value."""
```

## Request Examples
```python
# Called from background task in 016
from app.agents.workflow import run_inbox_workflow
await run_inbox_workflow(submission, db)
```

## Response Examples
After execution, the database row is updated:
```json
{
  "status": "completed",
  "detected_intent": "sales_lead",
  "confidence_score": 0.88,
  "assigned_agent": "sales",
  "result": {
    "agent_response": { "agent_type": "sales", "summary": "...", ... },
    "steps": [...]
  }
}
```

## Database Tables
**Reads and writes:** `inbox_submissions`
- Sets `status = 'processing'` at start
- Sets `status = 'completed'` or `'failed'` at end
- Updates `detected_intent`, `confidence_score`, `assigned_agent`, `result`, `error_message`

## Business Logic
1. Status transitions: `pending → processing → completed|failed`
2. OCR is optional and non-fatal — workflow continues without file_text if OCR fails.
3. All nodes are independent — a failure in one node falls back gracefully.
4. `persist_node` receives db via closure (not via state) since DB sessions are not JSON-serializable.
5. State `steps` accumulates an audit trail of all node executions.

## Validation Rules
- `submission_id` must be a valid UUID string.
- `final_status` must be `"completed"` or `"failed"`.

## Error Handling
| Scenario | Behavior |
|----------|----------|
| OCR fails | `file_text = None`, workflow continues |
| Intent detection fails | `detected_intent = "unknown"` |
| Confidence scoring fails | `confidence_score = 0.5` |
| Routing fails | Routes to executive agent |
| Agent fails | Sets `agent_error`, persist marks as failed |
| persist_node fails | Last-resort DB update in except block |
| Graph execution throws | Last-resort DB update marks as failed |

## UI Behavior
Not applicable — backend workflow.

## Component Breakdown
| Node | Responsibility |
|------|---------------|
| `ocr_check` | Conditional: run OCR or skip |
| `ocr_node` | Extract file text |
| `intent_node` | Classify intent |
| `confidence_node` | Score confidence |
| `router_node` | Select agent |
| `sales/support/finance/executive_node` | Generate AI response |
| `persist_node` | Write to DB |

## State Management
LangGraph manages state internally. See 020 for `AgentState` schema.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Submission with no content (empty string): intent = "unknown", confidence = 0.0, executive agent.
- Both content and file_url provided: both used for intent detection.
- Multiple concurrent workflows for same user: each has its own state + DB session.
- Very long OCR output (> 8000 chars): truncated within individual nodes.

## Test Cases
1. Submission with sales content → `assigned_agent = "sales"`, status = "completed".
2. Submission with low-confidence content → escalated to executive agent.
3. Submission with file_url → OCR node runs before intent_node.
4. OCR failure → workflow continues, `file_text = None`.
5. Agent failure → status = "failed", `error_message` set.
6. `steps` list has entries from all executed nodes.
7. DB status transitions: pending → processing → completed.
8. Concurrent workflows for same user don't interfere.

## Acceptance Criteria
- [ ] Full pipeline executes for all 4 agent types
- [ ] OCR conditional edge works correctly
- [ ] Agent routing conditional edge works for all agents
- [ ] DB updated with results after completion
- [ ] Status set to "failed" on any unrecoverable error
- [ ] Audit trail in `steps` captures all node executions

## Definition of Done
- All test cases pass
- No mypy errors
- `run_inbox_workflow` is the single public entry point
- Graph compiles without errors
