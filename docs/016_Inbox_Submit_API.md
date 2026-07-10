# 016 – Inbox Submit API

## Objective
Implement the `POST /api/v1/inbox/submit` endpoint that receives a user's text content and optional file URL, creates an `InboxSubmission` record in the database with status `pending`, queues it for async AI processing via the LangGraph workflow, and returns the submission immediately. Also implement `GET /api/v1/inbox/{id}` for status polling and `GET /api/v1/inbox/` for listing the user's submissions.

## Scope
- `POST /api/v1/inbox/submit` — create submission, trigger async workflow
- `GET /api/v1/inbox/{id}` — get single submission by ID
- `GET /api/v1/inbox/` — list current user's submissions (paginated)
- Background task trigger using FastAPI `BackgroundTasks`
- Submission ownership enforcement (users can only see their own)

## Out of Scope
- Workflow execution (025 LangGraph)
- Intent detection (017)
- Agent logic (021–024)
- Admin view of all submissions (034)

## Functional Requirements
1. `POST /submit` accepts `content` (string, 3–5000 chars) and `file_url` (optional URL string).
2. Creates `InboxSubmission` with status `pending` and returns 201 immediately.
3. Triggers background AI workflow without blocking the HTTP response.
4. `GET /{id}` returns 404 if submission doesn't exist or belongs to a different user.
5. `GET /` returns paginated list (default page=1, size=20, max size=100).
6. Users can only access their own submissions (enforced at DB query level).

## Technical Requirements
- FastAPI `BackgroundTasks` for async workflow trigger
- SQLAlchemy async queries
- Pydantic v2 response schemas
- Dependency: `get_current_active_user` from `app/api/deps.py`

## Folder Structure
```
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── endpoints/
    │           └── inbox.py          # All inbox routes
    └── schemas/
        └── inbox.py                   # Request + response schemas
```

## Files To Create

### `app/schemas/inbox.py`
```python
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
```

### `app/api/v1/endpoints/inbox.py`
```python
import math
import structlog
from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound

from app.api.deps import DBSession, CurrentUser
from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.models.inbox import InboxSubmission, WorkflowStatus
from app.schemas.inbox import (
    InboxSubmitRequest,
    InboxSubmissionResponse,
    PaginatedSubmissionsResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _run_workflow(submission_id: str, db_session_factory) -> None:
    """
    Background task: run LangGraph workflow for the given submission.
    Imports are deferred to avoid circular imports.
    """
    from app.agents.workflow import run_inbox_workflow
    from app.db.session import AsyncSessionLocal
    import uuid as _uuid

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(InboxSubmission).where(
                    InboxSubmission.id == _uuid.UUID(submission_id)
                )
            )
            submission = result.scalar_one()
            await run_inbox_workflow(submission, db)
        except Exception as exc:
            logger.error(
                "workflow_background_error",
                submission_id=submission_id,
                error=str(exc),
            )
            # Mark submission as failed
            try:
                async with AsyncSessionLocal() as db2:
                    res = await db2.execute(
                        select(InboxSubmission).where(
                            InboxSubmission.id == _uuid.UUID(submission_id)
                        )
                    )
                    sub = res.scalar_one()
                    sub.status = WorkflowStatus.failed
                    sub.error_message = f"Internal error: {str(exc)}"
                    await db2.commit()
            except Exception:
                pass


@router.post(
    "/submit",
    response_model=InboxSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit content for AI processing",
)
async def submit_inbox(
    body: InboxSubmitRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: CurrentUser,
) -> InboxSubmissionResponse:
    """
    Creates an InboxSubmission and immediately returns 201.
    AI workflow runs in the background.
    """
    submission = InboxSubmission(
        user_id=current_user.id,
        content=body.content,
        file_url=body.file_url,
        status=WorkflowStatus.pending,
    )
    db.add(submission)
    await db.flush()
    await db.refresh(submission)

    submission_id = str(submission.id)

    # Trigger async workflow AFTER commit (so DB row is visible to background task)
    background_tasks.add_task(_run_workflow, submission_id, None)

    logger.info(
        "submission_created",
        submission_id=submission_id,
        user_id=str(current_user.id),
    )

    return InboxSubmissionResponse.model_validate(submission)


@router.get(
    "/{submission_id}",
    response_model=InboxSubmissionResponse,
    summary="Get a submission by ID",
)
async def get_submission(
    submission_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> InboxSubmissionResponse:
    """
    Returns a single submission. Returns 404 if not found or not owned by user.
    """
    import uuid as _uuid

    try:
        uid = _uuid.UUID(submission_id)
    except ValueError:
        raise NotFoundError("Submission")

    result = await db.execute(
        select(InboxSubmission).where(InboxSubmission.id == uid)
    )
    submission = result.scalar_one_or_none()

    if submission is None:
        raise NotFoundError("Submission")

    if submission.user_id != current_user.id:
        # Return 404 instead of 403 to avoid ID enumeration
        raise NotFoundError("Submission")

    return InboxSubmissionResponse.model_validate(submission)


@router.get(
    "/",
    response_model=PaginatedSubmissionsResponse,
    summary="List current user's submissions",
)
async def list_submissions(
    db: DBSession,
    current_user: CurrentUser,
    page: int = 1,
    size: int = 20,
) -> PaginatedSubmissionsResponse:
    """
    Returns paginated list of submissions for the current user, newest first.
    """
    size = min(size, 100)  # Cap at 100
    page = max(page, 1)
    offset = (page - 1) * size

    # Total count
    count_result = await db.execute(
        select(func.count(InboxSubmission.id)).where(
            InboxSubmission.user_id == current_user.id
        )
    )
    total = count_result.scalar_one()

    # Paginated items
    items_result = await db.execute(
        select(InboxSubmission)
        .where(InboxSubmission.user_id == current_user.id)
        .order_by(InboxSubmission.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    items = items_result.scalars().all()

    return PaginatedSubmissionsResponse(
        items=[InboxSubmissionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 1,
    )
```

