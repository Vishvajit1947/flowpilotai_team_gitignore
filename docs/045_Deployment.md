# 045 – Deployment

## Objective
Document the complete deployment process for FlowPilot AI on Vercel (frontend) and Railway/Render (backend), including environment variable configuration, database migration execution, CI/CD pipeline setup with GitHub Actions, and post-deployment verification steps.

## Scope
- Frontend deployment to Vercel
- Backend deployment to Railway (or Render as alternative)
- GitHub Actions CI/CD pipeline
- Database migration execution in CI
- Health check verification
- Environment variable management

## Out of Scope
- Kubernetes/EKS deployment
- Multi-region deployment
- Blue/green deployments
- CDN configuration beyond Vercel defaults

## Functional Requirements
1. `git push main` triggers automatic deployment to production.
2. CI pipeline runs tests before deploying.
3. Database migrations run automatically on backend deploy.
4. Frontend preview deployments for every PR.
5. Deployment completes in under 10 minutes.
6. Rollback procedure documented.

## Technical Requirements
- GitHub Actions 2.x
- Vercel CLI / Vercel GitHub integration
- Railway CLI / Railway GitHub integration
- Alembic for migration execution
- `pytest` for CI test execution

## Folder Structure
```
FlowPilot-AI/
└── .github/
    └── workflows/
        ├── ci.yml        # Run tests on every PR
        └── deploy.yml    # Deploy on push to main
```

## Files To Create

### `.github/workflows/ci.yml`
```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test-backend:
    name: Backend Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          sudo apt-get install -y tesseract-ocr poppler-utils

      - name: Run linting
        working-directory: ./backend
        run: |
          black --check .
          isort --check .

      - name: Run tests
        working-directory: ./backend
        env:
          SECRET_KEY: test-secret-key-for-ci-at-least-32-chars
          DATABASE_URL: sqlite+aiosqlite:///./test.db
          SUPABASE_URL: https://test.supabase.co
          SUPABASE_KEY: test-key
          SUPABASE_SERVICE_KEY: test-service-key
          OPENAI_API_KEY: sk-test-key-for-ci-not-real
          ALLOWED_ORIGINS: '["http://localhost:3000"]'
          DEBUG: "true"
        run: pytest tests/ -v --tb=short

  test-frontend:
    name: Frontend Type Check & Lint
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Type check
        working-directory: ./frontend
        run: npm run type-check

      - name: Lint
        working-directory: ./frontend
        run: npm run lint
```

### `.github/workflows/deploy.yml`
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    name: Deploy Backend to Railway
    runs-on: ubuntu-latest
    needs: []  # Independent of frontend deploy

    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Run Alembic migrations
        working-directory: ./backend
        env:
          DATABASE_URL: ${{ secrets.PROD_DATABASE_URL }}
          SECRET_KEY: ${{ secrets.PROD_SECRET_KEY }}
          SUPABASE_URL: ${{ secrets.PROD_SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.PROD_SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.PROD_SUPABASE_SERVICE_KEY }}
          OPENAI_API_KEY: ${{ secrets.PROD_OPENAI_API_KEY }}
        run: |
          pip install alembic asyncpg pydantic-settings psycopg2-binary
          alembic upgrade head

      - name: Deploy to Railway
        working-directory: ./backend
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service flowpilot-backend --detach

  deploy-frontend:
    name: Deploy Frontend to Vercel
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
          vercel-args: '--prod'
```

## Existing Files To Modify
- `backend/Dockerfile` — add migration command to startup (or run in deploy script)
- `backend/main.py` — ensure `validate_config()` runs at startup

## Deployment Steps

### Initial Setup (one-time)

#### 1. Supabase Setup
```bash
# 1. Create project at supabase.com
# 2. Note: Project URL, anon key, service role key
# 3. Run migrations against Supabase Postgres:
export DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
cd backend && alembic upgrade head

# 4. Create storage bucket:
#    - Name: flowpilot-uploads
#    - Set to Public (for file access)
#    - File size limit: 10MB
#    - Allowed MIME types: application/pdf, image/png, image/jpeg
```

#### 2. Vercel Setup (Frontend)
```bash
# Install Vercel CLI
npm i -g vercel

# Link project
cd frontend && vercel link

# Set environment variables in Vercel Dashboard:
# NEXT_PUBLIC_API_URL = https://your-backend.railway.app
# NEXT_PUBLIC_SUPABASE_URL = https://your-project.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY = your-anon-key

