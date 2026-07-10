# 006 – Register API

## Objective
Implement the `POST /api/v1/auth/register` endpoint that accepts new user credentials, validates them, creates a hashed password, persists the user record to the database, and returns a JWT access token so the user is immediately authenticated after registration.

## Scope
- `POST /api/v1/auth/register` endpoint
- Input validation (email format, password strength, name length)
- Duplicate email conflict handling
- Password hashing via `security.hash_password`
- User record creation in `users` table
- JWT token generation and response

## Out of Scope
- Email verification (not in v1 scope)
- OAuth / social login
- Login endpoint (007)
- Frontend registration form (008)

## Functional Requirements
1. Accept `email`, `password`, `full_name` in request body.
2. Validate email format using Pydantic `EmailStr`.
3. Validate password: minimum 8 characters, at least one uppercase letter, one digit.
4. Validate `full_name`: 2–100 characters, no leading/trailing whitespace.
5. Return HTTP 409 if email already exists.
6. Hash password with bcrypt before storing.
7. Return HTTP 201 with `access_token` and `token_type` on success.
8. Never return the hashed password in any response.

## Technical Requirements
- FastAPI route in `app/api/v1/endpoints/auth.py`
- Pydantic v2 request validation with custom validators
- `pydantic[email]` for `EmailStr` (install `email-validator`)
- SQLAlchemy async session via `get_db` dependency
- `hash_password` from `app/core/security.py`
- `create_access_token` from `app/core/security.py`

## Folder Structure
```
backend/
└── app/
    ├── api/
    │   └── v1/
    │       ├── router.py              # Include auth router
    │       └── endpoints/
    │           ├── __init__.py
    │           └── auth.py            # Register + Login routes
    └── schemas/
        └── auth.py                    # RegisterRequest, TokenResponse
```

## Files To Create

### `app/api/v1/endpoints/auth.py`
```python
import structlog
from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSession
from app.core.exceptions import ConflictError, ValidationError
from app.core.security import create_access_token, hash_password
from app.db.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new user and returns a JWT access token.",
)
async def register(
    body: RegisterRequest,
    db: DBSession,
) -> TokenResponse:
    """
    Register endpoint:
    1. Check for duplicate email.
    2. Hash password.
    3. Persist user.
    4. Return access token.
    """
    # 1. Check existing email
    result = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    # 2. Hash password
    hashed = hash_password(body.password)

    # 3. Create user
    user = User(
        email=body.email.lower(),
        full_name=body.full_name.strip(),
        hashed_password=hashed,
    )
    db.add(user)
    try:
        await db.flush()   # get generated UUID before commit
        await db.refresh(user)
    except IntegrityError:
        # Race condition: another request registered same email concurrently
        raise ConflictError("An account with this email already exists")

    # 4. Generate token
    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )

    logger.info("user_registered", user_id=str(user.id), email=user.email)

    return TokenResponse(access_token=token)
```

## Files To Modify

### `app/schemas/auth.py` — add RegisterRequest validation
```python
from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 72:
            raise ValueError("Password must be at most 72 characters (bcrypt limit)")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Full name must be at most 100 characters")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

### `app/api/v1/router.py` — include auth router
```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
```

### `requirements.txt` — add email validator
```
email-validator==2.1.1
```

## API Contracts

### `POST /api/v1/auth/register`
```
Method:  POST
Path:    /api/v1/auth/register
Auth:    None (public)
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "alice@example.com",
  "password": "SecurePass1",
  "full_name": "Alice Smith"
}
```

**Success Response — HTTP 201:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error — HTTP 409 (duplicate email):**
```json
{
  "detail": "An account with this email already exists",
  "status_code": 409
}
```

**Error — HTTP 422 (validation):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "password"],
      "msg": "Value error, Password must be at least 8 characters",
      "input": "short"
    }
  ]
}
```

## Request Examples
```bash
# Successful registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SecurePass1","full_name":"Alice Smith"}'

# Duplicate email
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"AnotherPass1","full_name":"Alice"}'
```

