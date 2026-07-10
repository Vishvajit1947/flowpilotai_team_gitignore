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
    """Detect intent using intent service (caching/LLM fallback)."""
    text = state.get("file_text") or state.get("content")
    try:
        decision = await detect_intent(text)
        return {
            "detected_intent": decision.intent,
            **add_step(
                state,
                "intent_node",
                {"intent": decision.intent, "reasoning": decision.reasoning, "from_cache": decision.from_cache},
            ),
        }
    except Exception as exc:
        logger.error("intent_node_failed", error=str(exc))
        return {
            "detected_intent": "unknown",
            **add_step(state, "intent_node", {"intent": "unknown"}, error=str(exc)),
        }


async def confidence_node(state: AgentState) -> dict[str, Any]:
    """Calculate confidence score of submission."""
    text = state.get("file_text") or state.get("content")
    intent = state.get("detected_intent") or "unknown"
    try:
        decision = await compute_confidence(text, intent)
        return {
            "confidence_score": decision.score,
            **add_step(
                state,
                "confidence_node",
                {"score": decision.score, "reasoning": decision.reasoning, "from_cache": decision.from_cache},
            ),
        }
    except Exception as exc:
        logger.error("confidence_node_failed", error=str(exc))
        return {
            "confidence_score": 0.0,
            **add_step(state, "confidence_node", {"score": 0.0}, error=str(exc)),
        }


async def router_node(state: AgentState) -> dict[str, Any]:
    """Determine the correct agent path and whether escalation is needed."""
    intent = state.get("detected_intent") or "unknown"
    score = state.get("confidence_score") or 0.0
    try:
        decision = route(intent, score)
        return {
            "assigned_agent": decision.agent,
            "escalated": decision.escalated,
            **add_step(
                state,
                "router_node",
                {"agent": decision.agent.value if decision.agent else None, "escalated": decision.escalated},
            ),
        }
    except Exception as exc:
        logger.error("router_node_failed", error=str(exc))
        # Default fallback is executive agent
        return {
            "assigned_agent": AgentType.executive,
            "escalated": True,
            **add_step(
                state,
                "router_node",
                {"agent": "executive", "escalated": True},
                error=str(exc),
            ),
        }


async def persist_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    """Write intermediate and final results to database."""
    submission_id = state.get("submission_id")
    if not submission_id:
        return {}

    try:
        from sqlalchemy import select
        res = await db.execute(
            select(InboxSubmission).where(InboxSubmission.id == submission_id)
        )
        submission = res.scalar_one()

        # Update metadata fields
        submission.detected_intent = state.get("detected_intent")
        submission.confidence_score = state.get("confidence_score")
        submission.assigned_agent = state.get("assigned_agent")
        submission.error_message = state.get("error_message")

        # Determine status
        agent_resp = state.get("agent_response")
        if agent_resp:
            # If agent response is present, mark as completed
            final_status = WorkflowStatus.completed
        elif state.get("error_message"):
            final_status = WorkflowStatus.failed
        else:
            final_status = WorkflowStatus.processing

        submission.status = final_status
        submission.result = state_to_result(state)

        await db.commit()
        logger.info(
            "workflow_persisted",
            submission_id=submission_id,
            status=final_status,
        )

        return {
            "final_status": final_status,
            **add_step(state, "persist_node", {"final_status": final_status.value}),
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

def build_workflow_graph(db: AsyncSession) -> Any:
    """
    Build and compile the LangGraph workflow.
    `db` is passed via closure to the persist_node.
    """
    graph: Any = StateGraph(AgentState)

    # Add nodes
    graph.add_node("ocr_node", ocr_node)
    graph.add_node("intent_node", intent_node)
    graph.add_node("confidence_node", confidence_node)
    graph.add_node("router_node", router_node)
    graph.add_node("sales_node", sales_agent_node)
    graph.add_node("support_node", support_agent_node)
    graph.add_node("finance_node", finance_agent_node)
    graph.add_node("executive_node", executive_agent_node)
    async def _persist(s: AgentState) -> dict[str, Any]:
        return await persist_node(s, db)

    graph.add_node("persist_node", _persist)

    def ocr_check_node(s: AgentState) -> dict[str, Any]:
        return {}

    # Entry point
    graph.set_entry_point("ocr_check")
    graph.add_node("ocr_check", ocr_check_node)

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