# Deploy
vercel --prod
```

#### 3. Railway Setup (Backend)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create project
railway new flowpilot-backend

# Set environment variables:
railway variables set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
railway variables set DATABASE_URL=postgresql://...
railway variables set SUPABASE_URL=https://...
railway variables set SUPABASE_KEY=your-anon-key
railway variables set SUPABASE_SERVICE_KEY=your-service-key
railway variables set OPENAI_API_KEY=sk-...
railway variables set ALLOWED_ORIGINS='["https://your-vercel-app.vercel.app"]'
railway variables set DEBUG=false

# Deploy
cd backend && railway up
```

#### 4. GitHub Secrets Setup
```
PROD_DATABASE_URL      — Supabase PostgreSQL connection string
PROD_SECRET_KEY        — Generated 256-bit hex string
PROD_SUPABASE_URL      — Supabase project URL
PROD_SUPABASE_KEY      — Supabase anon key
PROD_SUPABASE_SERVICE_KEY — Supabase service role key
PROD_OPENAI_API_KEY    — OpenAI API key
RAILWAY_TOKEN          — Railway deployment token
VERCEL_TOKEN           — Vercel deployment token
VERCEL_ORG_ID          — Vercel organization ID
VERCEL_PROJECT_ID      — Vercel project ID
```

## API Contracts
Not applicable — deployment configuration.

## Request Examples
```bash
# Verify deployment
curl https://your-backend.railway.app/health
# Expected: {"status":"ok","version":"1.0.0","db":"connected"}

# Verify frontend
curl -I https://your-app.vercel.app
# Expected: 200 (or 307 redirect to /dashboard)
```

## Response Examples
```json
{"status": "ok", "version": "1.0.0", "db": "connected"}
```

## Database Tables
- Migrations run via `alembic upgrade head` in deploy workflow.
- Supabase PostgreSQL used for production.

## Business Logic
1. CI runs tests on every PR — blocks merge if tests fail.
2. Deploy workflow runs on push to `main` only.
3. Migrations run before backend deploy to ensure schema is ready.
4. Backend deploy is independent of frontend deploy (no `needs` dependency).
5. Frontend environment variables baked at build time — changes require redeploy.

## Validation Rules
- All GitHub Actions secrets must be set before first deploy.
- `alembic upgrade head` must succeed before Railway deploy.
- Vercel `--prod` flag required for production deploy (not preview).

## Error Handling
| Scenario | Action |
|----------|--------|
| Tests fail in CI | PR blocked — cannot merge |
| Migration fails | Deploy aborted — backend stays on old version |
| Vercel deploy fails | Automatic rollback to previous deployment |
| Railway deploy fails | Manual rollback: `railway rollback` |
| Health check fails after deploy | Manual investigation + `railway rollback` |

## Rollback Procedures

### Frontend Rollback (Vercel)
```bash
# List deployments
vercel ls

# Promote previous deployment to production
vercel promote <deployment-url>
```

### Backend Rollback (Railway)
```bash
# Roll back to previous deployment
railway rollback

# If schema migration needs reverting:
alembic downgrade -1
```

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
- First deploy: no previous migrations → `alembic upgrade head` runs all migrations.
- `NEXT_PUBLIC_API_URL` in Vercel: must point to Railway backend URL, not localhost.
- CORS `ALLOWED_ORIGINS` on Railway: must include Vercel production URL (`https://app.vercel.app`).
- Supabase connection pooling: Railway may use Supabase's connection pooler URL (`pooler.supabase.com:6543`).
- Cold start: Railway free tier may sleep — health check has 20s start period.

## Test Cases
1. `alembic upgrade head` against fresh Supabase DB succeeds.
2. Backend health check returns 200 after deploy.
3. Frontend loads and redirects to login page.
4. CI pipeline blocks PR when tests fail.
5. CORS allows requests from Vercel domain.

## Acceptance Criteria
- [ ] GitHub Actions CI pipeline configured
- [ ] Deploy pipeline configured for Vercel + Railway
- [ ] Migrations run automatically on deploy
- [ ] Production health check returns `"db":"connected"`
- [ ] Rollback procedures documented
- [ ] All GitHub Secrets documented

## Definition of Done
- CI pipeline runs successfully on a test PR
- Production deployment completes successfully
- Health check returns 200 with connected DB
- Frontend loads without errors
- README updated with deployment instructions
