# FlowPilot AI — Engineering Documentation Index

## Project Overview
FlowPilot AI is an AI-powered inbox orchestration and workflow automation platform.
Users submit text or documents, which are classified by intent, scored for confidence,
routed to a specialized AI agent (Sales / Support / Finance / Executive), and returned
as structured, actionable results — all within seconds.

**Stack:** Next.js 15 · TypeScript · Tailwind CSS · Shadcn UI · Framer Motion · FastAPI · Python 3.11 · Supabase PostgreSQL · SQLAlchemy 2.0 · LangGraph · LangChain · OpenAI GPT-4o · Tesseract OCR

---

## Document Map

### Foundation (001–004)
| Doc | Title | Description |
|-----|-------|-------------|
| [001](001_Project_Setup.md) | Project Setup | Monorepo init, tooling, dependencies, folder structure |
| [002](002_Frontend_Scaffold.md) | Frontend Scaffold | Next.js root layout, CSS variables, Shadcn init, global providers |
| [003](003_Backend_Scaffold.md) | Backend Scaffold | FastAPI app, config, logging, exception handlers, health check |
| [004](004_Database_Schema.md) | Database Schema | SQLAlchemy ORM models, Alembic migrations, all tables and indexes |

### Authentication (005–009)
| Doc | Title | Description |
|-----|-------|-------------|
| [005](005_Custom_JWT_Authentication.md) | Custom JWT Authentication | bcrypt hashing, JWT creation/validation, FastAPI auth dependencies |
| [006](006_Register_API.md) | Register API | `POST /auth/register` endpoint with full validation |
| [007](007_Login_API.md) | Login API | `POST /auth/login` + `GET /auth/me` endpoints |
| [008](008_Auth_Context.md) | Auth Context | Zustand auth store, Axios interceptors, login/register forms |
| [009](009_Protected_Routes.md) | Protected Routes | ProtectedRoute component, cookie sync, FOUC prevention |

### Dashboard Shell (010–012)
| Doc | Title | Description |
|-----|-------|-------------|
| [010](010_Dashboard_Layout.md) | Dashboard Layout | Two-column layout, sidebar/content shell, page transitions |
| [011](011_Sidebar_Component.md) | Sidebar Component | Navigation links, active states, collapse mode, user profile |
| [012](012_Header_Component.md) | Header Component | Page title, hamburger, user dropdown, theme toggle placeholder |

### Core Features (013–016)
| Doc | Title | Description |
|-----|-------|-------------|
| [013](013_Metric_Cards.md) | Metric Cards | KPI cards with count-up animation and skeleton loading |
| [014](014_AI_Inbox_UI.md) | AI Inbox UI | Two-panel inbox with form, polling, result panel, history |
| [015](015_File_Upload_Component.md) | File Upload Component | Drag-and-drop upload to Supabase Storage with progress |
| [016](016_Inbox_Submit_API.md) | Inbox Submit API | `POST /inbox/submit`, `GET /inbox/{id}`, `GET /inbox/` |

### AI Pipeline (017–025)
| Doc | Title | Description |
|-----|-------|-------------|
| [017](017_Intent_Detection.md) | Intent Detection | GPT-4o intent classification with caching |
| [018](018_Confidence_Scoring.md) | Confidence Scoring | Keyword pre-pass + GPT-4o confidence scoring [0.0–1.0] |
| [019](019_Agent_Router.md) | Agent Router | Intent→agent mapping, escalation rules, RoutingDecision |
| [020](020_Agent_State.md) | Agent State | LangGraph TypedDict state schema, audit trail |
| [021](021_Sales_Agent.md) | Sales Agent | Lead extraction, lead scoring, action items via GPT-4o |
| [022](022_Support_Agent.md) | Support Agent | Issue classification, severity, SLA, response draft |
| [023](023_Finance_Agent.md) | Finance Agent | Invoice extraction, anomaly detection, payment recommendation |
| [024](024_Executive_Agent.md) | Executive Agent | Strategic briefs, escalation handling, decision framework |
| [025](025_LangGraph_Workflow.md) | LangGraph Workflow | Full orchestration graph: OCR→intent→confidence→route→agent→persist |

### Document Intelligence (026–029)
| Doc | Title | Description |
|-----|-------|-------------|
| [026](026_Workflow_Viewer.md) | Workflow Viewer | Timeline visualization of LangGraph execution steps |
| [027](027_OCR_Service.md) | OCR Service | Tesseract OCR for PDF/image files from Supabase URLs |
| [028](028_Invoice_Extraction.md) | Invoice Extraction | `POST /documents/extract-invoice` standalone endpoint |
| [029](029_Document_Intelligence_Page.md) | Document Intelligence Page | Upload + extract UI with structured result card |

