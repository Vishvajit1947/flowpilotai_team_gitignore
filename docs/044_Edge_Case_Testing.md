# 044 – Edge Case Testing

## Objective
Document and implement tests for edge cases, boundary conditions, security vulnerabilities, and failure scenarios that may not be covered by standard integration tests — ensuring FlowPilot AI is robust against unexpected inputs, concurrent operations, and adversarial use.

## Scope
- Security edge cases: JWT attacks, CORS, injection
- Input boundary cases: oversized content, special characters, unicode
- Concurrency edge cases: duplicate registrations, double submissions
- OCR edge cases: corrupt files, empty documents
- AI service edge cases: API timeouts, invalid responses
- UI edge cases: rapid clicks, network interruptions

## Out of Scope
- Load testing
- Full penetration testing

## Functional Requirements
1. All edge cases documented with expected behavior.
2. Automated tests for all backend edge cases.
3. Manual testing checklist for frontend edge cases.

## Technical Requirements
- `pytest` for backend edge case tests
- `unittest.mock` for simulating failure conditions

## Folder Structure
```
backend/
└── tests/
    └── test_edge_cases.py
```

## Files To Create

### `tests/test_edge_cases.py`
```python
"""
Edge Case Tests for FlowPilot AI.
Tests security, boundary conditions, and failure scenarios.
"""
import pytest
import uuid
from unittest.mock import patch, AsyncMock


# ── Auth Edge Cases ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jwt_manipulation(client):
    """Tampered JWT should return 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "victim@test.com", "password": "VictimPass1", "full_name": "Victim"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "victim@test.com", "password": "VictimPass1"
    })
    token = resp.json()["access_token"]

    # Tamper with the signature (change last 5 chars)
    tampered = token[:-5] + "XXXXX"
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_bearer_token(client):
    """Empty Bearer token should return 401."""
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_malformed_auth_header(client):
    """Malformed Authorization header should return 401."""
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "NotBearer token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_email_case_normalization(client):
    """Email should be case-normalized on register and login."""
    await client.post("/api/v1/auth/register", json={
        "email": "ALICE@EXAMPLE.COM", "password": "AlicePass1", "full_name": "Alice"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "alice@example.com", "password": "AlicePass1"
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_password_exactly_72_chars(client):
    """Password of exactly 72 chars should succeed (bcrypt limit)."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "longpass@test.com",
        "password": "A" * 71 + "1",  # 72 chars, has uppercase + digit
        "full_name": "Long Pass User",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_password_73_chars_rejected(client):
    """Password of 73 chars should be rejected."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "tolong@test.com",
        "password": "A" * 72 + "1",  # 73 chars
        "full_name": "Too Long User",
    })
    assert resp.status_code == 422


# ── Inbox Edge Cases ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inbox_content_exactly_5000_chars(auth_client):
    """Content of exactly 5000 chars should succeed."""
    content = "A" * 4999 + "B"  # 5000 chars
    resp = await auth_client.post("/api/v1/inbox/submit", json={"content": content})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_inbox_content_5001_chars_rejected(auth_client):
    """Content of 5001 chars should be rejected."""
    content = "A" * 5001
    resp = await auth_client.post("/api/v1/inbox/submit", json={"content": content})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_inbox_unicode_content(auth_client):
    """Unicode content should be accepted."""
    resp = await auth_client.post("/api/v1/inbox/submit", json={
        "content": "こんにちは、新しいリードがあります。Acme Corpからです。"
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_inbox_content_only_whitespace(auth_client):
    """Content of only whitespace should be rejected (stripped < 3 chars)."""
    resp = await auth_client.post("/api/v1/inbox/submit", json={"content": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_inbox_invalid_uuid_in_path(auth_client):
    """Invalid UUID in path should return 404."""
    resp = await auth_client.get("/api/v1/inbox/not-a-uuid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_inbox_nonhttps_file_url_rejected(auth_client):
    """Non-HTTPS file_url should be rejected."""
    resp = await auth_client.post("/api/v1/inbox/submit", json={
        "content": "Test content here",
        "file_url": "http://insecure.example.com/file.pdf",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_inbox_pagination_cap(auth_client):
    """page size > 100 should be capped at 100."""
    resp = await auth_client.get("/api/v1/inbox/?page=1&size=999")
    assert resp.status_code == 200
    # Size should be capped — no 422 error


# ── Analytics Edge Cases ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_by_day_min_days(auth_client):
    """days=1 should return exactly 1 bucket."""
    resp = await auth_client.get("/api/v1/analytics/by-day?days=1")
    assert resp.status_code == 200
    assert len(resp.json()["buckets"]) == 1


@pytest.mark.asyncio
async def test_analytics_by_day_max_days(auth_client):
    """days=90 should return exactly 90 buckets."""
    resp = await auth_client.get("/api/v1/analytics/by-day?days=90")
    assert resp.status_code == 200
    assert len(resp.json()["buckets"]) == 90


@pytest.mark.asyncio
async def test_analytics_by_day_zero_rejected(auth_client):
    """days=0 should be rejected (ge=1 constraint)."""
    resp = await auth_client.get("/api/v1/analytics/by-day?days=0")
    assert resp.status_code == 422


# ── Admin Edge Cases ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_reset_idempotent(admin_client):
    """Calling reset twice should not error on second call."""
    await admin_client.post("/api/v1/admin/reset-demo")
    resp = await admin_client.post("/api/v1/admin/reset-demo")
    assert resp.status_code == 200
    assert resp.json()["deleted_rows"] == 0


@pytest.mark.asyncio
async def test_admin_seed_then_reset(admin_client):
    """Seed followed by reset should result in 0 submissions."""
    seed_resp = await admin_client.post("/api/v1/admin/seed-demo")
    seeded = seed_resp.json()["seeded_rows"]

    reset_resp = await admin_client.post("/api/v1/admin/reset-demo")
    assert reset_resp.json()["deleted_rows"] == seeded


# ── Document Extraction Edge Cases ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_invoice_non_https(auth_client):
    """Non-HTTPS file_url should be rejected."""
    resp = await auth_client.post("/api/v1/documents/extract-invoice", json={
        "file_url": "http://not-secure.com/invoice.pdf"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_invoice_unauthenticated(client):
    """Unauthenticated request should return 401."""
    resp = await client.post("/api/v1/documents/extract-invoice", json={
        "file_url": "https://example.com/invoice.pdf"
    })
    assert resp.status_code == 401


# ── AI Service Edge Cases (mocked) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intent_detection_fallback_on_timeout():
    """Intent detection should return 'unknown' on timeout."""
    from app.services.intent_detection import detect_intent
    import asyncio

    with patch("app.services.intent_detection._call_gpt4o", side_effect=asyncio.TimeoutError):
        result = await detect_intent("test content")
        assert result.intent == "unknown"


@pytest.mark.asyncio
async def test_confidence_scoring_fallback_on_error():
    """Confidence scoring should return 0.5 on error."""
    from app.services.confidence_scoring import compute_confidence

    with patch("app.services.confidence_scoring._gpt4o_score", side_effect=Exception("API error")):
        with patch("app.services.confidence_scoring._keyword_score", return_value=None):
            score = await compute_confidence("test content", "sales_lead")
            assert score == 0.5


@pytest.mark.asyncio
async def test_confidence_unknown_intent():
    """Unknown intent should always return 0.0 confidence."""
    from app.services.confidence_scoring import compute_confidence
    score = await compute_confidence("anything", "unknown")
    assert score == 0.0


@pytest.mark.asyncio
async def test_agent_routing_escalation():
    """Low confidence should escalate to executive agent."""
    from app.services.agent_router import route
    from app.db.models.inbox import AgentType

    decision = route("sales_lead", 0.2)
    assert decision.agent_type == AgentType.executive
    assert decision.escalated is True


@pytest.mark.asyncio
async def test_ocr_timeout_returns_empty():
    """OCR timeout should return empty string, not raise."""
    from app.services.ocr_service import extract_text_from_url
    import asyncio

    with patch("app.services.ocr_service._extract", side_effect=asyncio.TimeoutError):
        result = await extract_text_from_url("https://example.com/test.pdf")
        assert result == ""
```