## Response Examples

**201 Created:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJlbWFpbCI6ImFsaWNlQGV4YW1wbGUuY29tIiwicm9sZSI6InVzZXIiLCJpYXQiOjE3MDAwMDAwMDAsImV4cCI6MTcwMDAwMzYwMH0.signature",
  "token_type": "bearer"
}
```

## Database Tables
**Writes to:** `users`
- `id` — auto-generated UUID
- `email` — normalized to lowercase
- `full_name` — trimmed
- `hashed_password` — bcrypt hash
- `role` — defaults to `'user'`
- `is_active` — defaults to `true`
- `created_at`, `updated_at` — server defaults

## Business Logic
1. Email is always normalized to lowercase before storage and comparison.
2. Full name is trimmed of whitespace before storage.
3. The first user registered is NOT automatically promoted to admin — admin role must be set manually in the database by a DBA or via the admin reset endpoint (034).
4. After successful `flush()`, the user's UUID is available without waiting for a full commit — this allows generating the token before the session commits.

## Validation Rules
| Field | Rule | Error Message |
|-------|------|---------------|
| `email` | Valid email format | Pydantic EmailStr error |
| `email` | Unique in DB | "An account with this email already exists" |
| `password` | Min 8 characters | "Password must be at least 8 characters" |
| `password` | Max 72 characters | "Password must be at most 72 characters" |
| `password` | At least one uppercase | "Password must contain at least one uppercase letter" |
| `password` | At least one digit | "Password must contain at least one digit" |
| `full_name` | 2–100 characters | "Full name must be at least/most N characters" |

## Error Handling
| Scenario | Status | Response |
|----------|--------|----------|
| Duplicate email (pre-check) | 409 | `ConflictError` |
| Duplicate email (race condition) | 409 | `ConflictError` (IntegrityError catch) |
| Invalid email format | 422 | Pydantic validation error |
| Weak password | 422 | Pydantic validation error |
| Short full_name | 422 | Pydantic validation error |
| DB connection failure | 500 | Unhandled exception → 500 |

## UI Behavior
Not applicable — backend API only. Frontend registration form is covered in 008_Auth_Context.md.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Two simultaneous registrations with the same email: pre-check passes for both, `IntegrityError` on second `flush()` → 409 caught correctly.
- Email `ALICE@EXAMPLE.COM` and `alice@example.com` are treated as the same account.
- Password containing unicode characters: bcrypt handles UTF-8 encoding — tested explicitly.
- Password exactly 72 characters: accepted. Password 73 characters: rejected.
- `full_name` with only spaces: after `.strip()` results in empty string → fails min-length check.

## Test Cases
1. `POST /register` with valid data returns 201 and a JWT token.
2. Decoded JWT contains correct `sub`, `email`, `role` fields.
3. `POST /register` with same email twice returns 409.
4. `POST /register` with password `"short"` returns 422.
5. `POST /register` with password `"alllowercase1"` (no uppercase) returns 422.
6. `POST /register` with password `"NoDigits!"` (no digit) returns 422.
7. `POST /register` with 73-character password returns 422.
8. `POST /register` with invalid email `"notanemail"` returns 422.
9. `POST /register` with `full_name` `"A"` (1 char) returns 422.
10. `POST /register` normalizes email to lowercase in DB.
11. `POST /register` stores bcrypt hash (starts with `$2b$`) in DB.
12. Response body does NOT contain `hashed_password`.

## Acceptance Criteria
- [ ] `POST /api/v1/auth/register` returns 201 with JWT on valid input
- [ ] Duplicate email returns 409
- [ ] All validation rules enforced
- [ ] Email stored as lowercase
- [ ] Password stored as bcrypt hash
- [ ] Hashed password never exposed in response

## Definition of Done
- All test cases pass
- No mypy errors
- Email validator library installed (`email-validator`)
- Auth router included in `api_router`
