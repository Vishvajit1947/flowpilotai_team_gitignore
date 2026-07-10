from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class FlowPilotException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(FlowPilotException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message, status_code=401)


class AuthorizationError(FlowPilotException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundError(FlowPilotException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ValidationError(FlowPilotException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class ConflictError(FlowPilotException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


# ─── Exception Handlers ───────────────────────────────────────────────────────

async def flowpilot_exception_handler(
    request: Request, exc: FlowPilotException
) -> JSONResponse:
    logger.warning(
        "application_exception",
        path=str(request.url),
        status_code=exc.status_code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "status_code": exc.status_code},
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    logger.warning(
        "http_exception",
        path=str(request.url),
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        path=str(request.url),
        exc_type=type(exc).__name__,
        exc_message=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )
