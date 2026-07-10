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
