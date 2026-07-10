# 030 – Analytics API

## Objective
Implement the Analytics API endpoints that provide aggregated submission statistics, agent performance breakdowns, daily activity trends, and per-user metrics. These endpoints power both the dashboard metric cards and the analytics page.

## Scope
- `GET /api/v1/analytics/summary` — overall stats for current user
- `GET /api/v1/analytics/by-agent` — submissions grouped by agent type
- `GET /api/v1/analytics/by-day` — daily submission counts for the last N days
- `app/api/v1/endpoints/analytics.py` — route handlers
- `app/schemas/analytics.py` — response schemas

## Out of Scope
- Admin-level analytics (all users) — admin endpoint in 034
- Real-time streaming analytics
- Analytics UI (031)

## Functional Requirements
1. All endpoints scoped to the current authenticated user's data only.
2. `GET /summary` returns: total, completed, failed, pending, avg_confidence, by_agent counts.
3. `GET /by-agent` returns per-agent breakdown with counts and avg confidence.
4. `GET /by-day` accepts `days` query param (default 30, max 90) and returns daily counts.
5. Empty data returns zeros — never 404.
6. Use SQLAlchemy aggregate queries (COUNT, AVG) — do not fetch all rows.

## Technical Requirements
- SQLAlchemy `func.count`, `func.avg`, `func.coalesce`
- `GROUP BY` queries for agent and date breakdowns
- `date_trunc('day', ...)` for daily aggregation
- FastAPI `Query` param with validation
- Pydantic response schemas

## Folder Structure
```
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── endpoints/
    │           └── analytics.py
    └── schemas/
        └── analytics.py
```

## Files To Create

### `app/schemas/analytics.py`
```python
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.db.models.inbox import AgentType


class AgentBreakdown(BaseModel):
    agent: str
    count: int
    avg_confidence: float
    completed: int
    failed: int


class DayBucket(BaseModel):
    date: str          # ISO date string "YYYY-MM-DD"
    count: int


class AnalyticsSummary(BaseModel):
    total_submissions: int
    completed: int
    failed: int
    pending: int
    processing: int
    avg_confidence: float
    by_agent: Dict[str, int]


class AnalyticsByAgentResponse(BaseModel):
    agents: List[AgentBreakdown]


class AnalyticsByDayResponse(BaseModel):
    days: int
    buckets: List[DayBucket]
```

### `app/api/v1/endpoints/analytics.py`
```python
"""
Analytics API

Provides aggregated statistics about inbox submissions.
All queries are scoped to the currently authenticated user.
"""
import structlog
from typing import List
from fastapi import APIRouter, Query
from sqlalchemy import select, func, case, literal_column, text
from sqlalchemy.dialects.postgresql import aggregate_order_by
from datetime import datetime, timedelta, timezone

from app.api.deps import DBSession, CurrentUser
from app.db.models.inbox import InboxSubmission, WorkflowStatus, AgentType
from app.schemas.analytics import (
    AnalyticsSummary,
    AgentBreakdown,
    DayBucket,
    AnalyticsByAgentResponse,
    AnalyticsByDayResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Get submission analytics summary for current user",
)
async def get_analytics_summary(
    db: DBSession,
    current_user: CurrentUser,
) -> AnalyticsSummary:
    """Returns high-level statistics for the current user's submissions."""
    result = await db.execute(
        select(
            func.count(InboxSubmission.id).label("total"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.completed, 1), else_=None)
            ).label("completed"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.failed, 1), else_=None)
            ).label("failed"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.pending, 1), else_=None)
            ).label("pending"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.processing, 1), else_=None)
            ).label("processing"),
            func.coalesce(func.avg(InboxSubmission.confidence_score), 0.0).label("avg_confidence"),
        ).where(InboxSubmission.user_id == current_user.id)
    )
    row = result.one()

    # By-agent counts
    agent_result = await db.execute(
        select(
            InboxSubmission.assigned_agent,
            func.count(InboxSubmission.id).label("cnt"),
        )
        .where(
            InboxSubmission.user_id == current_user.id,
            InboxSubmission.assigned_agent.isnot(None),
        )
        .group_by(InboxSubmission.assigned_agent)
    )
    by_agent = {row.assigned_agent.value: row.cnt for row in agent_result}

    return AnalyticsSummary(
        total_submissions=row.total,
        completed=row.completed,
        failed=row.failed,
        pending=row.pending,
        processing=row.processing,
        avg_confidence=float(row.avg_confidence),
        by_agent=by_agent,
    )


@router.get(
    "/by-agent",
    response_model=AnalyticsByAgentResponse,
    summary="Get per-agent analytics breakdown",
)
async def get_analytics_by_agent(
    db: DBSession,
    current_user: CurrentUser,
) -> AnalyticsByAgentResponse:
    result = await db.execute(
        select(
            InboxSubmission.assigned_agent,
            func.count(InboxSubmission.id).label("count"),
            func.coalesce(func.avg(InboxSubmission.confidence_score), 0.0).label("avg_confidence"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.completed, 1), else_=None)
            ).label("completed"),
            func.count(
                case((InboxSubmission.status == WorkflowStatus.failed, 1), else_=None)
            ).label("failed"),
        )
        .where(
            InboxSubmission.user_id == current_user.id,
            InboxSubmission.assigned_agent.isnot(None),
        )
        .group_by(InboxSubmission.assigned_agent)
        .order_by(func.count(InboxSubmission.id).desc())
    )

    agents = [
        AgentBreakdown(
            agent=row.assigned_agent.value,
            count=row.count,
            avg_confidence=float(row.avg_confidence),
            completed=row.completed,
            failed=row.failed,
        )
        for row in result
    ]

    return AnalyticsByAgentResponse(agents=agents)


@router.get(
    "/by-day",
    response_model=AnalyticsByDayResponse,
    summary="Get daily submission counts",
)
async def get_analytics_by_day(
    db: DBSession,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=90, description="Number of past days to include"),
) -> AnalyticsByDayResponse:
    """Returns daily submission counts for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", InboxSubmission.created_at).label("day"),
            func.count(InboxSubmission.id).label("count"),
        )
        .where(
            InboxSubmission.user_id == current_user.id,
            InboxSubmission.created_at >= since,
        )
        .group_by(text("day"))
        .order_by(text("day"))
    )

    # Build a complete day series (fill in missing days with 0)
    raw_buckets = {row.day.strftime("%Y-%m-%d"): row.count for row in result}
    buckets: List[DayBucket] = []
    for i in range(days):
        day = (since + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        buckets.append(DayBucket(date=day, count=raw_buckets.get(day, 0)))

    return AnalyticsByDayResponse(days=days, buckets=buckets)
```

