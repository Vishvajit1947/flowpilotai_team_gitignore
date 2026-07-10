# 034 – Admin DB Reset

## Objective
Implement a protected admin endpoint `POST /api/v1/admin/reset-demo` that clears all inbox submissions (but not users) for demo reset purposes, and a companion `POST /api/v1/admin/seed-demo` that inserts sample data. Both require the `admin` role.

## Scope
- `POST /api/v1/admin/reset-demo` — delete all inbox_submissions rows
- `POST /api/v1/admin/seed-demo` — insert realistic demo submissions
- `GET /api/v1/admin/users` — list all users (admin only)
- `app/api/v1/endpoints/admin.py` — admin routes
- Admin-only dependency (`require_admin` from 005)

## Out of Scope
- Admin UI panel (035)
- User management (creating/deleting users via API)
- Database migrations

## Functional Requirements
1. `POST /reset-demo` deletes all rows from `inbox_submissions` table.
2. `POST /seed-demo` inserts 10 diverse sample submissions across all 4 agent types.
3. `GET /users` returns list of all users (email, role, is_active, created_at).
4. All endpoints require `role = 'admin'` via `require_admin` dependency.
5. Non-admin users receive 403.
6. Each operation is wrapped in a transaction.

## Technical Requirements
- FastAPI `require_admin` dependency
- SQLAlchemy bulk delete + bulk insert
- Seed data covers all 4 agent types with realistic content
- Returns operation summary (rows affected, operation name)

## Folder Structure
```
backend/
└── app/
    └── api/
        └── v1/
            └── endpoints/
                └── admin.py
```

## Files To Create

