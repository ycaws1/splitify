# Splitify Design Document

**Date:** 2026-02-14
**Status:** Approved

## Overview

Splitify is a PWA for splitting bills among groups. Users upload receipts, AI extracts line items, users assign who owes what, and the app calculates net balances with automated reminders.

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS 4 | SSR, PWA support, modern React |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0 async | Async-first, good AI/ML ecosystem |
| Auth | Supabase Auth | JWT-based, social login ready, no custom auth code |
| Database | Supabase Postgres (pgBouncer) | Managed, pooled connections, integrated with auth |
| Storage | Supabase Storage | Unified with auth/DB, S3-compatible |
| OCR/AI | Claude API (vision) | Excellent at reading messy receipts, structured output |
| Push | Web Push (VAPID / pywebpush) | Works on both Android and iOS PWA |
| Hosting | Vercel (frontend) + Render (backend) | Free tiers, easy deploy |

## Architecture

**Option A: FastAPI as sole backend.** Next.js is a thin frontend client.

```
┌──────────────┐     HTTP/REST      ┌──────────────┐
│   Next.js    │ ──────────────────► │   FastAPI    │
│  (Vercel)    │ ◄────────────────── │  (Render)    │
│              │                     │              │
│  Supabase    │                     │  Claude API  │
│  Auth UI     │                     │  (vision)    │
│  Realtime WS │                     │              │
│  Storage SDK │                     │  Supabase    │
└──────────────┘                     │  Postgres    │
       │                             └──────────────┘
       │ Realtime subscriptions              │
       └─────────────────────────────────────┘
              Supabase Platform
```

- All writes go through FastAPI.
- Frontend uses Supabase client only for: auth, realtime subscriptions, storage uploads.
- FastAPI validates Supabase JWTs on every request.

## Data Model

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | From Supabase Auth |
| email | VARCHAR | Unique |
| display_name | VARCHAR | |
| avatar_url | VARCHAR | Nullable |
| push_subscription | JSONB | Nullable, web push endpoint |
| created_at | TIMESTAMPTZ | |

### groups
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | VARCHAR | |
| invite_code | VARCHAR | Unique, short alphanumeric |
| created_by | UUID | FK → users |
| created_at | TIMESTAMPTZ | |

### group_members
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| group_id | UUID | FK → groups |
| user_id | UUID | FK → users |
| role | ENUM | owner, member |
| joined_at | TIMESTAMPTZ | |

Unique constraint on (group_id, user_id).

### receipts
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| group_id | UUID | FK → groups |
| uploaded_by | UUID | FK → users |
| image_url | VARCHAR | Supabase Storage path |
| merchant_name | VARCHAR | Nullable, extracted |
| receipt_date | DATE | Nullable, extracted |
| currency | VARCHAR(3) | Default configurable |
| subtotal | DECIMAL(12,2) | Nullable |
| tax | DECIMAL(12,2) | Nullable |
| service_charge | DECIMAL(12,2) | Nullable |
| total | DECIMAL(12,2) | Nullable |
| status | ENUM | processing, extracted, confirmed |
| raw_llm_response | JSONB | For debugging |
| version | INTEGER | Default 1, optimistic locking |
| created_at | TIMESTAMPTZ | |

### line_items
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| receipt_id | UUID | FK → receipts |
| description | VARCHAR | |
| quantity | DECIMAL(10,3) | |
| unit_price | DECIMAL(12,2) | |
| amount | DECIMAL(12,2) | |
| sort_order | INTEGER | |

### line_item_assignments
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| line_item_id | UUID | FK → line_items |
| user_id | UUID | FK → users |
| share_amount | DECIMAL(12,2) | Calculated portion |

Unique constraint on (line_item_id, user_id).

### payments
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| receipt_id | UUID | FK → receipts |
| paid_by | UUID | FK → users |
| amount | DECIMAL(12,2) | |
| created_at | TIMESTAMPTZ | |

### settlements
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| group_id | UUID | FK → groups |
| from_user | UUID | FK → users (owes) |
| to_user | UUID | FK → users (owed) |
| amount | DECIMAL(12,2) | |
| is_settled | BOOLEAN | Default false |
| settled_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | |

## API Design

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/callback | Sync Supabase user to local users table |

