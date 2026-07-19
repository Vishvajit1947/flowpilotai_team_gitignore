import math
import uuid as _uuid
import structlog
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import DBSession, CurrentUser
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.models.inbox import InboxSubmission, WorkflowStatus
from app.schemas.inbox import (
    InboxSubmitRequest,
    InboxSubmissionResponse,
    PaginatedSubmissionsResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/upload-file",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to Supabase Storage and return its URL",
)
async def upload_file(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
) -> dict:
    """
    Accepts a PDF/PNG/JPG file, uploads to Supabase Storage under
    the user's folder, and returns the public URL.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, PNG, JPG.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    file_ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    file_name = f"{_uuid.uuid4().hex}.{file_ext}"
    storage_path = f"uploads/{current_user.id}/{file_name}"

    if settings.is_mock_mode:
        mock_url = "https://images.unsplash.com/photo-1557804506-669a67965ba0" if "image" in (file.content_type or "") else "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        logger.info("file_uploaded_mock", user_id=str(current_user.id), path=storage_path)
        return {"url": mock_url, "path": storage_path}

    import httpx

    supabase_url = settings.SUPABASE_URL.rstrip("/")
    supabase_key = settings.SUPABASE_SERVICE_KEY

    upload_url = f"{supabase_url}/storage/v1/object/uploads/{storage_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            upload_url,
            content=contents,
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": file.content_type or "application/octet-stream",
                "x-upsert": "true",
            },
        )

    if resp.status_code not in (200, 201):
        logger.error("supabase_upload_failed", status=resp.status_code, body=resp.text[:300])
        raise HTTPException(status_code=502, detail=f"File upload failed: {resp.status_code}")

    public_url = f"{supabase_url}/storage/v1/object/public/uploads/{storage_path}"
    logger.info("file_uploaded", user_id=str(current_user.id), path=storage_path)

    return {"url": public_url, "path": storage_path}


async def _run_workflow(submission_id: str, db_session_factory) -> None:
    """
    Background task: run LangGraph workflow for the given submission.
    Imports are deferred to avoid circular imports.
    """
    from app.agents.workflow import run_inbox_workflow
    from app.db.session import AsyncSessionLocal
    import uuid as _uuid
    import asyncio
    from sqlalchemy.exc import NoResultFound

    async with AsyncSessionLocal() as db:
        try:
            # Retry loop to wait for transaction commit visibility
            submission = None
            for attempt in range(5):
                try:
                    result = await db.execute(
                        select(InboxSubmission).where(
                            InboxSubmission.id == _uuid.UUID(submission_id)
                        )
                    )
                    submission = result.scalar_one()
                    break
                except NoResultFound:
                    if attempt == 4:
                        raise
                    await asyncio.sleep(0.2)

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
    await db.commit()
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
    "/by-id/{submission_id}",
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
