# Today's Work + Day-Transition Archiving — Design

Date: 2026-06-14
Branch: clean_Phase_1
Status: Approved

## Problem

The admin/cheftech dashboard "Interventions" and "Ordres de travail" tabs show 0
items. Expected: a "Today's Work" view showing interventions and work orders
scheduled for the current day, with previous days auto-archived but still
retrievable.

## Root cause

1. **Aggressive archive sweep.** `services/archive.py` Pass 2 archives any row
   where `due_col < now`, regardless of status. For interventions the due column
   is `date_intervention`, for work orders `date_echeance`. A still-pending
   `EN_ATTENTE` intervention or unassigned WO whose date is in the past gets
   auto-archived within the hour (Celery beat `tasks.archive_past_due`, every
   3600s) and disappears from the dashboard. The `< now` comparison also archives
   items earlier *today*, not just previous days.
2. **User-scoped intervention query.** `modules/cheftech/routes/interventions.py`
   only returns interventions where
   `technician_id == me OR ordre_travail.created_by == me OR statut == PENDING_APPROVAL`.
   An ADMIN viewing `/admin/dashboard` (which renders `<CheftechDashboard role="ADMIN" />`)
   sees nothing unless an item is `PENDING_APPROVAL`.
3. **No "today" filter exists.** The tabs show *all* pending/unassigned items
   regardless of date — there is no notion of "today's work".

## Existing infrastructure (reused, not rebuilt)

- `services/archive.py` — `ArchiveService.archive_past_due / reactivate / purge_old / list_archived`.
- `core/celery_app.py` — hourly archive beat + weekly purge.
- `modules/archive/router.py` — `/api/v1/archive/{module}` list, reactivate, sweep, purge, counts (role-scoped).
- `archived_at` + `archive_reason` columns on both tables; both list endpoints already exclude archived rows.
- Frontend `modules/shared/ArchivePage.tsx` + `Archives.tsx` — archive/history UI.

## Decisions (from brainstorming)

- Archive rule: archive when the due date's **day** has passed; keep otherwise.
  No "skip pending" exception — pure date based.
- Today view: a "Today" filter on the existing tabs (default ON).
- Archive UI: already exists — not rebuilt.
- Scope: ADMIN / CHEFTECH / CHETOP see all interventions & WOs; TECHNICIEN sees own only.
- Timezone: UTC day boundary, consistent with Celery `timezone=UTC` and the
  timezone-aware UTC database.

## Changes

### 1. Archive boundary (backend)

`app/backend/services/archive.py`, `archive_past_due` Pass 2.

Replace `due_col < now` with `due_col < start_of_today`, where
`start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)` in UTC.

Result: items due today or in the future stay active; only items whose due-date
day is fully over are archived. Pass 1 (terminal-status archive) unchanged. NULL
due dates are never archived by date.

### 2. Role-based scoping (backend)

`app/backend/modules/cheftech/routes/interventions.py`.

Branch the count and main query on `current_user.role`:
- `ADMIN` / `CHEFTECH` / `CHETOP`: no user filter (all active interventions).
- `TECHNICIEN`: `Ordres_intervention.technician_id == current_user.id`.

Work-order endpoint already returns all active rows — unchanged.

### 3. "Today" filter (frontend)

`InterventionsTab.tsx`, `WorkOrdersTab.tsx`, and a small `isToday` helper in
`dashboard/utils`.

Add an "Aujourd'hui" toggle (default ON). When ON, the existing
pending/unassigned list is additionally filtered to items whose scheduled date is
today (`date_intervention` for interventions, `date_echeance` for work orders).
When OFF, all active items are shown. Client-side filtering, matching the existing
client-filter pattern; the backend archive sweep already removes past-day items so
the active set is effectively today + future.

## Tests (TDD — written before implementation)

### Backend (pytest, `tests/backend/`)

- `test_archive_boundary`:
  - row due yesterday → archived
  - row due today → not archived
  - row due tomorrow → not archived
  - row in terminal status with any date → archived
- `test_interventions_role_scope`:
  - ADMIN and CHEFTECH see all active interventions
  - TECHNICIEN sees only interventions where `technician_id == self`

### Frontend (Testing Library)

- `InterventionsTab`: today's item visible; yesterday/tomorrow item hidden with
  toggle ON, visible with toggle OFF.
- `WorkOrdersTab`: same behaviour keyed on `date_echeance`.

### Verification mapping

1. Today's interventions and WOs displayed → frontend Today-filter tests + role-scope.
2. Other-date items excluded from today's view → frontend toggle-ON tests.
3. Yesterday's items auto-archived → `test_archive_boundary` (yesterday case).
4. Archived records retrievable → existing `/api/v1/archive/{module}` + `ArchivePage`.

## Out of scope

- Archive page UI (already exists).
- Purge / retention changes.
- Per-user timezone localization (UTC only for now; configurable TZ is a future option).

## Risks

- **Timezone.** UTC day boundary may differ from operators' local midnight by a
  few hours. Accepted for now; revisit with a configurable TZ if needed.
- **Frontend pagination.** Today filter is client-side over the first 100 fetched
  rows. Acceptable given the archive sweep keeps the active set small; revisit with
  a backend `scheduled_date` filter if active volume grows.
