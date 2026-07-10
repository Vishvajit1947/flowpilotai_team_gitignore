# 003 – Backend Scaffold

## Objective
Build the complete FastAPI application scaffold including configuration management, database session factory, structured logging, CORS middleware, global exception handlers, health check endpoint, and the core application module layout so every subsequent backend task has a consistent, typed foundation.

## Scope
- `app/core/config.py` — Pydantic Settings with environment variable binding
- `app/core/security.py` — password hashing and JWT utilities (stubs, fully implemented in 005)
- `app/core/logging.py` — structlog configuration
- `app/core/exceptions.py` — custom exception classes
- `app/db/session.py` — SQLAlchemy async session factory
- `app/db/base.py` — declarative base model
- `app/api/deps.py` — FastAPI dependency injection functions
- `app/api/v1/router.py` — top-level v1 API router
- `main.py` — application entry point with middleware and lifespan

## Out of Scope
- Authentication endpoints (006, 007)
- Database table definitions (004)
- Agent logic (017–025)
- Any business logic beyond infrastructure

## Functional Requirements
1. `GET /health` returns `{"status": "ok", "version": "1.0.0", "db": "connected"}`.
2. All endpoints are versioned under `/api/v1/`.
3. CORS is configured via environment variable `ALLOWED_ORIGINS`.
4. All exceptions return structured JSON: `{"detail": "...", "status_code": N}`.
5. Application logs are structured JSON in production, human-readable in development.
6. Database connections are pooled and released on shutdown.

## Technical Requirements
- FastAPI 0.111.x with `lifespan` context manager (not deprecated `startup`/`shutdown` events)
- SQLAlchemy 2.0 with async engine (`asyncpg` driver)
- Pydantic Settings v2 for config
- structlog for logging
- Python 3.11+
- All modules must be importable without side effects

## Folder Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── agents/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── main.py
└── .env
```

## Files To Create

### `app/core/config.py`
```python
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "FlowPilot AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    # OpenAI
    OPENAI_API_KEY: str

    # CORS — stored as JSON string in env: '["http://localhost:3000"]'
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()  # type: ignore[call-arg]
```

### `app/core/exceptions.py`
```python
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
```

### `app/core/logging.py`
```python
import logging
import structlog
from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog for the application."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.DEBUG:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(
            logging.DEBUG if settings.DEBUG else logging.WARNING
        )
```

### `app/db/base.py`
```python
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    # All tables get automatic created_at / updated_at
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )
```

### `app/db/session.py`
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

# Convert postgres:// to postgresql+asyncpg://
_db_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace(
    "postgres://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Health check for database connectivity."""
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("db_connection_failed", error=str(e))
        return False
```

### `app/api/deps.py`
```python
"""
FastAPI dependency functions used across route handlers.
Authentication dependencies are extended in 005_Custom_JWT_Authentication.md.
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

# Type alias for injected DB session
DBSession = Annotated[AsyncSession, Depends(get_db)]
```

### `app/api/v1/router.py`
```python
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

# Sub-routers are included here as features are added:
# from app.api.v1.endpoints import auth, inbox, analytics
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
```

### `main.py` (complete version)
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    FlowPilotException,
    flowpilot_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import configure_logging
from app.db.session import check_db_connection, engine

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    logger.info("startup", app=settings.APP_NAME, version=settings.VERSION)
    yield
    logger.info("shutdown", app=settings.APP_NAME)
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered inbox orchestration and workflow automation",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Exception Handlers ───────────────────────────────────────────────────────
app.add_exception_handler(FlowPilotException, flowpilot_exception_handler)  # type: ignore
app.add_exception_handler(HTTPException, http_exception_handler)            # type: ignore
app.add_exception_handler(Exception, unhandled_exception_handler)           # type: ignore

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ─── Health Check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check() -> dict:
    db_ok = await check_db_connection()
    return {
        "status": "ok",
        "version": settings.VERSION,
        "db": "connected" if db_ok else "disconnected",
    }
```

### `tests/conftest.py`
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.api.deps import get_db
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

## Existing Files To Modify
- `requirements.txt` — add `aiosqlite==0.20.0` (for test SQLite) and `asyncpg==0.29.0`

## API Contracts

### Health Check
```
GET /health
Authorization: none

Response 200:
{
  "status": "ok",
  "version": "1.0.0",
  "db": "connected"
}

Response 200 (DB down):
{
  "status": "ok",
  "version": "1.0.0",
  "db": "disconnected"
}
```

## Request Examples
```bash
curl http://localhost:8000/health
```

## Response Examples
```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "connected"
}
```

## Database Tables
None defined in this task — see 004_Database_Schema.md.

## Business Logic
- Health check never returns a non-200 status code. DB connectivity is reported as a field, not an HTTP error, so load balancers don't remove healthy app instances just because the DB is slow.
- All exceptions caught at the application level return structured JSON — never HTML error pages.
- Session commits happen automatically via the `get_db` dependency on successful handler completion; rollback on any exception.

## Validation Rules
- `SECRET_KEY` must be set — Pydantic will raise `ValidationError` at startup if missing.
- `DATABASE_URL` must be set — same.
- `ALLOWED_ORIGINS` is parsed from JSON string if provided as environment variable.

## Error Handling
| Exception Class | HTTP Status | Usage |
|-----------------|-------------|-------|
| `AuthenticationError` | 401 | Invalid/missing JWT |
| `AuthorizationError` | 403 | Insufficient role |
| `NotFoundError` | 404 | Resource missing |
| `ValidationError` | 422 | Business rule violation |
| `ConflictError` | 409 | Duplicate resource |
| `FlowPilotException` | variable | Base class |
| `HTTPException` (FastAPI) | variable | Route-level raises |
| Unhandled `Exception` | 500 | Catch-all |

All error responses follow this shape:
```json
{ "detail": "Human-readable message", "status_code": 422 }
```

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- `DATABASE_URL` from Supabase uses `postgres://` scheme — the session module must convert it to `postgresql+asyncpg://`.
- Running tests uses SQLite in-memory via aiosqlite — no Postgres required for unit tests.
- `engine.dispose()` must be called in the lifespan shutdown to prevent connection pool leaks in tests.
- If `structlog` is not configured before the first log call, output will be unformatted — `configure_logging()` is called at module level in `main.py`.

## Test Cases
1. `GET /health` returns 200 with `{"status":"ok"}`.
2. `GET /health` when DB is unreachable returns 200 with `{"db":"disconnected"}`.
3. `GET /api/v1/unknown` returns `{"detail":"Not Found","status_code":404}`.
4. Raising `FlowPilotException("test", 400)` in a route returns 400 JSON.
5. Unhandled exception in a route returns 500 JSON (not HTML).
6. CORS preflight `OPTIONS /health` with `Origin: http://localhost:3000` returns 200.
7. CORS preflight with disallowed origin returns 400.

## Acceptance Criteria
- [ ] `GET /health` returns 200 JSON
- [ ] All exceptions return structured JSON (never HTML)
- [ ] CORS allows configured origins only
- [ ] Structlog outputs JSON in non-debug mode
- [ ] DB session auto-commits on success, auto-rolls back on exception
- [ ] Application starts and shuts down cleanly via lifespan

## Definition of Done
- All acceptance criteria checked
- `pytest tests/` passes
- `uvicorn main:app` starts without errors with a valid `.env`
- No mypy errors on `app/core/` and `app/db/`
