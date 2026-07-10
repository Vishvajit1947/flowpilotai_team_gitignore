from __future__ import annotations
import uuid
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    Float,
    Enum as SAEnum,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum

if TYPE_CHECKING:
    from app.db.models.user import User


class AgentType(str, enum.Enum):
    sales = "sales"
    support = "support"
    finance = "finance"
    executive = "executive"


class WorkflowStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class InboxSubmission(Base):
    __tablename__ = "inbox_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    detected_intent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    assigned_agent: Mapped[AgentType | None] = mapped_column(
        SAEnum(AgentType, name="agent_type"),
        nullable=True,
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus, name="workflow_status"),
        nullable=False,
        default=WorkflowStatus.pending,
        server_default="pending",
        index=True,
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="submissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InboxSubmission id={self.id} status={self.status}>"
