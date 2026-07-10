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
from __future__ import annotations
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


def add_step(state: AgentState, step_name: str, data: dict[str, Any], error: Optional[str] = None) -> dict[str, Any]:
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
    assigned_agent = state.get("assigned_agent")
    return {
        "detected_intent": state.get("detected_intent"),
        "confidence_score": state.get("confidence_score"),
        "assigned_agent": assigned_agent.value if assigned_agent else None,
        "escalated": state.get("escalated", False),
        "routing_reason": state.get("routing_reason"),
        "agent_response": state.get("agent_response"),
        "steps": state.get("steps", []),
    }
