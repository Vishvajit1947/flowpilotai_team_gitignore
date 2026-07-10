import math
import structlog
from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select, func

from app.api.deps import DBSession, CurrentUser
from app.core.exceptions import NotFoundError
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
    size = max(min(size, 100), 1)  # Cap at 100, min 1
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
