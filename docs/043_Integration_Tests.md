# 043 – Integration Tests

## Objective
Write integration tests for all critical backend API flows: auth (register/login), inbox submission lifecycle, analytics endpoints, and admin endpoints — using `pytest-asyncio` and `httpx.AsyncClient` with an in-memory SQLite test database.

## Scope
- `tests/test_auth.py` — register, login, get_me endpoints
- `tests/test_inbox.py` — submit, poll, list endpoints
- `tests/test_analytics.py` — summary, by-agent, by-day
- `tests/test_admin.py` — reset, seed, list users
- `tests/conftest.py` — shared fixtures (from 003, extended here)
- Mock OpenAI calls to avoid API costs in tests

## Out of Scope
- Frontend tests (separate test framework)
- Load/performance tests
- E2E tests (045)

## Functional Requirements
1. All API endpoints have at least one happy-path test.
2. All auth error cases tested (wrong password, duplicate email, expired token).
3. Inbox submission lifecycle tested (create → poll → complete).
4. Admin endpoints tested with both admin and non-admin tokens.
5. Tests run in under 30 seconds total.
6. Tests use mocked OpenAI to avoid real API calls.

## Technical Requirements
- `pytest-asyncio` with `asyncio_mode = "auto"`
- `httpx.AsyncClient` with `ASGITransport`
- SQLite in-memory database (from conftest in 003)
- `unittest.mock.patch` for OpenAI mocking

## Folder Structure
```
backend/
└── tests/
    ├── __init__.py
    ├── conftest.py          # Fixtures (from 003, extended)
    ├── test_auth.py
    ├── test_inbox.py
    ├── test_analytics.py
    └── test_admin.py
```

## Files To Create

### Extended `tests/conftest.py`
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    """Client with a pre-registered and logged-in user."""
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass1",
        "full_name": "Test User",
    })
    # Login
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass1",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest_asyncio.fixture
async def admin_client(client):
    """Client with an admin user."""
    from sqlalchemy import select, update
    from app.db.models.user import User, UserRole

    resp = await client.post("/api/v1/auth/register", json={
        "email": "admin@example.com",
        "password": "AdminPass1",
        "full_name": "Admin User",
    })
    token = resp.json()["access_token"]

    # Promote to admin via DB
    async with TestSessionLocal() as db:
        await db.execute(
            update(User)
            .where(User.email == "admin@example.com")
            .values(role=UserRole.admin)
        )
        await db.commit()

    # Re-login to get admin token
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminPass1",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

### `tests/test_auth.py`
```python
import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "alice@example.com",
        "password": "AlicePass1",
        "full_name": "Alice Smith",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "DupPass1", "full_name": "Dup User"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "short",
        "full_name": "Test User",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_no_uppercase(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "alllowercase1",
        "full_name": "Test User",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "bob@example.com", "password": "BobPass1", "full_name": "Bob"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "bob@example.com", "password": "BobPass1"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "carol@example.com", "password": "CarolPass1", "full_name": "Carol"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "carol@example.com", "password": "WrongPass1"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "SomePass1"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_get_me(auth_client):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_me_no_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
```

### `tests/test_inbox.py`
```python
import pytest
from unittest.mock import patch, AsyncMock


MOCK_INTENT = AsyncMock()
MOCK_INTENT.return_value = type('obj', (object,), {
    'intent': 'sales_lead', 'reasoning': 'test', 'from_cache': False
})()

MOCK_CONFIDENCE = AsyncMock(return_value=0.88)


@pytest.mark.asyncio
async def test_submit_inbox(auth_client):
    resp = await auth_client.post("/api/v1/inbox/submit", json={
        "content": "We have a new enterprise lead from Acme Corp",
        "file_url": None,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["content"] == "We have a new enterprise lead from Acme Corp"
    assert "id" in data


@pytest.mark.asyncio
async def test_submit_short_content(auth_client):
    resp = await auth_client.post("/api/v1/inbox/submit", json={"content": "Hi"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_no_auth(client):
    resp = await client.post("/api/v1/inbox/submit", json={"content": "Test content"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_submission(auth_client):
    create_resp = await auth_client.post("/api/v1/inbox/submit", json={
        "content": "Test submission content"
    })
    submission_id = create_resp.json()["id"]

    resp = await auth_client.get(f"/api/v1/inbox/{submission_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == submission_id


@pytest.mark.asyncio
async def test_get_submission_not_found(auth_client):
    resp = await auth_client.get("/api/v1/inbox/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_submissions(auth_client):
    # Create 3 submissions
    for i in range(3):
        await auth_client.post("/api/v1/inbox/submit", json={"content": f"Submission {i+1} content"})

    resp = await auth_client.get("/api/v1/inbox/?page=1&size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_cross_user_isolation(client):
    """User A cannot access User B's submissions."""
    # User A registers and submits
    await client.post("/api/v1/auth/register", json={
        "email": "userA@test.com", "password": "UserAPass1", "full_name": "User A"
    })
    resp_a = await client.post("/api/v1/auth/login", json={"email": "userA@test.com", "password": "UserAPass1"})
    token_a = resp_a.json()["access_token"]

    create_resp = await client.post("/api/v1/inbox/submit",
        json={"content": "User A private content"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    submission_id = create_resp.json()["id"]

    # User B registers and tries to access User A's submission
    await client.post("/api/v1/auth/register", json={
        "email": "userB@test.com", "password": "UserBPass1", "full_name": "User B"
    })
    resp_b = await client.post("/api/v1/auth/login", json={"email": "userB@test.com", "password": "UserBPass1"})
    token_b = resp_b.json()["access_token"]

    resp = await client.get(f"/api/v1/inbox/{submission_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
```

