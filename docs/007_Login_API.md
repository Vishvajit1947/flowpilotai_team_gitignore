# 007 – Login API

## Objective
Implement the `POST /api/v1/auth/login` endpoint that authenticates an existing user by verifying their email and password, then returns a signed JWT access token. Also implement a `GET /api/v1/auth/me` endpoint that returns the current authenticated user's profile.

## Scope
- `POST /api/v1/auth/login` — credential verification and token issuance
- `GET /api/v1/auth/me` — return current user profile from JWT
- Timing-safe password comparison
- Structured error responses for auth failures

## Out of Scope
- Password reset flow
- Rate limiting (infrastructure concern — handled at reverse proxy)
- Refresh tokens
- Multi-factor authentication

## Functional Requirements
1. Accept `email` and `password` in request body (JSON, not form data).
2. Normalize email to lowercase before DB lookup.
3. If email not found, return 401 with generic message (no user enumeration).
4. If password does not match, return 401 with same generic message.
5. If user's `is_active` is `false`, return 401 with "Account is deactivated".
6. On success, return 200 with `access_token` and `token_type`.
7. `GET /me` returns authenticated user's public profile (no password hash).

## Technical Requirements
- FastAPI route in `app/api/v1/endpoints/auth.py` (same file as register)
- `verify_password` from `app/core/security.py`
- `create_access_token` from `app/core/security.py`
- `get_current_active_user` dependency for `/me` endpoint
- Pydantic response model for user profile

## Folder Structure
```
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── endpoints/
    │           └── auth.py        # Add login + me endpoints
    └── schemas/
        ├── auth.py                # LoginRequest (already exists)
        └── user.py                # UserResponse schema
```

## Files To Create

### `app/schemas/user.py`
```python
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.db.models.user import UserRole


class UserResponse(BaseModel):
    """Public user profile returned by API endpoints."""
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

## Files To Modify

### `app/api/v1/endpoints/auth.py` — add login and me endpoints
```python
import structlog
from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSession, CurrentUser
from app.core.exceptions import ConflictError, AuthenticationError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(body: RegisterRequest, db: DBSession) -> TokenResponse:
    # ... (implementation from 006_Register_API.md)
    pass


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive a JWT token",
    description="Validates email and password, returns a signed JWT access token.",
)
async def login(
    body: LoginRequest,
    db: DBSession,
) -> TokenResponse:
    """
    Login flow:
    1. Find user by email.
    2. Verify password.
    3. Check account is active.
    4. Issue JWT.
    """
    GENERIC_ERROR = "Invalid email or password"

    # 1. Find user
    result = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    # Use a constant-time check even when user doesn't exist
    # to avoid timing-based user enumeration attacks
    if user is None:
        # Still call verify_password to consume constant time
        verify_password("dummy", "$2b$12$dummyhashfortimingnobodywillguessthis")
        logger.info("login_failed_no_user", email=body.email.lower())
        raise AuthenticationError(GENERIC_ERROR)

    # 2. Verify password
    if not verify_password(body.password, user.hashed_password):
        logger.info("login_failed_wrong_password", user_id=str(user.id))
        raise AuthenticationError(GENERIC_ERROR)

    # 3. Check active
    if not user.is_active:
        logger.info("login_failed_inactive", user_id=str(user.id))
        raise AuthenticationError("Account is deactivated")

    # 4. Issue token
    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )

    logger.info("login_success", user_id=str(user.id))
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Returns the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
```

### `app/schemas/auth.py` — add LoginRequest
```python
from pydantic import BaseModel, EmailStr, field_validator
import re


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v
```

## API Contracts

### `POST /api/v1/auth/login`
```
Method:  POST
Path:    /api/v1/auth/login
Auth:    None (public)
Content-Type: application/json
```

### `GET /api/v1/auth/me`
```
Method:  GET
Path:    /api/v1/auth/me
Auth:    Bearer <token>
```

## Request Examples
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SecurePass1"}'

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Response Examples

**POST /login — 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**POST /login — 401 Unauthorized:**
```json
{
  "detail": "Invalid email or password",
  "status_code": 401
}
```

**POST /login — 401 (deactivated):**
```json
{
  "detail": "Account is deactivated",
  "status_code": 401
}
```

**GET /me — 200 OK:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**GET /me — 401 (no token):**
```json
{
  "detail": "Not authenticated",
  "status_code": 401
}
```

## Database Tables
**Reads from:** `users`
- Queries by `email` (indexed)
- No writes

## Business Logic
1. **Anti-enumeration**: The same error message `"Invalid email or password"` is returned whether the email doesn't exist OR the password is wrong. This prevents attackers from discovering which emails are registered.
2. **Timing attack mitigation**: When a user is not found, `verify_password` is still called with a dummy hash to consume approximately the same time as a real comparison (~250ms bcrypt). This prevents timing-based enumeration.
3. **Deactivation**: Deactivated users get a different, specific error message because they already know they have an account. The generic message is only used for non-existent emails / wrong passwords.
4. `/me` is a convenience endpoint that validates the token and returns the full user profile — useful for the frontend to hydrate auth state on page load.

## Validation Rules
| Field | Rule |
|-------|------|
| `email` | Valid email format, normalized to lowercase |
| `password` | Non-empty string |

Login endpoint has minimal validation — heavy validation (password strength) is only on register.

## Error Handling
| Scenario | Status | Detail |
|----------|--------|--------|
| Email not found | 401 | "Invalid email or password" |
| Wrong password | 401 | "Invalid email or password" |
| Account deactivated | 401 | "Account is deactivated" |
| Invalid/missing token on `/me` | 401 | "Could not validate credentials" |
| Expired token on `/me` | 401 | "Token has expired" |
| DB unreachable | 500 | "Internal server error" |

## UI Behavior
Not applicable — backend API only.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Empty password string `""`: rejected by Pydantic validator before bcrypt is called.
- Email `ALICE@EXAMPLE.COM` normalized to `alice@example.com` before DB lookup.
- User deleted between token issuance and `/me` call: `get_current_user` returns 401 (user not found in DB).
- User deactivated between token issuance and `/me` call: `get_current_user` returns 401 (account deactivated).
- Concurrent logins: stateless JWTs allow multiple valid tokens simultaneously — this is expected behavior.

## Test Cases
1. `POST /login` with valid credentials returns 200 and JWT.
2. `POST /login` with wrong password returns 401 with generic message.
3. `POST /login` with non-existent email returns 401 with generic message (same message).
4. `POST /login` with deactivated user returns 401 with "Account is deactivated".
5. `POST /login` with empty password returns 422 (Pydantic validation).
6. `POST /login` with invalid email format returns 422.
7. Login response does not expose `hashed_password`.
8. `GET /me` with valid token returns 200 with correct user profile.
9. `GET /me` with expired token returns 401.
10. `GET /me` with no Authorization header returns 401.
11. `GET /me` with malformed token returns 401.
12. Verify timing difference between found/not-found is < 50ms (bcrypt constant-time).

## Acceptance Criteria
- [ ] `POST /login` returns 200 + JWT for valid credentials
- [ ] Wrong password and missing email both return same error message
- [ ] Deactivated users get specific error message
- [ ] `GET /me` returns user profile for valid token
- [ ] `hashed_password` never appears in any response
- [ ] Anti-enumeration timing mitigation implemented

## Definition of Done
- All test cases pass
- No mypy errors
- `LoginRequest` and `UserResponse` schemas exported
- `login` and `get_me` endpoints registered in auth router
