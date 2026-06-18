# B1 — Dashboard Command Center (Upgrade-in-Place) — Design Spec

Date: 2026-06-18
Status: Approved (pending written-spec review)
Source: `presentation/blueprint/EAM_FEATURE_BLUEPRINT.md` → Part B1

## 1. Goal

Upgrade the existing dashboards into a role-aware "command center" **without rebuilding them**. Add an AI daily briefing, a next-best-action feed, loading skeletons, drill-through, and small quality-of-life touches — via **shared reusable components mounted in all four dashboards**.

Explicitly out of scope this round: configurable widget engine, Executive KPI Wallboard, per-widget export. (Deferred — revisit later.)

## 2. Current State

Four hardcoded dashboards exist:
- `app/frontend/src/modules/shared/Dashboard.tsx` — generic; client-side fetch of 100 machines + 100 WOs, computes 6 stat cards + Recent WOs + Upcoming Maintenance. Uses an `animate-spin` spinner.
- `app/frontend/src/modules/cheftech/CheftechDashboard.tsx` (+ `dashboard/components/DashboardStatsCards.tsx`)
- `app/frontend/src/modules/chetop/ChetopDashboard.tsx`
- `app/frontend/src/modules/technicien/TechnicianDashboard.tsx`

Design system in use: `bg-slate-800/900` cards, white headings, `text-blue-300/400` muted text, emerald/orange/red status, `Card`/`Badge` UI primitives, `cn` util. **All new components follow this exact theme** — no new palette.

## 3. Approach

Upgrade-in-place. Build **shared components** under `app/frontend/src/modules/shared/dashboard/` and mount them in each of the four dashboards. The components are common (same look/behavior); the **data passed in is role-scoped**.

## 4. Components (frontend)

All live in `app/frontend/src/modules/shared/dashboard/`.

### `BriefingBar`
- Props: `role`, `siteId?`.
- Fetches `GET /dashboard/briefing`. Shows skeleton while loading; renders cached text on success.
- Visual: slate panel (`bg-slate-800`, `border-slate-700`), `Sparkles` icon in blue-400, white lead word "Daily briefing.", blue-100 body.
- Never blocks the page: on error, renders nothing or a quiet fallback line (the backend already guarantees a template fallback).

### `NextBestActions`
- Props: `role`, plus the already-fetched `machines`, `workOrders`, `alerts`.
- **Client-side compute** (no new endpoint). Ranks candidate items, shows top 5, each row links to its record.
- Visual: list rows, left border colored by severity (red/amber/blue), severity badge, label, `ChevronRight`.

### `DashboardSkeleton`
- Card and list skeleton blocks (`bg-slate-800 animate-pulse`). Replaces the `animate-spin` spinner in `shared/Dashboard.tsx` and is reused by the others.

### `DeltaBadge`
- Props: `current`, `previous` (or `change`). Renders `▲ N` (emerald) / `▼ N` (red) / `–` (muted) "vs yesterday". Pure, no fetch.

### `DashboardFilters`
- Date-range + site selector. Persists to `localStorage` per user (`eam.dashboard.filters.<userId>`). Existing dashboard fetches read the active filter. Default: last 7 days, all sites.

### Drill-through links
- Wrap KPI cards / list rows in links to the filtered destination list. Examples:
  - Urgent WOs → `/work-orders?priority=URGENTE&status=!TERMINE`
  - Fleet health → machines list sorted by health
  - Overdue PMs → planning filtered to overdue
- Implemented with the app's existing router `Link`; cards gain `cursor-pointer` + a `ChevronRight` affordance.

## 5. Backend — Briefing endpoint

`GET /dashboard/briefing?role=&site=` → `{ text, generated_at, facts: [...], source: "cache" | "llm" | "template" }`

Flow:
1. **Build role-scoped snapshot** reusing the existing chat-bridge pattern (`get_ml_snapshot()` / `chat_context.py`): counts (urgent WOs, pending, completed-this-week), top degraded machines (ML health), overdue PMs, active anomaly + parts-shortage alerts. For TECHNICIEN, scope to that user's assignments.
2. **Compute `snapshot_hash`** over the material facts only (so cosmetic changes don't bust the cache).
3. **Cache lookup** by key `(scope, scope_id, site, date, snapshot_hash)`:
   - `scope = "role"`, `scope_id = role` for ADMIN / CHEFTECH / CHETOP.
   - `scope = "user"`, `scope_id = user_id` for TECHNICIEN.
4. **Hit** → return cached text (`source: cache`). **Miss** → call the LLM to phrase the facts naturally, store, return (`source: llm`).
5. **LLM unavailable** → assemble the rule-based template from the same facts and return it (`source: template`). The endpoint **never raises** — mirrors the platform's proven `score_source=fallback` safety property.

Storage: a `dashboard_briefing_cache` table (or reuse an existing cache mechanism) keyed as above, with `text`, `generated_at`. Daily rows; old rows pruned by date.

Cost: ~1 LLM call per scope per day, and only when facts materially change. Negligible.

## 6. Next-best-action scoring (deterministic, client-side)

`score = urgency_weight × impact`
- `urgency_weight`: critical alert > urgent WO > overdue PM > parts shortage > upcoming PM.
- `impact`: machine criticality × predicted downtime signal (from ML health / P5 priority where available; fallback to a constant if absent).
- Candidate set filtered by role: TECHNICIEN sees only their assigned items; ADMIN/CHEFTECH/CHETOP see site-wide.
- Sort desc, take top 5. Each item carries a deep link to its record.

## 7. Error Handling & Edge Cases

- Briefing: LLM fail → template; empty data → "All clear today" empty state.
- Filters: missing/invalid → default (last 7 days, all sites).
- Every async section shows a skeleton; fetch failures raise a toast with retry.
- Empty states everywhere (helpful, with a next-step link) instead of blank panels.

## 8. Testing

Backend:
- snapshot builder returns correct counts per role (incl. TECHNICIEN assignment scoping).
- cache hit returns stored text without an LLM call.
- `snapshot_hash` change triggers regeneration.
- LLM-down path returns a non-empty template and `source: template`; endpoint never raises.

Frontend:
- `DashboardSkeleton` renders during load (no spinner).
- `BriefingBar` renders returned text; renders fallback on error without crashing.
- `NextBestActions` ordering matches the scoring rule; rows link to correct hrefs.
- `DeltaBadge` shows ▲/▼/– correctly.
- `DashboardFilters` persists and restores per user.

## 9. Rollout

1. Build shared components + backend endpoint behind the existing dashboards.
2. Wire into `shared/Dashboard.tsx` first (validate), then the three role dashboards.
3. Ship. Wallboard and export follow in a later increment.
