# 019 – Agent Router

## Objective
Implement the agent router that maps detected intent and confidence score to the appropriate specialized agent, applies escalation rules for low-confidence submissions, and returns a routing decision including the selected agent type, whether to escalate, and routing metadata.

## Scope
- `app/services/agent_router.py` — routing logic
- Intent-to-agent mapping
- Confidence threshold rules (low < 0.4, medium 0.4–0.79, high ≥ 0.8)
- Escalation to executive agent for low confidence
- `RoutingDecision` dataclass
- Integration with LangGraph workflow (025)

## Out of Scope
- Agent implementations (021–024)
- LangGraph workflow (025)
- Intent detection (017)
- Confidence scoring (018)

## Functional Requirements
1. Accept `intent` (string) and `confidence_score` (float 0.0–1.0).
2. Map intent to agent: `sales_lead→sales`, `customer_support→support`, `invoice_processing→finance`, `executive_summary→executive`, `unknown→executive`.
3. If `confidence_score < 0.4`, override with `executive` agent and set `escalated=True`.
4. Return `RoutingDecision` with `agent_type`, `escalated`, `original_intent`, `reason`.
5. Routing must be deterministic (no randomness).
6. Log routing decisions with `structlog`.

## Technical Requirements
- Pure Python, no external dependencies
- `dataclasses` for `RoutingDecision`
- `structlog` for logging
- Type annotations throughout

## Folder Structure
```
backend/
└── app/
    └── services/
        └── agent_router.py
```

## Files To Create

### `app/services/agent_router.py`
```python
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
```

## Existing Files To Modify
None.

## API Contracts
Internal function — not an HTTP endpoint.

### Function Signature
```python
def route(
    intent: str,
    confidence_score: float,
    override_agent: Optional[AgentType] = None,
) -> RoutingDecision:
```

### RoutingDecision Fields
| Field | Type | Description |
|-------|------|-------------|
| `agent_type` | `AgentType` | Which agent handles this |
| `escalated` | `bool` | True if low-confidence escalation |
| `original_intent` | `str` | The intent from detection |
| `confidence_score` | `float` | Normalized [0, 1] |
| `reason` | `str` | Human-readable routing explanation |
| `confidence_tier` | `str` | "low", "medium", or "high" (property) |

## Request Examples
```python
from app.services.agent_router import route
from app.db.models.inbox import AgentType

# Normal high-confidence routing
decision = route("sales_lead", 0.92)
# decision.agent_type == AgentType.sales
# decision.escalated == False
# decision.confidence_tier == "high"

# Low confidence escalation
decision = route("invoice_processing", 0.25)
# decision.agent_type == AgentType.executive
# decision.escalated == True
# decision.confidence_tier == "low"

# Unknown intent
decision = route("unknown", 0.0)
# decision.agent_type == AgentType.executive
# decision.escalated == False
```

## Response Examples
```python
RoutingDecision(
    agent_type=<AgentType.sales>,
    escalated=False,
    original_intent="sales_lead",
    confidence_score=0.92,
    reason="High confidence (0.92) for 'sales_lead'. Routed to sales agent."
)
```

## Database Tables
Not applicable — pure routing logic.

## Business Logic
| Intent | Agent | Condition |
|--------|-------|-----------|
| `sales_lead` | `sales` | confidence ≥ 0.4 |
| `customer_support` | `support` | confidence ≥ 0.4 |
| `invoice_processing` | `finance` | confidence ≥ 0.4 |
| `executive_summary` | `executive` | confidence ≥ 0.4 |
| `unknown` | `executive` | always |
| Any | `executive` | confidence < 0.4 (escalated) |

## Validation Rules
- `confidence_score` clamped to [0.0, 1.0] before routing.
- Unknown `intent` strings not in `INTENT_TO_AGENT` map default to `executive`.

## Error Handling
| Scenario | Behavior |
|----------|----------|
| Intent not in mapping | Defaults to `executive` agent |
| Confidence out of range | Clamped before routing |
| `override_agent` provided | Uses override, no escalation check |

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
Stateless — pure function.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- `confidence_score = 0.4` exactly: NOT escalated (threshold is `< 0.4`).
- `confidence_score = 0.3999`: escalated.
- Intent `"sales_lead"` with `confidence_score = 0.1`: escalated to executive.
- `override_agent` bypasses all routing logic — used only for admin testing.

## Test Cases
1. `route("sales_lead", 0.9)` returns `agent_type=sales, escalated=False`.
2. `route("customer_support", 0.75)` returns `agent_type=support, escalated=False`.
3. `route("invoice_processing", 0.85)` returns `agent_type=finance, escalated=False`.
4. `route("executive_summary", 0.65)` returns `agent_type=executive, escalated=False`.
5. `route("unknown", 0.0)` returns `agent_type=executive, escalated=False`.
6. `route("sales_lead", 0.3)` returns `agent_type=executive, escalated=True`.
7. `route("sales_lead", 0.399)` escalated=True.
8. `route("sales_lead", 0.4)` escalated=False.
9. `route("bad_intent", 0.9)` returns `agent_type=executive` (fallback).
10. `route("sales_lead", 0.8, override_agent=AgentType.finance)` returns `agent_type=finance`.
11. `confidence_tier` returns "low", "medium", "high" at correct boundaries.

## Acceptance Criteria
- [ ] All 5 intent-to-agent mappings correct
- [ ] Low confidence (< 0.4) always routes to executive with `escalated=True`
- [ ] Unknown intent always routes to executive
- [ ] `override_agent` parameter bypasses normal routing
- [ ] `confidence_tier` property returns correct tier
- [ ] All routing decisions logged

## Definition of Done
- All test cases pass
- No mypy errors
- Thresholds defined as module constants (not magic numbers in conditions)
- Routing table is the single source of truth for intent→agent mapping