## Files To Modify

### `app/api/v1/router.py`
```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth, inbox

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
```

## API Contracts

### `POST /api/v1/inbox/submit`
```
Method:  POST
Path:    /api/v1/inbox/submit
Auth:    Bearer token (required)
Content-Type: application/json

Request:
{
  "content": "We have a new enterprise lead from Acme Corp worth $500k",
  "file_url": null
}

Response 201:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "content": "We have a new enterprise lead from Acme Corp worth $500k",
  "file_url": null,
  "detected_intent": null,
  "confidence_score": null,
  "assigned_agent": null,
  "status": "pending",
  "result": null,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### `GET /api/v1/inbox/{id}`
```
Method: GET
Auth:   Bearer token
Response 200: InboxSubmissionResponse
Response 404: { "detail": "Submission not found", "status_code": 404 }
```

### `GET /api/v1/inbox/?page=1&size=20`
```
Method: GET
Auth:   Bearer token
Response 200:
{
  "items": [...],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

## Request Examples
```bash
# Submit
curl -X POST http://localhost:8000/api/v1/inbox/submit \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"New lead from Acme Corp, $500k deal","file_url":null}'

# Poll status
curl http://localhost:8000/api/v1/inbox/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"

# List submissions
curl "http://localhost:8000/api/v1/inbox/?page=1&size=10" \
  -H "Authorization: Bearer <token>"
```

## Response Examples

**POST /submit — 201:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "content": "New lead from Acme Corp, $500k deal",
  "file_url": null,
  "detected_intent": null,
  "confidence_score": null,
  "assigned_agent": null,
  "result": null,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Database Tables
**Writes to:** `inbox_submissions`
- Creates row with `status = 'pending'`
- Background task updates `status`, `detected_intent`, `confidence_score`, `assigned_agent`, `result`, `error_message`

## Business Logic
1. The HTTP response returns immediately after DB write — no waiting for AI processing.
2. Background task opens its own DB session (not the request session, which closes after response).
3. If background task fails, status is set to `failed` with error message.
4. User can only see their own submissions — `user_id` filter on all queries.
5. Accessing another user's submission by ID returns 404 (not 403) to prevent ID enumeration.
6. Pagination size is capped at 100 to prevent large result sets.

## Validation Rules
| Field | Rule |
|-------|------|
| `content` | 3–5000 chars after strip |
| `file_url` | Must start with `https://` if provided |
| `file_url` | Max 2048 chars |
| `page` | Min 1 |
| `size` | Min 1, max 100 |

## Error Handling
| Scenario | Status |
|----------|--------|
| Content too short | 422 |
| Content too long | 422 |
| Invalid file_url | 422 |
| Submission not found | 404 |
| Submission owned by other user | 404 (not 403) |
| No auth token | 401 |
| Background task fails | Sets DB status to `failed` |

## UI Behavior
Not applicable — backend only.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
- `GET /` with no submissions returns `{"items":[],"total":0,"page":1,"size":20,"pages":1}`.

## Edge Cases
- `_run_workflow` imports `run_inbox_workflow` lazily (deferred import) to avoid circular imports between endpoints and agents.
- The background task opens a new `AsyncSessionLocal()` because the request session is closed before the task runs.
- If commit fails after `flush()`: the `get_db` dependency auto-rolls back, returning 500.
- `size=0` in query params: clamped to `min(0, 100) = 0` — actually returns 0 items. Add `max(size, 1)` to prevent empty pages.
- Invalid UUID in path: caught with `try/except ValueError` → 404.

## Test Cases
1. `POST /submit` with valid content returns 201 with `status="pending"`.
2. `POST /submit` with content < 3 chars returns 422.
3. `POST /submit` with content > 5000 chars returns 422.
4. `POST /submit` with non-https `file_url` returns 422.
5. `POST /submit` without auth token returns 401.
6. `GET /{id}` returns submission for owner.
7. `GET /{id}` returns 404 for non-existent ID.
8. `GET /{id}` returns 404 when requesting another user's submission.
9. `GET /{id}` returns 404 for invalid UUID format.
10. `GET /` returns paginated list of user's submissions.
11. `GET /?size=200` caps at 100 items.
12. Background task sets status to `failed` when workflow throws.

## Acceptance Criteria
- [ ] `POST /submit` returns 201 immediately (background processing)
- [ ] `GET /{id}` returns correct submission for owner
- [ ] Users cannot access other users' submissions
- [ ] Pagination works correctly
- [ ] Background task failures update status to `failed`
- [ ] All validation rules enforced

## Definition of Done
- All test cases pass
- No mypy errors
- Inbox router registered in `api_router`
- Background task opens new DB session correctly
