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
