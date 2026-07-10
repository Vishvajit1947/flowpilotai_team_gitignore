# 004 – Database Schema

## Objective
Define and create all PostgreSQL database tables for FlowPilot AI using SQLAlchemy ORM models and Alembic migrations. This document covers every table, column, type, constraint, index, and foreign key relationship required by the entire application.

## Scope
- SQLAlchemy ORM model definitions for all tables
- Alembic migration setup and initial migration file
- Database indexes for query performance
- Table relationship definitions
- Supabase Row Level Security (RLS) policy notes

## Out of Scope
- Seed data / fixtures (handled per feature task)
- Redis or any non-Postgres store
- Supabase Auth (we use custom JWT — see 005)

## Functional Requirements
1. All tables must have `id` (UUID primary key), `created_at`, and `updated_at` columns.
2. Soft-delete pattern is NOT used — rows are hard deleted when removed.
3. Foreign keys must have `ON DELETE CASCADE` where child rows are meaningless without parent.
4. All text fields storing user-provided content must have reasonable length limits.
5. Confidence scores are stored as `FLOAT` in range [0.0, 1.0].
6. Workflow result JSON is stored as `JSONB`.

## Technical Requirements
- PostgreSQL 15+ (Supabase-hosted)
- SQLAlchemy 2.0 ORM with Python type annotations
- Alembic 1.13+ for migrations
- UUID primary keys using `gen_random_uuid()` (PostgreSQL native)
- `TIMESTAMPTZ` for all timestamps
- `asyncpg` driver (async connections)

## Folder Structure
```
backend/
├── app/
│   └── db/
│       ├── base.py            # DeclarativeBase (from 003)
│       ├── session.py         # Engine + session factory (from 003)
│       └── models/
│           ├── __init__.py    # Re-exports all models
│           ├── user.py        # User model
│           └── inbox.py       # InboxSubmission model
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
└── alembic.ini
```

## Files To Create

### `app/db/models/user.py`
```python
import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.user,
        server_default="user",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships
    submissions: Mapped[list["InboxSubmission"]] = relationship(
        "InboxSubmission",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
```

### `app/db/models/inbox.py`
```python
import uuid
from typing import Any
from sqlalchemy import (
    String,
    Text,
    Float,
    Enum as SAEnum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


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
        JSONB,
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
```

### `app/db/models/__init__.py`
```python
# Re-export all models so Alembic's env.py can discover them
from app.db.models.user import User, UserRole
from app.db.models.inbox import InboxSubmission, AgentType, WorkflowStatus

__all__ = [
    "User",
    "UserRole",
    "InboxSubmission",
    "AgentType",
    "WorkflowStatus",
]
```

