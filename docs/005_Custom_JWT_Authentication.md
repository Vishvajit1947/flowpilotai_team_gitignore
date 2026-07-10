# 005 – Custom JWT Authentication

## Objective
Implement the core authentication security layer: password hashing with bcrypt, JWT access token creation and verification using `python-jose`, and the FastAPI dependency that extracts and validates the current user from a Bearer token on every protected request.

## Scope
- `app/core/security.py` — `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`
- `app/api/deps.py` — `get_current_user`, `get_current_active_user`, `require_admin` dependencies
- JWT payload schema (Pydantic)
- Token expiry, algorithm, and secret key configuration

## Out of Scope
- Register endpoint (006)
- Login endpoint (007)
- Frontend auth (008)
- Refresh token mechanism (not in scope for v1)

## Functional Requirements
1. Passwords must be hashed using bcrypt with a cost factor of 12.
2. JWT tokens must be signed with HS256 algorithm using a configurable secret key.
3. JWT payload must include `sub` (user ID as string), `email`, `role`, and `exp` (expiry).
4. `get_current_user` dependency must verify the token and return the `User` ORM object.
5. `require_admin` dependency must raise 403 if the authenticated user's role is not `admin`.
6. Expired tokens must return HTTP 401 with detail `"Token has expired"`.
7. Malformed tokens must return HTTP 401 with detail `"Could not validate credentials"`.

## Technical Requirements
- `python-jose[cryptography]` 3.3.0
- `bcrypt` 4.1.3 (passlib compatibility note: use bcrypt directly, not passlib)
- FastAPI `Depends` system for dependency injection
- `OAuth2PasswordBearer` scheme for Swagger UI compatibility
- Token expiry from `settings.ACCESS_TOKEN_EXPIRE_MINUTES`

## Folder Structure
```
backend/
└── app/
    ├── core/
    │   └── security.py        # Password + JWT utilities
    ├── api/
    │   └── deps.py            # FastAPI auth dependencies
    └── schemas/
        └── auth.py            # TokenPayload Pydantic model
```

## Files To Create

### `app/schemas/auth.py`
```python
from pydantic import BaseModel
from typing import Optional


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str        # user ID (UUID as string)
    email: str
    role: str
    exp: Optional[int] = None   # UNIX timestamp, set by python-jose


class TokenResponse(BaseModel):
    """Response body for login endpoint."""
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str
```

## Files To Modify

### `app/core/security.py` (complete implementation)
```python
"""
Security utilities for FlowPilot AI.

- Password hashing: bcrypt cost factor 12
- JWT: HS256, python-jose
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import JWTError, ExpiredSignatureError, jwt
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


# ─── Password Hashing ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt (cost=12)."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: UUID string of the user
        email:   user's email address
        role:    'admin' or 'user'
        expires_delta: override default expiry

    Returns:
        Encoded JWT string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    logger.debug("token_created", user_id=user_id, expires_at=expire.isoformat())
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        AuthenticationError: if token is invalid or expired

    Returns:
        Decoded payload dict
    """
    from app.core.exceptions import AuthenticationError

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except ExpiredSignatureError:
        logger.info("token_expired")
        raise AuthenticationError("Token has expired")
    except JWTError as exc:
        logger.warning("token_invalid", error=str(exc))
        raise AuthenticationError("Could not validate credentials")
```

### `app/api/deps.py` (extended from 003)
```python
"""
FastAPI dependency injection functions.
"""
from typing import Annotated
import structlog
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models.user import User, UserRole

logger = structlog.get_logger(__name__)

# Type alias for injected DB session
DBSession = Annotated[AsyncSession, Depends(get_db)]

# OAuth2 scheme — token extracted from Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession,
) -> User:
    """
    FastAPI dependency: validates JWT and returns the authenticated User.

    Raises:
        AuthenticationError (401) if token is missing, invalid, or expired.
        AuthenticationError (401) if user_id in token does not exist in DB.
        AuthenticationError (401) if user is inactive.
    """
    payload = decode_access_token(token)  # raises AuthenticationError on failure

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token payload missing subject")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Token subject is not a valid UUID")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("token_user_not_found", user_id=user_id_str)
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Alias for get_current_user — for explicitness in route signatures."""
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    FastAPI dependency: ensures the current user has role='admin'.

    Raises:
        AuthorizationError (403) if user is not admin.
    """
    if current_user.role != UserRole.admin:
        raise AuthorizationError("Admin access required")
    return current_user


# Convenient type aliases for route handlers
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
```