### Groups
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/groups | Create group |
| GET | /api/groups | List my groups |
| GET | /api/groups/{id} | Group detail + members |
| POST | /api/groups/{id}/invite | Generate invite (link/QR/email) |
| POST | /api/groups/join/{code} | Join via invite code |

### Receipts
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/groups/{id}/receipts | Upload receipt (triggers OCR) |
| GET | /api/groups/{id}/receipts | List receipts in group |
| GET | /api/receipts/{id} | Receipt detail + line items |
| PUT | /api/receipts/{id} | Edit extracted data (version check) |
| POST | /api/receipts/{id}/confirm | Confirm extraction |

### Assignments
| Method | Path | Description |
|--------|------|-------------|
| PUT | /api/receipts/{id}/assignments | Bulk assign users to line items (version check) |
| GET | /api/receipts/{id}/assignments | Get current assignments |

### Payments & Settlements
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/receipts/{id}/payments | Record who paid |
| GET | /api/groups/{id}/balances | Net balances (who owes who) |
| POST | /api/groups/{id}/settle | Mark debt as settled |

### Statistics
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/groups/{id}/stats | Stats by period (?period=1d\|1mo\|1yr) |

### Push
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/push/subscribe | Register push subscription |
| DELETE | /api/push/subscribe | Unregister |

## Frontend Pages

| Route | Purpose |
|-------|---------|
| / | Landing / login (Supabase Auth UI) |
| /dashboard | Group list, quick balances |
| /groups/new | Create group |
| /groups/[id] | Group home: members, recent receipts, balances |
| /groups/[id]/receipts | Receipt list |
| /groups/[id]/receipts/new | Upload receipt (camera/gallery) |
| /receipts/[id] | Receipt detail: line items, assign, mark paid |
| /groups/[id]/stats | Statistics charts by period |
| /join/[code] | Invite landing page |
| /settings | Profile, push preferences |

## Concurrency Strategy

1. **Optimistic locking:** `version` column on `receipts`. Updates use `WHERE version = :expected` and increment. 409 Conflict on mismatch.
2. **Supabase Realtime:** Frontend subscribes to table changes per group. All connected clients see updates live.
3. **Transactions:** Assignment changes + settlement recalculation happen in a single DB transaction.
4. **Idempotency:** Receipt upload uses idempotency keys to prevent duplicate OCR processing.

## Receipt OCR Flow

1. User uploads image → frontend stores in Supabase Storage.
2. Frontend calls `POST /api/groups/{id}/receipts` with image URL.
3. FastAPI creates receipt record (status: `processing`), triggers background task.
4. Background task sends image to Claude vision API with structured extraction prompt.
5. Claude returns JSON → FastAPI validates, saves to `receipts` + `line_items`.
6. Status changes to `extracted`. Supabase Realtime notifies frontend.
7. User reviews, edits if needed, confirms.

## Settlement Calculation

1. For each receipt in the group:
   - Sum each user's `share_amount` from `line_item_assignments`.
   - Add proportional share of tax + service charge (based on subtotal ratio).
2. Sum across all receipts to get each user's total responsibility.
3. Subtract what each user actually paid (from `payments`).
4. Positive balance = user owes money. Negative = user is owed.
5. Simplify debts using greedy algorithm to minimize number of transactions.

## Web Push Reminders

- Frontend registers push subscription via VAPID, sends to FastAPI.
- Stored in `users.push_subscription` (JSONB).
- Daily cron (FastAPI background scheduler or Render cron job):
  - Query `settlements WHERE is_settled = false AND created_at < now() - interval '14 days'`.
  - Send web push to `from_user`: "You still owe {to_user} ${amount} from {group}."

## PWA Requirements

- `manifest.json`: app name, icons (192x192, 512x512), theme color, display: standalone.
- Service worker: cache app shell for offline loading. Data requires network.
- iOS: add `apple-touch-icon`, `apple-mobile-web-app-capable` meta tags.
- "Add to Home Screen" prompt handling for both platforms.

## Invitation Methods

1. **Invite link:** Generated URL with invite code, shareable via any messaging app.
2. **QR code:** Generated client-side from the invite link, scannable.
3. **Email invite:** FastAPI sends email with invite link (via Supabase email or a transactional email service).
