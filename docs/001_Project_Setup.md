# 001 – Project Setup

## Objective
Initialize the complete FlowPilot AI monorepo with correct directory structure, tooling configuration, dependency manifests, and environment scaffolding so that every subsequent task has a consistent, reproducible foundation to build upon.

## Scope
- Root monorepo folder layout
- Frontend (Next.js 15) project initialization
- Backend (FastAPI / Python) project initialization
- Shared environment variable templates
- Git configuration (.gitignore, .gitattributes)
- Code-quality tooling (ESLint, Prettier, Black, isort, pre-commit hooks)
- Package manager lock files committed to version control

## Out of Scope
- Any application logic
- Database migrations (covered in 004_Database_Schema.md)
- Docker configuration (covered in 041_Docker_Setup.md)
- CI/CD pipelines (covered in 045_Deployment.md)

## Functional Requirements
1. Running `npm install` inside `frontend/` must succeed without errors.
2. Running `pip install -r requirements.txt` inside `backend/` must succeed without errors.
3. `npm run dev` inside `frontend/` must start the Next.js dev server on port 3000.
4. `uvicorn main:app --reload` inside `backend/` must start the FastAPI dev server on port 8000.
5. All lint and format commands must pass on a clean checkout.

## Technical Requirements
- Node.js >= 20.x
- Python >= 3.11
- npm >= 10.x
- pip + virtualenv or Poetry
- Next.js 15.x (App Router)
- FastAPI 0.111.x
- Pydantic v2
- ESLint flat-config (eslint.config.mjs)
- Prettier 3.x
- Black 24.x
- isort 5.x
- pre-commit 3.x

## Folder Structure
```
FlowPilot-AI/
├── frontend/                  # Next.js 15 application
│   ├── app/                   # App Router pages
│   ├── components/            # Shared React components
│   ├── lib/                   # Utility functions
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # Zustand state stores
│   ├── types/                 # TypeScript type definitions
│   ├── public/                # Static assets
│   ├── styles/                # Global CSS
│   ├── .env.local.example     # Frontend env template
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   ├── eslint.config.mjs
│   └── .prettierrc
├── backend/
│   ├── app/
│   │   ├── api/               # Route handlers
│   │   ├── core/              # Config, security, constants
│   │   ├── db/                # Database models and sessions
│   │   ├── services/          # Business logic services
│   │   ├── agents/            # LangGraph / LangChain agents
│   │   ├── schemas/           # Pydantic request/response models
│   │   └── utils/             # Helper utilities
│   ├── tests/
│   ├── .env.example           # Backend env template
│   ├── main.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml
│   └── .pre-commit-config.yaml
├── docs/                      # This documentation folder
├── .gitignore
├── .gitattributes
└── README.md
```

## Files To Create

### Root
- `.gitignore` — covers Node, Python, OS artifacts, `.env*` files (never commit secrets)
- `.gitattributes` — enforce LF line endings for all text files

### `frontend/package.json`
```json
{
  "name": "flowpilot-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --turbo",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "format": "prettier --write .",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.4.0",
    "@types/node": "^20.12.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "framer-motion": "^11.2.0",
    "recharts": "^2.12.0",
    "zustand": "^4.5.0",
    "axios": "^1.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "lucide-react": "^0.400.0",
    "sonner": "^1.5.0",
    "class-variance-authority": "^0.7.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-tooltip": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-separator": "^1.1.0",
    "@radix-ui/react-avatar": "^1.1.0",
    "@radix-ui/react-badge": "^1.0.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-switch": "^1.1.0"
  },
  "devDependencies": {
    "eslint": "^9.0.0",
    "prettier": "^3.3.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "eslint-config-next": "15.1.0",
    "eslint-plugin-react-hooks": "^4.6.0"
  }
}
```

### `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### `frontend/next.config.ts`
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  experimental: {
    typedRoutes: true,
  },
  images: {
    remotePatterns: [],
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

### `frontend/tailwind.config.ts`
```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

### `backend/requirements.txt`
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
supabase==2.4.2
psycopg2-binary==2.9.9
sqlalchemy==2.0.30
alembic==1.13.1
python-jose[cryptography]==3.3.0
bcrypt==4.1.3
python-multipart==0.0.9
httpx==0.27.0
langchain==0.2.1
langchain-openai==0.1.8
langchain-community==0.2.1
langgraph==0.1.14
openai==1.30.1
pytesseract==0.3.10
Pillow==10.3.0
pdf2image==1.17.0
python-dotenv==1.0.1
structlog==24.2.0
```

### `backend/requirements-dev.txt`
```
pytest==8.2.1
pytest-asyncio==0.23.7
pytest-httpx==0.30.0
httpx==0.27.0
black==24.4.2
isort==5.13.2
mypy==1.10.0
pre-commit==3.7.1
```

### `backend/pyproject.toml`
```toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### `backend/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="FlowPilot AI",
    version="1.0.0",
    description="AI-powered inbox orchestration platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

### `frontend/.env.local.example`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=FlowPilot AI
```

### `backend/.env.example`
```
DEBUG=true
SECRET_KEY=change-me-in-production-use-256-bit-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql://postgres:password@localhost:5432/flowpilot
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## Existing Files To Modify
None — this is the initial setup task.

## API Contracts
None — this task is infrastructure only.

## Database Tables
None — see 004_Database_Schema.md.

## Business Logic
None — setup only.

## Validation Rules
- `.env*` files must never be committed (enforced in `.gitignore`)
- All Python files must pass `black --check` and `isort --check`
- All TypeScript files must pass `tsc --noEmit`
- All TypeScript/TSX files must pass `eslint`

## Error Handling
- If `npm install` fails, check Node version: must be >= 20
- If `pip install` fails, ensure Python 3.11+ and virtualenv is activated
- If `next dev` fails on port 3000, check for port conflicts

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
- Windows users: ensure `.gitattributes` enforces LF, not CRLF
- Apple Silicon: confirm all Python native extensions compile (psycopg2-binary, Pillow)
- If Tesseract OCR system dependency is missing, `pytesseract` will raise at runtime — document this in README

## Test Cases
1. `npm run type-check` exits 0 in a clean checkout
2. `npm run lint` exits 0 in a clean checkout
3. `python -m pytest tests/` exits 0 with no tests (empty suite is OK)
4. `uvicorn main:app --port 8000` starts and `/health` returns `{"status":"ok"}`
5. `next build` completes without TypeScript errors

## Acceptance Criteria
- [ ] `frontend/` and `backend/` directories exist with correct structure
- [ ] All dependencies install cleanly
- [ ] Dev servers start without errors
- [ ] Lint and format tooling configured and passing
- [ ] `.env` files never committed; example files exist
- [ ] `/health` endpoint returns 200

## Definition of Done
- All acceptance criteria checked off
- No TypeScript errors (`tsc --noEmit`)
- No Python lint violations (`black --check`, `isort --check`)
- Folder structure matches specification exactly
- PR reviewed and merged to `main`
