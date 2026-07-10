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