## Files To Modify

### `app/api/v1/router.py` — include analytics router
```python
from app.api.v1.endpoints import auth, inbox, documents, analytics

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
```

## API Contracts

### `GET /api/v1/analytics/summary`
```
Response 200:
{
  "total_submissions": 142,
  "completed": 128,
  "failed": 14,
  "pending": 0,
  "processing": 0,
  "avg_confidence": 0.873,
  "by_agent": { "sales": 45, "support": 61, "finance": 22, "executive": 14 }
}
```

### `GET /api/v1/analytics/by-agent`
```
Response 200:
{
  "agents": [
    { "agent": "support", "count": 61, "avg_confidence": 0.88, "completed": 58, "failed": 3 },
    ...
  ]
}
```

### `GET /api/v1/analytics/by-day?days=7`
```
Response 200:
{
  "days": 7,
  "buckets": [
    { "date": "2024-01-09", "count": 12 },
    { "date": "2024-01-10", "count": 8 },
    ...
  ]
}
```

## Request Examples
```bash
curl http://localhost:8000/api/v1/analytics/summary \
  -H "Authorization: Bearer <token>"

curl "http://localhost:8000/api/v1/analytics/by-day?days=14" \
  -H "Authorization: Bearer <token>"
```

## Database Tables
**Reads from:** `inbox_submissions`
- Uses aggregate functions (COUNT, AVG)
- No writes

## Business Logic
1. All queries filter by `user_id = current_user.id` — users see only their own data.
2. `avg_confidence` uses `COALESCE(..., 0.0)` to return 0 instead of NULL for new accounts.
3. `by-day` fills in missing days with `count=0` to ensure a complete time series.
4. `by-agent` filters out `NULL` assigned_agent rows (pending/failed before routing).

## Validation Rules
- `days` query param: 1–90, default 30.
- All responses return 200 with zeroed data for new users (never 404).

## Error Handling
| Scenario | Behavior |
|----------|----------|
| No submissions | Returns all zeros |
| `days` out of range | 422 validation error |
| DB query error | 500 |

## UI Behavior
Not applicable — backend only.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
- New user with 0 submissions: all counts = 0, `by_agent = {}`, `buckets` all zeros.

## Edge Cases
- `avg_confidence` when all confidence scores are NULL: COALESCE returns 0.0.
- Day bucket: if a day has no submissions, it's filled with `count=0` in Python after query.
- `date_trunc("day", ...)` uses DB timezone (UTC) — ensure submission `created_at` is TIMESTAMPTZ.
- Large `days=90` with active user: up to 90 rows returned — acceptable.

## Test Cases
1. `GET /summary` with 0 submissions returns all zeros.
2. `GET /summary` with mixed statuses returns correct counts.
3. `GET /by-agent` groups by agent type correctly.
4. `GET /by-day?days=7` returns 7 buckets.
5. Days with no submissions appear as `count=0` (not missing).
6. `days=91` returns 422.
7. User A cannot see user B's analytics (user scoping).
8. `avg_confidence` is `0.0` when no completed submissions.

## Acceptance Criteria
- [ ] `/summary` returns correct totals per status
- [ ] `/by-agent` groups correctly with avg confidence
- [ ] `/by-day` returns complete date series with zeros for empty days
- [ ] All endpoints user-scoped
- [ ] Empty data returns zeros not 404

## Definition of Done
- All test cases pass
- No mypy errors
- All 3 endpoints registered in api_router
- Aggregate queries use SQL-level aggregation (no Python-side aggregation)
