# 042 – Environment Config

## Objective
Document and implement the complete environment variable configuration for both frontend and backend, including validation at startup, a configuration documentation guide, and environment-specific configurations for development, staging, and production.

## Scope
- `backend/app/core/config.py` — complete Pydantic settings (extends 003)
- `frontend/.env.local.example` — complete frontend env template
- `backend/.env.example` — complete backend env template
- `backend/app/core/config_validator.py` — startup validation checks
- Environment tier documentation

## Out of Scope
- Secrets management (AWS Secrets Manager, Vault) — documented as future work
- CI/CD env injection (045)

## Functional Requirements
1. Application fails to start if required environment variables are missing.
2. Startup logs show which environment tier is active (dev/staging/prod).
3. All environment variables documented with type, default, and description.
4. `DEBUG=true` enables Swagger UI and verbose logging.
5. `DEBUG=false` (production) disables Swagger and uses JSON logging.

## Technical Requirements
- Pydantic Settings v2 with field validators
- Required fields: `SECRET_KEY`, `DATABASE_URL`, `OPENAI_API_KEY`, `SUPABASE_*`
- Optional with defaults: `DEBUG`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

## Folder Structure
```
backend/
├── app/
│   └── core/
│       ├── config.py           # Pydantic settings (from 003, extended here)
│       └── config_validator.py # Startup validation
├── .env.example
└── .env.development.example

frontend/
├── .env.local.example
└── .env.production.example
```

## Files To Create

### `backend/app/core/config_validator.py`
```python
"""
Startup configuration validator.
Checks that all required settings are present and valid before the app starts.
"""
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


def validate_config() -> None:
    """
    Run at application startup to validate configuration.
    Raises ValueError if any required configuration is invalid.
    """
    errors = []

    # SECRET_KEY strength check
    if len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY must be at least 32 characters long")
    if settings.SECRET_KEY == "change-me-in-production-use-256-bit-random-string":
        if not settings.DEBUG:
            errors.append("SECRET_KEY must be changed from the default value in production")
        else:
            logger.warning("using_default_secret_key", env="development")

    # OpenAI API key format check
    if not settings.OPENAI_API_KEY.startswith("sk-"):
        errors.append("OPENAI_API_KEY does not appear to be valid (should start with 'sk-')")

    # Database URL check
    if not any(
        settings.DATABASE_URL.startswith(prefix)
        for prefix in ("postgresql://", "postgres://", "postgresql+asyncpg://")
    ):
        errors.append("DATABASE_URL must be a PostgreSQL connection string")

    # Supabase URL format check
    if not settings.SUPABASE_URL.startswith("https://"):
        errors.append("SUPABASE_URL must be an HTTPS URL")

    if errors:
        for error in errors:
            logger.error("config_validation_error", error=error)
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")

    logger.info(
        "config_validated",
        debug=settings.DEBUG,
        algorithm=settings.ALGORITHM,
        token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        allowed_origins=settings.ALLOWED_ORIGINS,
    )
```

### Complete `backend/.env.example`
```bash
# ── Application ────────────────────────────────────────────────────────────────
APP_NAME=FlowPilot AI
DEBUG=false
# Set to true in development: enables Swagger UI, verbose logging, hot reload

# ── Security ──────────────────────────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-me-generate-a-256-bit-random-hex-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Database ──────────────────────────────────────────────────────────────────
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://postgres:password@localhost:5432/flowpilot

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_KEY=your-service-role-secret-key

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-your-openai-api-key-here

# ── CORS ──────────────────────────────────────────────────────────────────────
# JSON array of allowed origins
# Development: ["http://localhost:3000"]
# Production: ["https://your-domain.com"]
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### `backend/.env.development.example`
```bash
DEBUG=true
SECRET_KEY=change-me-in-production-use-256-bit-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
DATABASE_URL=postgresql://postgres:password@localhost:5432/flowpilot_dev
SUPABASE_URL=https://dev-project.supabase.co
SUPABASE_KEY=dev-anon-key
SUPABASE_SERVICE_KEY=dev-service-key
OPENAI_API_KEY=sk-your-key
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:3001"]
```

### Complete `frontend/.env.local.example`
```bash
# ── API ────────────────────────────────────────────────────────────────────────
# Backend API base URL (without /api/v1 suffix)
NEXT_PUBLIC_API_URL=http://localhost:8000

