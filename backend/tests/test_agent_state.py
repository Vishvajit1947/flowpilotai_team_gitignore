import operator
import pytest
from app.db.models.inbox import AgentType
from app.agents.types import AgentResponse, WorkflowStep
from app.agents.state import initial_state, add_step, state_to_result, AgentState


def test_initial_state():
    # 1. initial_state(...) creates state with all fields set.
    # 2. initial_state(...).get("detected_intent") returns None.
    state = initial_state(
        submission_id="550e8400-e29b-41d4-a716-446655440000",
        user_id="user-123",
        content="Hello world",
        file_url="http://example.com/file.pdf"
    )

    assert state["submission_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert state["user_id"] == "user-123"
    assert state["content"] == "Hello world"
    assert state["file_url"] == "http://example.com/file.pdf"

    # Defaults check
    assert state.get("file_text") is None
    assert state.get("detected_intent") is None
    assert state.get("intent_reasoning") is None
    assert state.get("intent_from_cache") is False
    assert state.get("confidence_score") is None
    assert state.get("assigned_agent") is None
    assert state.get("escalated") is False
    assert state.get("routing_reason") is None
    assert state.get("confidence_tier") is None
    assert state.get("agent_response") is None
    assert state.get("agent_error") is None
    assert state.get("steps") == []
    assert state.get("final_status") is None
    assert state.get("error_message") is None


def test_add_step():
    # 3. add_step(state, "test_node", {}) returns {"steps": [dict]}
    state = initial_state("sub-id", "usr-id", "content")
    update = add_step(state, "test_node", {"some_key": "some_val"})

    assert "steps" in update
    assert len(update["steps"]) == 1
    
    step_dict = update["steps"][0]
    assert step_dict["step_name"] == "test_node"
    assert step_dict["status"] == "completed"
    assert step_dict["data"] == {"some_key": "some_val"}
    assert step_dict["error"] is None


def test_add_step_with_error():
    state = initial_state("sub-id", "usr-id", "content")
    update = add_step(state, "test_node", {}, error="Failed to call model")

    assert update["steps"][0]["status"] == "failed"
    assert update["steps"][0]["error"] == "Failed to call model"


def test_steps_reducer_operator_add():
    # 4. Multiple add_step calls accumulate in steps list via operator.add
    # We simulate LangGraph's list accumulation using operator.add reducer
    state_steps = []
    
    # Node 1 returns updates
    update1 = add_step(None, "node_1", {"data1": 1}) # type: ignore
    state_steps = operator.add(state_steps, update1["steps"])

    # Node 2 returns updates
    update2 = add_step(None, "node_2", {"data2": 2}) # type: ignore
    state_steps = operator.add(state_steps, update2["steps"])

    assert len(state_steps) == 2
    assert state_steps[0]["step_name"] == "node_1"
    assert state_steps[1]["step_name"] == "node_2"


def test_state_to_result_filters_fields():
    # 5. state_to_result(state) returns only public fields (no raw content)
    state = initial_state("sub-id", "usr-id", "content")
    state.update({
        "detected_intent": "sales_lead",
        "confidence_score": 0.85,
        "assigned_agent": AgentType.sales,
        "escalated": False,
        "routing_reason": "High confidence sales lead",
        "agent_response": {
            "summary": "Everything is good",
            "action_items": []
        },
        "steps": [{"step_name": "test"}]
    })

    result = state_to_result(state)

    # Excluded fields
    assert "submission_id" not in result
    assert "user_id" not in result
    assert "content" not in result
    assert "file_url" not in result

    # Included fields
    assert result["detected_intent"] == "sales_lead"
    assert result["confidence_score"] == 0.85
    assert result["assigned_agent"] == "sales"  # Enum value string
    assert result["escalated"] is False
    assert result["routing_reason"] == "High confidence sales lead"
    assert result["agent_response"] == {
        "summary": "Everything is good",
        "action_items": []
    }
    assert result["steps"] == [{"step_name": "test"}]


def test_state_to_result_with_none_assigned_agent():
    # 6. state_to_result with None assigned_agent returns "assigned_agent": None
    state = initial_state("sub-id", "usr-id", "content")
    result = state_to_result(state)
    assert result["assigned_agent"] is None


def test_dataclasses_to_dict():
    # 7. AgentResponse.to_dict() and WorkflowStep.to_dict() return JSON-serializable types
    response = AgentResponse(
        agent_type=AgentType.sales,
        summary="A summary paragraph.",
        structured_data={"val": 42},
        action_items=["item 1"],
        confidence=0.95
    )
    
    resp_dict = response.to_dict()
    assert resp_dict == {
        "agent_type": "sales",
        "summary": "A summary paragraph.",
        "structured_data": {"val": 42},
        "action_items": ["item 1"],
        "confidence": 0.95,
        "metadata": {}
    }

    step = WorkflowStep(
        step_name="router_node",
        status="completed",
        data={"route": "sales"},
        error=None
    )
    step_dict = step.to_dict()
    assert step_dict == {
        "step_name": "router_node",
        "status": "completed",
        "data": {"route": "sales"},
        "error": None
    }
