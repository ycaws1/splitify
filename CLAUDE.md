# Splitify

Bill-splitting PWA where groups upload receipts, AI extracts line items, and users assign who owes what.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS 4, next-pwa |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0 (async), asyncpg |
| Auth | Supabase Auth (JWT) |
| Database | Supabase Postgres with pgBouncer connection pooling |
| Storage | Supabase Storage (receipt images) |
| OCR/AI | Anthropic Claude API (vision) |
| Push | Web Push API (VAPID / pywebpush) |
| Deployment | Vercel (frontend) + Render (backend) |

## Project Structure

```
splitify/
├── frontend/                # Next.js app
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # Reusable UI components
│   │   ├── lib/             # Utilities, Supabase client, API client
│   │   ├── hooks/           # Custom React hooks
│   │   └── types/           # TypeScript type definitions
│   ├── public/
│   │   ├── manifest.json    # PWA manifest
│   │   └── sw.js            # Service worker
│   └── next.config.ts
├── backend/                 # FastAPI app
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── api/             # Route handlers grouped by domain
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── core/            # Config, auth middleware, dependencies
│   │   └── workers/         # Background tasks (OCR, reminders)
│   ├── alembic/             # Database migrations
│   ├── alembic.ini
│   └── requirements.txt
├── docs/
│   └── plans/               # Design and implementation plans
└── CLAUDE.md
```

## Architecture

- **Option A: FastAPI owns all business logic.** Next.js is a thin frontend that calls FastAPI APIs.
- All writes go through FastAPI. Frontend subscribes to Supabase Realtime for live updates.
- Supabase Auth issues JWTs; FastAPI validates them via middleware on every request.
- Concurrency: optimistic locking with `version` columns on receipts. All assignment changes are transactional.

## Coding Conventions

### Frontend (TypeScript / Next.js)

- Use App Router with server components by default; `"use client"` only when needed (interactivity, hooks).
- Use `fetch` with the FastAPI base URL from env vars — no direct Supabase DB queries from frontend.
- Supabase client is used only for: auth (login/signup/session), realtime subscriptions, and storage uploads.
- Name components in PascalCase, files in kebab-case (e.g., `receipt-detail.tsx` exports `ReceiptDetail`).
- Colocate component-specific types in the same file; shared types go in `src/types/`.
- Use Tailwind for all styling. No CSS modules or styled-components.
- Forms use React Hook Form + Zod for validation.

### Backend (Python / FastAPI)

- Async everywhere: async def for all route handlers and service functions.
- SQLAlchemy 2.0 style with `async_session` and `select()` statements (not legacy Query API).
- Pydantic v2 for all request/response schemas. Use `model_config = ConfigDict(from_attributes=True)`.
- Group routes by domain in `app/api/`: `groups.py`, `receipts.py`, `assignments.py`, `payments.py`, `stats.py`, `push.py`.
- Business logic lives in `app/services/`, not in route handlers. Route handlers validate input, call services, return responses.
- Use FastAPI's `Depends()` for auth, DB sessions, and shared dependencies.
- Database sessions: use `async with` context managers. One session per request via dependency injection.
- Migrations via Alembic. Never modify the DB schema manually.

### Naming

- Python: snake_case for functions/variables, PascalCase for classes.
- TypeScript: camelCase for functions/variables, PascalCase for components/types.
- DB tables: snake_case, plural (e.g., `line_items`, `group_members`).
- API routes: kebab-case paths, e.g., `/api/groups/{id}/receipts`.

## Key Patterns

### Auth Flow
1. Frontend: Supabase Auth UI handles login/signup → gets JWT access token.
2. Frontend: sends `Authorization: Bearer <token>` on all FastAPI requests.
3. Backend: `get_current_user` dependency verifies JWT with Supabase JWKS, extracts user ID.

### Receipt Upload Flow
1. Frontend uploads image to Supabase Storage, gets public URL.
2. Frontend calls `POST /api/groups/{id}/receipts` with the image URL.
3. FastAPI triggers background task: sends image to Claude vision API, extracts structured data.
4. Extracted data saved to `receipts` + `line_items` tables with status `extracted`.
5. Supabase Realtime broadcasts the change; frontend updates live.

### Concurrency
- `receipts` table has a `version` column (integer, default 1).
- All updates include `WHERE version = :expected_version` and increment version.
- On conflict (0 rows updated), return 409 Conflict — frontend refetches and retries.
- Supabase Realtime keeps all connected clients in sync.

### Settlement Calculation
- Sum each user's assigned shares + proportional tax/service charge.
- Compare against actual payments.
- Simplify debts using greedy algorithm (minimize transactions).

## Environment Variables

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=          # FastAPI backend URL
NEXT_PUBLIC_VAPID_PUBLIC_KEY=
```

### Backend (`backend/.env`)
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
DATABASE_URL=                 # Supabase Postgres pooled connection string
ANTHROPIC_API_KEY=
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_EMAIL=
```

## Commands

### Frontend
```bash
cd frontend && npm install          # Install dependencies
cd frontend && npm run dev          # Dev server (localhost:3000)
cd frontend && npm run build        # Production build
cd frontend && npm run lint         # ESLint
```

### Backend
```bash
cd backend && pip install -r requirements.txt   # Install dependencies
cd backend && uvicorn app.main:app --reload     # Dev server (localhost:8000)
cd backend && alembic upgrade head              # Run migrations
cd backend && alembic revision --autogenerate -m "description"  # New migration
cd backend && pytest                            # Run tests
```

## Database

- All migrations through Alembic. Run `alembic upgrade head` after pulling changes.
- Use Supabase pooled connection string (port 6543) for the app, direct connection (port 5432) for migrations.
- Never use raw SQL in application code — always SQLAlchemy ORM.

## Testing

- Backend: pytest + pytest-asyncio + httpx (async test client for FastAPI).
- Frontend: Vitest + React Testing Library.
- Test files live next to the code they test: `services/receipt_service.py` → `services/test_receipt_service.py`.