# ── App ────────────────────────────────────────────────────────────────────────
NEXT_PUBLIC_APP_NAME=FlowPilot AI

# ── Supabase (public keys only — no service role key on frontend) ──────────────
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-public-key
```

### `frontend/.env.production.example`
```bash
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_APP_NAME=FlowPilot AI
NEXT_PUBLIC_SUPABASE_URL=https://prod-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=prod-anon-key
```

## Files To Modify

### `main.py` — call `validate_config()` at startup
```python
from app.core.config_validator import validate_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()  # Fail fast if config is invalid
    logger.info("startup", app=settings.APP_NAME)
    yield
    await engine.dispose()
```

## API Contracts
Not applicable.

## Request Examples
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
# Output example: a3f5e8d2c1b4a7e6f9d8c3b2a1e4f7d6...
```

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
### Required Environment Variables
| Variable | Required | Default | Type | Description |
|----------|----------|---------|------|-------------|
| `SECRET_KEY` | YES | — | string (≥32 chars) | JWT signing secret |
| `DATABASE_URL` | YES | — | postgres URL | PostgreSQL connection |
| `SUPABASE_URL` | YES | — | HTTPS URL | Supabase project URL |
| `SUPABASE_KEY` | YES | — | string | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | YES | — | string | Supabase service role key |
| `OPENAI_API_KEY` | YES | — | sk-... string | OpenAI API key |
| `DEBUG` | no | `false` | bool | Enable debug mode |
| `ALGORITHM` | no | `HS256` | string | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `60` | int | Token lifetime |
| `ALLOWED_ORIGINS` | no | `["http://localhost:3000"]` | JSON array | CORS origins |

### Frontend Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | YES | Backend URL |
| `NEXT_PUBLIC_SUPABASE_URL` | YES | Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | YES | Supabase public key |
| `NEXT_PUBLIC_APP_NAME` | no | App display name |

## Validation Rules
- `SECRET_KEY` must be ≥ 32 characters.
- `SECRET_KEY` cannot be default value in production.
- `OPENAI_API_KEY` must start with `sk-`.
- `DATABASE_URL` must be a PostgreSQL URL.
- `SUPABASE_URL` must be HTTPS.

## Error Handling
- Missing required variable → `pydantic_settings.ValidationError` at import time.
- Invalid value → `ValueError` from `validate_config()` at startup.
- Both cause application to refuse to start (fail-fast).

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
- `ALLOWED_ORIGINS` as comma-separated string (not JSON): `parse_cors` validator handles both formats.
- `DATABASE_URL` with `postgres://` scheme (Heroku-style): config.py converts to `postgresql+asyncpg://`.
- `ACCESS_TOKEN_EXPIRE_MINUTES=0`: technically valid but produces immediately-expired tokens — documented warning.
- `NEXT_PUBLIC_*` variables baked into frontend build at build time — cannot be changed at runtime.

## Test Cases
1. Missing `SECRET_KEY` causes startup failure with clear error message.
2. Short `SECRET_KEY` (< 32 chars) causes validation error.
3. Default `SECRET_KEY` in production causes validation error.
4. Invalid `OPENAI_API_KEY` (no `sk-` prefix) causes validation error.
5. Valid config logs `config_validated` with key settings.
6. `ALLOWED_ORIGINS` as comma-separated string is parsed correctly.

## Acceptance Criteria
- [ ] Application refuses to start with missing/invalid config
- [ ] Default secret key blocked in production
- [ ] All required env vars documented
- [ ] `.env.example` covers all configuration options
- [ ] Startup logs show active configuration tier

## Definition of Done
- All test cases pass
- `validate_config()` called in lifespan startup
- Both `.env.example` files complete and accurate
- `NEXT_PUBLIC_*` variables never include secrets