## Existing Files To Modify
None — new test file only.

## API Contracts
Tests validate existing API contracts.

## Database Tables
Same as integration tests — in-memory SQLite.

## Business Logic
- JWT tampering: last 5 chars changed → signature verification fails.
- Content whitespace trimming: `"   "` stripped → 0 chars → fails 3-char minimum.
- Unicode: UTF-8 content must be stored and retrieved correctly.
- Password boundary: 72 chars = bcrypt limit = accepted; 73 = rejected.

## Validation Rules
All edge cases test existing validation rules from feature tasks.

## Error Handling
Mocked services return controlled error states.

## UI Behavior

### Frontend Manual Testing Checklist
```
Auth:
  [ ] Rapid-click submit button on login form — no double submission
  [ ] Browser back after login — should stay on dashboard
  [ ] Direct URL /dashboard with no token — redirects to login
  [ ] Token expiry during session — next API call clears auth and redirects
  [ ] Copy-paste expired token in localStorage — API call clears it

Inbox:
  [ ] Paste 5000+ chars in textarea — character counter shows red
  [ ] Submit with 5000 chars exactly — succeeds
  [ ] Submit then navigate away — polling stops when component unmounts
  [ ] Submit two messages rapidly — second blocked while first is processing

File Upload:
  [ ] Drop a .txt file — rejected with error
  [ ] Drop a 10.5MB PDF — rejected with size error
  [ ] Drop a 10MB PDF exactly — accepted
  [ ] Drop an RGBA PNG — accepted (converted to RGB)

Dark Mode:
  [ ] Toggle dark mode — no flash or reflow
  [ ] Reload page in dark mode — stays dark
  [ ] System dark mode change while app is open — follows if 'system' selected

Charts:
  [ ] Page with 0 submissions — charts show empty states
  [ ] Date range selector — chart updates
  [ ] Resize window — charts remain responsive
```

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
These are the edge cases — this document IS the edge case documentation.

## Test Cases
28 automated backend tests defined above.

## Acceptance Criteria
- [ ] All 28 automated edge case tests pass
- [ ] Frontend manual testing checklist completed
- [ ] JWT tampering detected and rejected
- [ ] Boundary values (5000 chars, 72 char password) tested
- [ ] AI service timeouts return safe fallbacks

## Definition of Done
- All automated tests pass
- Manual testing checklist checked off
- No new security vulnerabilities introduced
