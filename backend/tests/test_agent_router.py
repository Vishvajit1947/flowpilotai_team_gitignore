import pytest
from app.db.models.inbox import AgentType
from app.services.agent_router import route, RoutingDecision


def test_route_sales_lead():
    # 1. route("sales_lead", 0.9) returns agent_type=sales, escalated=False
    decision = route("sales_lead", 0.9)
    assert decision.agent_type == AgentType.sales
    assert decision.escalated is False
    assert decision.original_intent == "sales_lead"
    assert decision.confidence_score == 0.9
    assert decision.confidence_tier == "high"


def test_route_customer_support():
    # 2. route("customer_support", 0.75) returns agent_type=support, escalated=False
    decision = route("customer_support", 0.75)
    assert decision.agent_type == AgentType.support
    assert decision.escalated is False
    assert decision.original_intent == "customer_support"
    assert decision.confidence_score == 0.75
    assert decision.confidence_tier == "medium"


def test_route_invoice_processing():
    # 3. route("invoice_processing", 0.85) returns agent_type=finance, escalated=False
    decision = route("invoice_processing", 0.85)
    assert decision.agent_type == AgentType.finance
    assert decision.escalated is False
    assert decision.original_intent == "invoice_processing"
    assert decision.confidence_score == 0.85
    assert decision.confidence_tier == "high"


def test_route_executive_summary():
    # 4. route("executive_summary", 0.65) returns agent_type=executive, escalated=False
    decision = route("executive_summary", 0.65)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is False
    assert decision.original_intent == "executive_summary"
    assert decision.confidence_score == 0.65
    assert decision.confidence_tier == "medium"


def test_route_unknown_intent():
    # 5. route("unknown", 0.0) returns agent_type=executive, escalated=False
    decision = route("unknown", 0.0)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is False
    assert decision.original_intent == "unknown"
    assert decision.confidence_score == 0.0
    assert decision.confidence_tier == "low"


def test_route_low_confidence_escalation():
    # 6. route("sales_lead", 0.3) returns agent_type=executive, escalated=True
    decision = route("sales_lead", 0.3)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is True
    assert decision.confidence_score == 0.3
    assert decision.confidence_tier == "low"


def test_route_boundary_escalated():
    # 7. route("sales_lead", 0.399) escalated=True
    decision = route("sales_lead", 0.399)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is True
    assert decision.confidence_score == 0.399


def test_route_boundary_not_escalated():
    # 8. route("sales_lead", 0.4) escalated=False
    decision = route("sales_lead", 0.4)
    assert decision.agent_type == AgentType.sales
    assert decision.escalated is False
    assert decision.confidence_score == 0.4
    assert decision.confidence_tier == "medium"


def test_route_bad_intent_fallback():
    # 9. route("bad_intent", 0.9) returns agent_type=executive (fallback)
    decision = route("bad_intent", 0.9)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is False
    assert decision.original_intent == "bad_intent"
    assert decision.confidence_score == 0.9
    assert decision.confidence_tier == "high"


def test_route_override_agent():
    # 10. route("sales_lead", 0.8, override_agent=AgentType.finance) returns agent_type=finance
    decision = route("sales_lead", 0.8, override_agent=AgentType.finance)
    assert decision.agent_type == AgentType.finance
    assert decision.escalated is False
    assert decision.original_intent == "sales_lead"
    assert decision.confidence_score == 0.8
    assert decision.confidence_tier == "high"


def test_confidence_tiers():
    # 11. confidence_tier returns "low", "medium", "high" at correct boundaries
    d_low = RoutingDecision(
        agent_type=AgentType.sales,
        escalated=False,
        original_intent="sales_lead",
        confidence_score=0.39,
        reason=""
    )
    assert d_low.confidence_tier == "low"

    d_medium = RoutingDecision(
        agent_type=AgentType.sales,
        escalated=False,
        original_intent="sales_lead",
        confidence_score=0.4,
        reason=""
    )
    assert d_medium.confidence_tier == "medium"

    d_medium2 = RoutingDecision(
        agent_type=AgentType.sales,
        escalated=False,
        original_intent="sales_lead",
        confidence_score=0.799,
        reason=""
    )
    assert d_medium2.confidence_tier == "medium"

    d_high = RoutingDecision(
        agent_type=AgentType.sales,
        escalated=False,
        original_intent="sales_lead",
        confidence_score=0.8,
        reason=""
    )
    assert d_high.confidence_tier == "high"


def test_confidence_clamping():
    # Test boundary clamping for out-of-range confidence scores
    d_over = route("sales_lead", 1.5)
    assert d_over.confidence_score == 1.0

    d_under = route("sales_lead", -0.5)
    assert d_under.confidence_score == 0.0
