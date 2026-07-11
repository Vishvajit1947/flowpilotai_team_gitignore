"""
Agent Router

Maps intent + confidence to the appropriate specialized agent.

Routing Rules:
  intent → agent mapping (primary routing)
  confidence < 0.4 → escalate to executive agent
  unknown intent → executive agent
"""
from dataclasses import dataclass
from typing import Optional
import structlog
from app.db.models.inbox import AgentType

logger = structlog.get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LOW_CONFIDENCE_THRESHOLD = 0.4
HIGH_CONFIDENCE_THRESHOLD = 0.8

INTENT_TO_AGENT: dict[str, AgentType] = {
    "sales_lead": AgentType.sales,
    "customer_support": AgentType.support,
    "invoice_processing": AgentType.finance,
    "executive_summary": AgentType.executive,
    "unknown": AgentType.executive,
}


# ─── Result ───────────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    agent_type: AgentType
    escalated: bool
    original_intent: str
    confidence_score: float
    reason: str

    @property
    def confidence_tier(self) -> str:
        if self.confidence_score < LOW_CONFIDENCE_THRESHOLD:
            return "low"
        if self.confidence_score < HIGH_CONFIDENCE_THRESHOLD:
            return "medium"
        return "high"


# ─── Router ───────────────────────────────────────────────────────────────────

def route(
    intent: str,
    confidence_score: float,
    override_agent: Optional[AgentType] = None,
) -> RoutingDecision:
    """
    Determine which agent should handle the submission.

    Args:
        intent:          Detected intent string
        confidence_score: Float in [0.0, 1.0]
        override_agent:  Optional manual override (admin use)

    Returns:
        RoutingDecision
    """
    confidence_score = max(0.0, min(1.0, confidence_score))

    # Manual override (admin feature)
    if override_agent is not None:
        decision = RoutingDecision(
            agent_type=override_agent,
            escalated=False,
            original_intent=intent,
            confidence_score=confidence_score,
            reason=f"Manual override to {override_agent.value} agent",
        )
        _log_decision(decision)
        return decision

    # Primary intent → agent mapping
    primary_agent = INTENT_TO_AGENT.get(intent, AgentType.executive)

    # Unknown intent always goes to executive
    if intent == "unknown":
        decision = RoutingDecision(
            agent_type=AgentType.executive,
            escalated=False,
            original_intent=intent,
            confidence_score=confidence_score,
            reason="Unknown intent routed to executive agent",
        )
        _log_decision(decision)
        return decision

    # Low confidence escalation
    if confidence_score < LOW_CONFIDENCE_THRESHOLD:
        decision = RoutingDecision(
            agent_type=AgentType.executive,
            escalated=True,
            original_intent=intent,
            confidence_score=confidence_score,
            reason=(
                f"Low confidence ({confidence_score:.2f}) for intent '{intent}'. "
                f"Escalated to executive agent for review."
            ),
        )
        _log_decision(decision)
        return decision

    # Normal routing
    reason_prefix = "high" if confidence_score >= HIGH_CONFIDENCE_THRESHOLD else "medium"
    decision = RoutingDecision(
        agent_type=primary_agent,
        escalated=False,
        original_intent=intent,
        confidence_score=confidence_score,
        reason=(
            f"{reason_prefix.capitalize()} confidence ({confidence_score:.2f}) "
            f"for '{intent}'. Routed to {primary_agent.value} agent."
        ),
    )
    _log_decision(decision)
    return decision


def _log_decision(decision: RoutingDecision) -> None:
    logger.info(
        "routing_decision",
        agent=decision.agent_type.value,
        intent=decision.original_intent,
        confidence=round(decision.confidence_score, 3),
        escalated=decision.escalated,
        tier=decision.confidence_tier,
        reason=decision.reason,
    )