### `alembic.ini`
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### `alembic/env.py`
```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import all models so their metadata is populated
from app.db.base import Base
import app.db.models  # noqa: F401 — side-effect import registers models

from app.core.config import settings

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### `alembic/versions/0001_initial_schema.py`
```python
"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'user')")
    op.execute(
        "CREATE TYPE agent_type AS ENUM ('sales', 'support', 'finance', 'executive')"
    )
    op.execute(
        "CREATE TYPE workflow_status AS ENUM ('pending', 'processing', 'completed', 'failed')"
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "user", name="user_role", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── inbox_submissions ─────────────────────────────────────────────────────
    op.create_table(
        "inbox_submissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_url", sa.String(2048), nullable=True),
        sa.Column("detected_intent", sa.String(255), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "assigned_agent",
            sa.Enum(
                "sales", "support", "finance", "executive",
                name="agent_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="workflow_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inbox_submissions_user_id", "inbox_submissions", ["user_id"]
    )
    op.create_index(
        "ix_inbox_submissions_status", "inbox_submissions", ["status"]
    )
    op.create_index(
        "ix_inbox_submissions_created_at", "inbox_submissions", ["created_at"]
    )

    # ── updated_at triggers ───────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    for table in ("users", "inbox_submissions"):
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
        """)


def downgrade() -> None:
    for table in ("users", "inbox_submissions"):
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_table("inbox_submissions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS workflow_status")
    op.execute("DROP TYPE IF EXISTS agent_type")
    op.execute("DROP TYPE IF EXISTS user_role")
```

## Existing Files To Modify
- `app/db/base.py` — already defined in 003; no changes needed
- `app/db/session.py` — already defined in 003; no changes needed

## API Contracts
None — this is data layer only.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables

### `users`
| Column | Type | Constraints | Default |
|--------|------|-------------|---------|
| `id` | UUID | PK, NOT NULL | `gen_random_uuid()` |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | — |
| `full_name` | VARCHAR(255) | NOT NULL | — |
| `hashed_password` | VARCHAR(255) | NOT NULL | — |
| `role` | ENUM(user_role) | NOT NULL | `'user'` |
| `is_active` | BOOLEAN | NOT NULL | `true` |
| `created_at` | TIMESTAMPTZ | NOT NULL | `now()` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `now()` |

### `inbox_submissions`
| Column | Type | Constraints | Default |
|--------|------|-------------|---------|
| `id` | UUID | PK, NOT NULL | `gen_random_uuid()` |
| `user_id` | UUID | FK→users.id CASCADE, NOT NULL, INDEX | — |
| `content` | TEXT | NOT NULL | — |
| `file_url` | VARCHAR(2048) | NULL | — |
| `detected_intent` | VARCHAR(255) | NULL | — |
| `confidence_score` | FLOAT | NULL, range [0,1] | — |
| `assigned_agent` | ENUM(agent_type) | NULL | — |
| `status` | ENUM(workflow_status) | NOT NULL, INDEX | `'pending'` |
| `result` | JSONB | NULL | — |
| `error_message` | TEXT | NULL | — |
| `created_at` | TIMESTAMPTZ | NOT NULL, INDEX | `now()` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `now()` |

### Indexes
| Table | Index Name | Columns | Unique |
|-------|-----------|---------|--------|
| users | `ix_users_email` | email | YES |
| inbox_submissions | `ix_inbox_submissions_user_id` | user_id | NO |
| inbox_submissions | `ix_inbox_submissions_status` | status | NO |
| inbox_submissions | `ix_inbox_submissions_created_at` | created_at | NO |

## Business Logic
- `updated_at` is automatically maintained via PostgreSQL trigger — ORM-level `onupdate` is a fallback.
- User deletion cascades to all their inbox submissions (no orphaned rows).
- `confidence_score` application-level constraint: must be between 0.0 and 1.0; enforced in service layer, not DB constraint.

## Validation Rules
- `email` must be unique (DB-enforced via unique index).
- `content` in inbox_submissions must be non-empty (enforced in API layer).
- `file_url` max length 2048 bytes (standard URL limit).

## Error Handling
- Migration failure: Alembic will roll back the transaction automatically.
- `IntegrityError` on duplicate email: caught in Register API (006) and returned as 409 Conflict.
- `ForeignKeyViolation` when deleting a user that has submissions: prevented by cascade.

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
- `gen_random_uuid()` requires the `pgcrypto` extension in older Postgres versions. Supabase enables this by default. Verify with `SELECT gen_random_uuid();` before migration.
- Alembic `env.py` must convert `postgres://` to `postgresql+asyncpg://` before creating the engine.
- Running migrations in CI should use `--check` flag to verify no pending migrations.
- Enum types in PostgreSQL are non-transactional for DROP — downgrade may fail if run in a transaction. Downgrade is for development only.

## Test Cases
1. Running `alembic upgrade head` against a fresh database creates all tables.
2. Running `alembic downgrade base` drops all tables and enums cleanly.
3. Creating a `User` ORM object and committing persists to the DB.
4. Creating a second `User` with duplicate email raises `IntegrityError`.
5. Deleting a `User` cascades deletion of all their `InboxSubmission` rows.
6. `updated_at` changes when a row is updated via the trigger.
7. `InboxSubmission.result` correctly stores and retrieves nested JSONB.

## Acceptance Criteria
- [ ] `alembic upgrade head` succeeds on a fresh Supabase database
- [ ] All tables and indexes exist as specified
- [ ] All enum types exist in the database
- [ ] Cascade delete works (user → submissions)
- [ ] `updated_at` trigger fires on row updates
- [ ] ORM models correctly map to database columns

## Definition of Done
- `alembic upgrade head` runs without errors
- `alembic downgrade base` runs without errors
- All model imports work without circular dependencies
- No mypy errors on model files
