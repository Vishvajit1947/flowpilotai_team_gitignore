# 041 – Docker Setup

## Objective
Create production-ready Docker configurations for the frontend (Next.js) and backend (FastAPI) services, a `docker-compose.yml` for local development with hot reload, and a production `docker-compose.prod.yml` for deployment.

## Scope
- `frontend/Dockerfile` — multi-stage Next.js production build
- `backend/Dockerfile` — Python FastAPI production image
- `docker-compose.yml` — local development with hot reload
- `docker-compose.prod.yml` — production-grade compose
- `.dockerignore` files for both services
- Health checks for all services

## Out of Scope
- Kubernetes configuration
- Nginx reverse proxy configuration
- SSL/TLS termination
- CI/CD pipeline (045)

## Functional Requirements
1. `docker compose up` starts frontend (port 3000) and backend (port 8000).
2. Hot reload works in development mode for both services.
3. Production images are minimal and secure (non-root user).
4. Backend container includes Tesseract OCR and Poppler system dependencies.
5. Health checks on both containers.
6. Environment variables loaded from `.env` files.

## Technical Requirements
- Frontend: Node.js 20 Alpine base image
- Backend: Python 3.11 slim base image
- Multi-stage builds for production (minimize image size)
- Non-root user in production images
- `.env.local` for frontend, `.env` for backend (not in Docker image)

## Folder Structure
```
FlowPilot-AI/
├── frontend/
│   ├── Dockerfile
│   └── .dockerignore
├── backend/
│   ├── Dockerfile
│   └── .dockerignore
├── docker-compose.yml
└── docker-compose.prod.yml
```

## Files To Create

### `frontend/Dockerfile`
```dockerfile
# ── Stage 1: Dependencies ──────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# ── Stage 2: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build-time env (public vars only — no secrets)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ARG NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

RUN npm run build

# ── Stage 3: Production runner ─────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Copy Next.js standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD node -e "const http = require('http'); http.get('http://localhost:3000/', (r) => { process.exit(r.statusCode >= 200 && r.statusCode < 400 ? 0 : 1); }).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
```

### `frontend/.dockerignore`
```
node_modules
.next
.git
*.md
.env*.local
.env
coverage
.nyc_output
.DS_Store
Thumbs.db
```

### `backend/Dockerfile`
```dockerfile
# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Production runtime ────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy application code
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--no-access-log"]
```

### `backend/.dockerignore`
```
__pycache__
*.pyc
*.pyo
.env
.git
*.md
tests/
.pytest_cache
.mypy_cache
venv/
.venv/
*.egg-info
```

### `docker-compose.yml` (development)
```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: builder   # Use builder stage for dev (has build tools)
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - PYTHONPATH=/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: node:20-alpine
    working_dir: /app
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    env_file:
      - ./frontend/.env.local
    environment:
      - NODE_ENV=development
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### `docker-compose.prod.yml` (production)
```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
        NEXT_PUBLIC_SUPABASE_URL: ${NEXT_PUBLIC_SUPABASE_URL}
        NEXT_PUBLIC_SUPABASE_ANON_KEY: ${NEXT_PUBLIC_SUPABASE_ANON_KEY}
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "const http=require('http');http.get('http://localhost:3000/',r=>{process.exit(r.statusCode<400?0:1)}).on('error',()=>process.exit(1))"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

## Existing Files To Modify
- `frontend/next.config.ts` — add `output: 'standalone'` for Docker optimization:
```typescript
const nextConfig: NextConfig = {
  output: 'standalone',
  // ... existing config
};
```

## API Contracts
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Development: backend uses `--reload` flag, mounts source code as volume.
- Production: multi-stage build, non-root user, `output: 'standalone'` reduces image size.
- OCR dependencies (tesseract, poppler) installed in backend runtime image only.
- Frontend `node_modules` anonymous volume prevents host modules from overriding container modules.

## Validation Rules
Not applicable.

## Error Handling
- Health check failure: Docker restarts container after 3 failures.
- If backend is unhealthy, frontend container waits (depends_on with condition).

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
- Apple Silicon (ARM64): Python packages must be ARM-compatible — `python:3.11-slim` is multi-arch.
- Node `node_modules` in volumes: use anonymous volume to prevent host interference.
- `next.config.ts` with `output: 'standalone'`: must be set for the Dockerfile's `server.js` copy to work.
- `.env` files should never be in Docker image — loaded at runtime via `env_file`.

## Test Cases
1. `docker compose build` completes without errors.
2. `docker compose up` starts both services.
3. `curl http://localhost:8000/health` returns 200.
4. `curl http://localhost:3000/` returns 200.
5. Production build: `docker compose -f docker-compose.prod.yml build` succeeds.
6. Non-root user in production container: `docker exec <container> whoami` returns `nextjs`/`appuser`.
7. Tesseract available in backend: `docker exec <backend> tesseract --version`.

## Acceptance Criteria
- [ ] `docker compose up` starts both services with hot reload
- [ ] Production Dockerfiles use multi-stage builds
- [ ] Non-root users in production images
- [ ] Tesseract and Poppler in backend image
- [ ] Health checks configured on both services
- [ ] `.env` files not baked into images

## Definition of Done
- All test cases pass
- Both images build without errors
- `docker compose -f docker-compose.prod.yml up` works
- Image sizes documented (backend target < 800MB, frontend < 200MB)