### `app/api/v1/endpoints/admin.py`
```python
"""
Admin API endpoints.
All routes require role='admin'.
"""
import structlog
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, status
from sqlalchemy import delete, select, func

from app.api.deps import DBSession, AdminUser
from app.db.models.user import User
from app.db.models.inbox import InboxSubmission, WorkflowStatus, AgentType
from app.schemas.user import UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

# ─── Seed Data ─────────────────────────────────────────────────────────────────

SEED_SUBMISSIONS = [
    {
        "content": "Hi, we have a new enterprise lead from Acme Corp. John Smith (CTO) is interested in our platform for 500 users. Budget confirmed at $250k/year. He wants a demo next Tuesday.",
        "detected_intent": "sales_lead",
        "confidence_score": 0.92,
        "assigned_agent": AgentType.sales,
        "status": WorkflowStatus.completed,
        "result": {
            "agent_response": {
                "agent_type": "sales",
                "summary": "High-value enterprise lead from Acme Corp CTO, $250k/year budget confirmed.",
                "structured_data": {
                    "company_name": "Acme Corp",
                    "contact_name": "John Smith",
                    "urgency": "hot",
                    "lead_score": 87,
                    "deal_size_estimate": "$250,000",
                },
                "action_items": ["Schedule demo for Tuesday", "Send enterprise pricing proposal"],
                "confidence": 0.92,
            },
            "steps": [
                {"step_name": "intent_node", "status": "completed", "data": {"intent": "sales_lead"}},
                {"step_name": "confidence_node", "status": "completed", "data": {"score": 0.92}},
                {"step_name": "router_node", "status": "completed", "data": {"agent": "sales", "escalated": False}},
                {"step_name": "sales_agent_node", "status": "completed", "data": {"lead_score": 87, "urgency": "hot"}},
            ],
        },
    },
    {
        "content": "URGENT: Our login page has been returning 500 errors for the last 2 hours. All enterprise customers are affected. Error: JWT_SECRET_MISSING in logs.",
        "detected_intent": "customer_support",
        "confidence_score": 0.97,
        "assigned_agent": AgentType.support,
        "status": WorkflowStatus.completed,
        "result": {
            "agent_response": {
                "agent_type": "support",
                "summary": "Critical production outage — JWT secret missing, all enterprise logins failing.",
                "structured_data": {
                    "issue_type": "bug",
                    "severity": "critical",
                    "sla_recommendation": "1 hour",
                    "escalate_to_engineering": True,
                },
                "action_items": ["Check environment variables immediately", "Roll back recent deploy"],
                "confidence": 0.97,
            },
            "steps": [
                {"step_name": "intent_node", "status": "completed", "data": {"intent": "customer_support"}},
                {"step_name": "confidence_node", "status": "completed", "data": {"score": 0.97}},
                {"step_name": "router_node", "status": "completed", "data": {"agent": "support", "escalated": False}},
                {"step_name": "support_agent_node", "status": "completed", "data": {"severity": "critical"}},
            ],
        },
    },
    {
        "content": "Please process this invoice from TechSupplies Inc. Invoice #INV-2024-0042, $4,860.00 due Feb 14. For cloud storage services.",
        "detected_intent": "invoice_processing",
        "confidence_score": 0.89,
        "assigned_agent": AgentType.finance,
        "status": WorkflowStatus.completed,
        "result": {
            "agent_response": {
                "agent_type": "finance",
                "summary": "Invoice from TechSupplies Inc for $4,860.00 — approved for payment.",
                "structured_data": {
                    "vendor_name": "TechSupplies Inc",
                    "invoice_number": "INV-2024-0042",
                    "total_amount": 4860.00,
                    "payment_recommendation": "approve",
                    "anomalies": [],
                },
                "action_items": ["Route for CFO approval", "Schedule payment by Feb 14"],
                "confidence": 0.89,
            },
            "steps": [
                {"step_name": "intent_node", "status": "completed", "data": {"intent": "invoice_processing"}},
                {"step_name": "confidence_node", "status": "completed", "data": {"score": 0.89}},
                {"step_name": "router_node", "status": "completed", "data": {"agent": "finance"}},
                {"step_name": "finance_agent_node", "status": "completed", "data": {"total_amount": 4860.0}},
            ],
        },
    },
    {
        "content": "Q3 Board Report: Revenue $12.4M (+18% YoY). Churn 2.3%, NPS 64. Key risk: enterprise churn in APAC region. Proposed: expand CS team by 3 headcount.",
        "detected_intent": "executive_summary",
        "confidence_score": 0.94,
        "assigned_agent": AgentType.executive,
        "status": WorkflowStatus.completed,
        "result": {
            "agent_response": {
                "agent_type": "executive",
                "summary": "Strong Q3 performance with 18% revenue growth. APAC churn risk flagged.",
                "structured_data": {
                    "content_type": "kpi_review",
                    "priority": "high",
                    "key_metrics": [
                        {"metric": "Revenue", "value": "$12.4M", "context": "+18% YoY"},
                        {"metric": "Churn", "value": "2.3%", "context": "Within target"},
                    ],
                },
                "action_items": ["Approve APAC CS headcount request", "Schedule board follow-up"],
                "confidence": 0.94,
            },
            "steps": [
                {"step_name": "intent_node", "status": "completed", "data": {"intent": "executive_summary"}},
                {"step_name": "confidence_node", "status": "completed", "data": {"score": 0.94}},
                {"step_name": "router_node", "status": "completed", "data": {"agent": "executive"}},
                {"step_name": "executive_agent_node", "status": "completed", "data": {"priority": "high"}},
            ],
        },
    },
    {
        "content": "Can you help me understand what the thingy does with the data?",
        "detected_intent": "unknown",
        "confidence_score": 0.15,
        "assigned_agent": AgentType.executive,
        "status": WorkflowStatus.completed,
        "result": {
            "agent_response": {
                "agent_type": "executive",
                "summary": "Low-confidence submission escalated for manual review.",
                "structured_data": {
                    "content_type": "escalation",
                    "escalation_context": {"was_escalated": True, "recommended_handler": "manual_review"},
                },
                "action_items": ["Manual review required"],
                "confidence": 0.2,
            },
            "steps": [
                {"step_name": "intent_node", "status": "completed", "data": {"intent": "unknown"}},
                {"step_name": "confidence_node", "status": "completed", "data": {"score": 0.15}},
                {"step_name": "router_node", "status": "completed", "data": {"agent": "executive", "escalated": True}},
                {"step_name": "executive_agent_node", "status": "completed", "data": {"is_escalation": True}},
            ],
        },
    },
]

# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post(
    "/reset-demo",
    status_code=status.HTTP_200_OK,
    summary="Reset all demo data (admin only)",
)
async def reset_demo(db: DBSession, admin: AdminUser) -> dict:
    result = await db.execute(delete(InboxSubmission))
    deleted = result.rowcount
    await db.commit()
    logger.info("demo_reset", admin_id=str(admin.id), deleted_rows=deleted)
    return {"operation": "reset_demo", "deleted_rows": deleted}


@router.post(
    "/seed-demo",
    status_code=status.HTTP_201_CREATED,
    summary="Seed demo data (admin only)",
)
async def seed_demo(db: DBSession, admin: AdminUser) -> dict:
    submissions = []
    for seed in SEED_SUBMISSIONS:
        s = InboxSubmission(
            user_id=admin.id,
            content=seed["content"],
            detected_intent=seed["detected_intent"],
            confidence_score=seed["confidence_score"],
            assigned_agent=seed["assigned_agent"],
            status=seed["status"],
            result=seed["result"],
        )
        submissions.append(s)

    db.add_all(submissions)
    await db.commit()
    logger.info("demo_seeded", admin_id=str(admin.id), count=len(submissions))
    return {"operation": "seed_demo", "seeded_rows": len(submissions)}


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
)
async def list_users(db: DBSession, admin: AdminUser) -> list[UserResponse]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]
```

