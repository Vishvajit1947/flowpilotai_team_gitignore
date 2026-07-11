import uuid
from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, field_validator, model_validator
from app.db.models.inbox import AgentType, WorkflowStatus


class InboxSubmitRequest(BaseModel):
    content: str
    file_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_request(self) -> "InboxSubmitRequest":
        content_val = (self.content or "").strip()
        file_url_val = (self.file_url or "").strip()

        if not file_url_val and len(content_val) < 3:
            raise ValueError("Content must be at least 3 characters when no file is attached")
        
        if len(content_val) > 5000:
            raise ValueError("Content must be at most 5000 characters")

        if file_url_val:
            if not file_url_val.startswith("https://"):
                raise ValueError("file_url must be an HTTPS URL")
            if len(file_url_val) > 2048:
                raise ValueError("file_url must be at most 2048 characters")

        self.content = content_val
        self.file_url = file_url_val if file_url_val else None
        return self



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