## API Contracts
These utilities are not endpoints themselves. They are consumed by:
- `POST /api/v1/auth/register` (006)
- `POST /api/v1/auth/login` (007)
- All protected endpoints via `Depends(get_current_user)`

## Request Examples
Not applicable (utility module).

## Response Examples
Token response shape (used by login endpoint):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Decoded JWT payload:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "role": "user",
  "iat": 1700000000,
  "exp": 1700003600
}
```

## Database Tables
Reads from `users` table (SELECT by id).

## Business Logic
1. Password hashing: bcrypt with cost factor 12. This takes ~250ms which is intentional (brute-force resistance).
2. JWT includes `role` so downstream services don't need an extra DB query for RBAC.
3. `get_current_user` always queries the DB to catch deactivated accounts — the JWT alone is not sufficient.
4. Token expiry is sliding from issue time, not last activity (simple stateless implementation).

## Validation Rules
- Plain password must be a non-empty string before hashing.
- JWT `sub` must be a valid UUID string — invalid format → 401.
- `role` in JWT must match one of the `UserRole` enum values — mismatched role in DB vs token is handled by the DB query (we trust the DB, not the JWT role for authorization).

## Error Handling
| Scenario | Error | HTTP |
|----------|-------|------|
| Expired token | `AuthenticationError("Token has expired")` | 401 |
| Invalid token signature | `AuthenticationError("Could not validate credentials")` | 401 |
| No `sub` in payload | `AuthenticationError("Token payload missing subject")` | 401 |
| Invalid UUID in `sub` | `AuthenticationError("Token subject is not a valid UUID")` | 401 |
| User not found in DB | `AuthenticationError("User not found")` | 401 |
| User deactivated | `AuthenticationError("User account is deactivated")` | 401 |
| Non-admin accessing admin route | `AuthorizationError("Admin access required")` | 403 |

All errors return JSON: `{"detail": "<message>", "status_code": N}`

## UI Behavior
Not applicable — backend utility module.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- bcrypt `$2b$` vs `$2a$` prefix: `bcrypt.checkpw` handles both transparently.
- Token issued for a deleted user: user lookup in `get_current_user` returns `None` → 401.
- Clock skew: `python-jose` allows 0 seconds of leeway by default. If needed, use `options={"leeway": 10}` in `jwt.decode()`.
- Very long passwords (>72 bytes): bcrypt truncates at 72 bytes. Document this limitation; do not silently truncate in code — validate max length 72 at the API layer (006, 007).

## Test Cases
1. `hash_password("mypassword")` returns a string starting with `$2b$`.
2. `verify_password("mypassword", hash_password("mypassword"))` returns `True`.
3. `verify_password("wrong", hash_password("mypassword"))` returns `False`.
4. `create_access_token("uuid", "a@b.com", "user")` returns a JWT string.
5. `decode_access_token(create_access_token(...))` returns payload with matching `sub`.
6. Token with `exp` in the past raises `AuthenticationError("Token has expired")`.
7. Tampered token raises `AuthenticationError("Could not validate credentials")`.
8. `get_current_user` with valid token and existing user returns the User object.
9. `get_current_user` with valid token but deleted user raises `AuthenticationError`.
10. `require_admin` with a `user`-role user raises `AuthorizationError`.
11. `require_admin` with an `admin`-role user returns the User object.

## Acceptance Criteria
- [ ] bcrypt hashing works with cost factor 12
- [ ] `verify_password` returns False for wrong password
- [ ] JWT tokens encode user_id, email, role, exp
- [ ] Expired tokens return 401 with correct detail message
- [ ] Invalid tokens return 401
- [ ] Deactivated users return 401
- [ ] Non-admin users accessing admin routes return 403
- [ ] All dependencies injectable via FastAPI `Depends`

## Definition of Done
- All test cases pass
- No mypy errors
- `bcrypt` import from `bcrypt` directly (not `passlib`) to avoid compatibility issues
- `TokenPayload`, `TokenResponse`, `RegisterRequest`, `LoginRequest` exported from `app/schemas/auth.py`
