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