### `tests/test_analytics.py`
```python
import pytest


@pytest.mark.asyncio
async def test_analytics_summary_empty(auth_client):
    resp = await auth_client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_submissions"] == 0
    assert data["completed"] == 0
    assert data["avg_confidence"] == 0.0


@pytest.mark.asyncio
async def test_analytics_by_day_default(auth_client):
    resp = await auth_client.get("/api/v1/analytics/by-day")
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 30
    assert len(data["buckets"]) == 30


@pytest.mark.asyncio
async def test_analytics_by_day_custom(auth_client):
    resp = await auth_client.get("/api/v1/analytics/by-day?days=7")
    assert resp.status_code == 200
    assert resp.json()["days"] == 7
    assert len(resp.json()["buckets"]) == 7


@pytest.mark.asyncio
async def test_analytics_by_day_invalid(auth_client):
    resp = await auth_client.get("/api/v1/analytics/by-day?days=91")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_by_agent_empty(auth_client):
    resp = await auth_client.get("/api/v1/analytics/by-agent")
    assert resp.status_code == 200
    assert resp.json()["agents"] == []
```

### `tests/test_admin.py`
```python
import pytest


@pytest.mark.asyncio
async def test_reset_demo_admin(admin_client):
    resp = await admin_client.post("/api/v1/admin/reset-demo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation"] == "reset_demo"
    assert "deleted_rows" in data


@pytest.mark.asyncio
async def test_reset_demo_non_admin(auth_client):
    resp = await auth_client.post("/api/v1/admin/reset-demo")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_seed_demo_admin(admin_client):
    resp = await admin_client.post("/api/v1/admin/seed-demo")
    assert resp.status_code == 201
    data = resp.json()
    assert data["operation"] == "seed_demo"
    assert data["seeded_rows"] > 0


@pytest.mark.asyncio
async def test_list_users_admin(admin_client):
    resp = await admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert "hashed_password" not in users[0]


@pytest.mark.asyncio
async def test_list_users_non_admin(auth_client):
    resp = await auth_client.get("/api/v1/admin/users")
    assert resp.status_code == 403
```

## Existing Files To Modify
- `tests/conftest.py` — extended with `auth_client` and `admin_client` fixtures

## API Contracts
All tests validate the contracts defined in 006, 007, 016, 030, 034.

## Database Tables
Tests use SQLite in-memory (mirrors schema via SQLAlchemy ORM).

## Business Logic
- OpenAI calls are mocked in inbox tests to prevent real API calls.
- Test database is created fresh before each test and dropped after.
- Admin promotion done directly via DB (not via API).

## Validation Rules
- Tests fail on unexpected status codes.
- Response body schemas validated against expected fields.

## Error Handling
- Test fixtures include cleanup in `yield` patterns.
- `app.dependency_overrides` cleared after each test client fixture.

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
- SQLite doesn't support `gen_random_uuid()` — ORM uses Python `uuid.uuid4()` as default.
- SQLite doesn't support `JSONB` — tests mock the JSONB column as regular JSON.
- SQLite doesn't support `date_trunc('day', ...)` — analytics tests may need SQLAlchemy-dialect-agnostic queries.

## Test Cases
Defined above — 24 tests total across 4 test files.

## Acceptance Criteria
- [ ] All 24 tests pass
- [ ] No real OpenAI API calls made
- [ ] Test suite completes in < 30 seconds
- [ ] Cross-user isolation verified
- [ ] Admin access control verified

## Definition of Done
- `pytest tests/ -v` exits 0
- Coverage ≥ 70% for API endpoint files
- No deprecation warnings from pytest
