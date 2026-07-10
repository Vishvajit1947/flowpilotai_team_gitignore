import uuid
from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, field_validator
from app.db.models.inbox import AgentType, WorkflowStatus


class InboxSubmitRequest(BaseModel):
    content: str
    file_url: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Content must be at least 3 characters")
        if len(v) > 5000:
            raise ValueError("Content must be at most 5000 characters")
        return v

    @field_validator("file_url")
    @classmethod
    def validate_file_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("file_url must be an HTTPS URL")
        if len(v) > 2048:
            raise ValueError("file_url must be at most 2048 characters")
        return v


class InboxSubmissionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    file_url: Optional[str]
    detected_intent: Optional[str]
    confidence_score: Optional[float]
    assigned_agent: Optional[AgentType]
    status: WorkflowStatus
    result: Optional[dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedSubmissionsResponse(BaseModel):
    items: List[InboxSubmissionResponse]
    total: int
    page: int
    size: int
    pages: int