## Files To Modify

### `app/api/v1/router.py` — include admin router
```python
from app.api.v1.endpoints import auth, inbox, documents, analytics, admin

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
```

## API Contracts

### `POST /api/v1/admin/reset-demo`
```
Auth: Bearer token (admin role required)
Response 200: { "operation": "reset_demo", "deleted_rows": 42 }
Response 403: { "detail": "Admin access required" }
```

### `POST /api/v1/admin/seed-demo`
```
Auth: Bearer token (admin role required)
Response 201: { "operation": "seed_demo", "seeded_rows": 5 }
```

### `GET /api/v1/admin/users`
```
Auth: Bearer token (admin role required)
Response 200: [ UserResponse, ... ]
```

## Request Examples
```bash
curl -X POST http://localhost:8000/api/v1/admin/reset-demo \
  -H "Authorization: Bearer <admin_token>"

curl -X POST http://localhost:8000/api/v1/admin/seed-demo \
  -H "Authorization: Bearer <admin_token>"
```

## Database Tables
- `POST /reset-demo` — DELETE FROM `inbox_submissions`
- `POST /seed-demo` — INSERT INTO `inbox_submissions`
- `GET /users` — SELECT FROM `users`

## Business Logic
- `reset-demo` uses `delete(InboxSubmission)` (not `DELETE FROM` text) for ORM-level cascade safety.
- Seed data is always attached to the admin user's `user_id` for simplicity.
- Both operations are logged with admin user ID for audit.

## Validation Rules
- Only admin role can call these endpoints.
- No body validation needed for reset/seed.

## Error Handling
| Scenario | Status |
|----------|--------|
| Non-admin user | 403 |
| DB error | 500 |

## UI Behavior
Not applicable — see 035 for Admin Banner.

## Test Cases
1. `POST /reset-demo` with admin token deletes all submissions and returns count.
2. `POST /reset-demo` with user token returns 403.
3. `POST /seed-demo` inserts 5 sample submissions.
4. After seed, `GET /api/v1/inbox/` returns 5 submissions.
5. `GET /users` returns all users.
6. `GET /users` with non-admin token returns 403.

## Acceptance Criteria
- [ ] `/reset-demo` deletes all submissions (not users)
- [ ] `/seed-demo` creates realistic demo data
- [ ] All endpoints return 403 for non-admin
- [ ] Operations logged with admin ID
- [ ] Transaction wraps each operation

## Definition of Done
- All test cases pass
- No mypy errors
- Admin router registered in `api_router`
- Seed data covers all 4 agent types + escalation case