### Analytics (030–032)
| Doc | Title | Description |
|-----|-------|-------------|
| [030](030_Analytics_API.md) | Analytics API | Summary, by-agent, by-day aggregation endpoints |
| [031](031_Analytics_UI.md) | Analytics UI | Full analytics page with Recharts donut + bar charts |
| [032](032_Dashboard_Charts.md) | Dashboard Charts | Sparkline and agent utilization bars on main dashboard |

### History & Admin (033–035)
| Doc | Title | Description |
|-----|-------|-------------|
| [033](033_Workflow_History.md) | Workflow History | Paginated table with status filter and detail drawer |
| [034](034_Admin_DB_Reset.md) | Admin DB Reset | Admin-only reset/seed/list-users API endpoints |
| [035](035_Admin_Banner.md) | Admin Banner | Admin control panel UI with confirmation dialogs |

### UX Systems (036–040)
| Doc | Title | Description |
|-----|-------|-------------|
| [036](036_Toast_System.md) | Toast System | Centralized sonner toast helper with message constants |
| [037](037_Loading_States.md) | Loading States | Skeleton, Spinner, PageLoader, TableSkeleton, CardSkeleton |
| [038](038_Error_Boundaries.md) | Error Boundaries | React error boundaries, global-error.tsx, SectionError |
| [039](039_Page_Animations.md) | Page Animations | Framer Motion variants, FadeIn/SlideIn/ScaleIn/Stagger |
| [040](040_Dark_Mode.md) | Dark Mode | Theme toggle, ThemeProvider, anti-flash script |

### Infrastructure (041–046)
| Doc | Title | Description |
|-----|-------|-------------|
| [041](041_Docker_Setup.md) | Docker Setup | Multi-stage Dockerfiles, docker-compose dev + prod |
| [042](042_Environment_Config.md) | Environment Config | Complete env var reference, startup validation |
| [043](043_Integration_Tests.md) | Integration Tests | pytest test suite for all API endpoints |
| [044](044_Edge_Case_Testing.md) | Edge Case Testing | Security, boundary, concurrency, and failure tests |
| [045](045_Deployment.md) | Deployment | Vercel + Railway deploy, GitHub Actions CI/CD |
| [046](046_README.md) | README | Root README.md with full setup and usage instructions |

---

## Dependency Graph

```
001 (Setup)
  └─► 002 (Frontend Scaffold)
        └─► 008 (Auth Context)
              └─► 009 (Protected Routes)
                    └─► 010 (Dashboard Layout)
                          ├─► 011 (Sidebar)
                          ├─► 012 (Header)
                          ├─► 013 (Metric Cards) ◄── 030 (Analytics API)
                          ├─► 014 (AI Inbox UI)  ◄── 016 (Inbox API)
                          │     └─► 015 (File Upload)
                          ├─► 031 (Analytics UI) ◄── 030
                          ├─► 032 (Dashboard Charts)
                          ├─► 033 (Workflow History)
                          └─► 035 (Admin Banner)  ◄── 034 (Admin API)

  └─► 003 (Backend Scaffold)
        └─► 004 (DB Schema)
              └─► 005 (JWT Auth)
                    ├─► 006 (Register API)
                    ├─► 007 (Login API)
                    ├─► 016 (Inbox API)
                    │     └─► 025 (LangGraph Workflow)
                    │           ├─► 017 (Intent Detection)
                    │           ├─► 018 (Confidence Scoring)
                    │           ├─► 019 (Agent Router)
                    │           ├─► 020 (Agent State)
                    │           ├─► 021 (Sales Agent)
                    │           ├─► 022 (Support Agent)
                    │           ├─► 023 (Finance Agent)
                    │           ├─► 024 (Executive Agent)
                    │           └─► 027 (OCR Service)
                    ├─► 028 (Invoice Extraction)
                    ├─► 030 (Analytics API)
                    └─► 034 (Admin API)
```

---

## Stats
- **Total documents:** 46
- **Total size:** ~594 KB
- **Average lines per document:** ~392
- **Coverage:** All features, all API contracts, all DB schemas, all UI components

---

## How to Use These Documents

Each document is **fully self-contained**. To implement any task:

1. Open the relevant `.md` file
2. Read the **Objective**, **Scope**, and **Technical Requirements**
3. Follow the **Files To Create** and **Files To Modify** sections exactly
4. Validate against **Acceptance Criteria** and **Test Cases**
5. Mark **Definition of Done** checklist

Documents do NOT need to be read in order — each contains all necessary context.
The only exception is when a document says it **depends on** another (e.g., auth endpoints
depend on the JWT utilities from 005).
