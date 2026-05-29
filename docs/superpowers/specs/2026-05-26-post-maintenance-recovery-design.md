# Post-Maintenance Recovery Detection — Design Spec

**Date:** 2026-05-26  
**Status:** Approved

---

## Context

The existing ML pipeline (P1–P6 + Wave 2 DST fusion) predicts machine failures and computes a `unified_health_score` (0–100). What is missing is a way to measure whether a completed work order actually improved the machine's condition — and by how much.

This feature adds **pre/post health snapshots** to work orders and computes a recovery delta using the same models already in production. No new models are trained; the existing `unified_health_score` is the single signal.

---

## Goal

When a work order is completed, show:

> *"Health improved +23 points since WO #47 was opened (42 → 65). Status: Recovering."*

Displayed in:
1. The MLIntelligenceTab — new "Post-Maintenance Recovery" card
2. The work order detail page — before/after score row
3. The machine header/overview — recovery badge during 7-day window

---

## Architecture

### 1. Database — Two new columns on `ordres_travail`

```sql
health_score_at_creation   FLOAT  NULLABLE   -- unified_health_score when WO was created
health_score_at_completion FLOAT  NULLABLE   -- unified_health_score captured just before WO is completed
```

Migration: `app/backend/alembic/versions/XXXX_add_health_snapshots_to_ordres_travail.py`

No new tables. No changes to other models.

### 2. New Service — `app/backend/services/ml/recovery.py`

**`PostMaintenanceRecoveryService`**

```python
async def snapshot_health(machine_id: int, db: Session) -> float | None
```
- Calls existing `MLClient.get_unified_health(machine_id)` (already used in `router.py`)
- Returns `unified_health_score` or `None` if ML service is unavailable
- Non-blocking: failure never raises, always returns None silently

```python
def compute_recovery(
    work_order: OrdresTravail,
    current_score: float | None
) -> RecoveryResult
```
- Inputs: WO row + current live score
- Computes: `delta = current_score - health_score_at_creation`
- Returns `RecoveryResult` dataclass:

```python
@dataclass
class RecoveryResult:
    delta: float | None          # positive = improvement
    status: str                  # "Recovered" | "Recovering" | "No improvement" | "Monitoring"
    score_before: float | None   # health_score_at_creation
    score_after_completion: float | None  # health_score_at_completion
    current_score: float | None  # live score
    days_since_completion: int | None
    within_recovery_window: bool  # date_fin + 7 days > now
    work_order_id: int
```

**Recovery status logic:**

| Condition | Status |
|-----------|--------|
| WO not yet completed | `"Monitoring"` |
| delta > 0 AND current ≥ 75 | `"Recovered"` |
| delta > 0 AND current < 75 | `"Recovering"` |
| delta ≤ 0 | `"No improvement"` |
| Outside 7-day window | status preserved as history, `within_recovery_window=False` |
| No pre-snapshot (ML was down at creation) | `"No baseline"` |

**Threshold constants** (configurable in `core/config.py`):
```python
RECOVERY_HEALTHY_THRESHOLD = 75.0   # unified_health_score ≥ this → "Recovered"
RECOVERY_WINDOW_DAYS = 7
```

### 3. Integration Points — where snapshots are taken

**At WO creation** (snapshot pre-maintenance baseline):

Files to modify:
- `app/backend/modules/admin/admin_work_orders.py` — WO creation route
- `app/backend/modules/cheftech/cheftech_work_orders.py` — WO creation route

Pattern (both files, after WO row is committed):
```python
score = await recovery_service.snapshot_health(machine_id, db)
if score is not None:
    work_order.health_score_at_creation = score
    db.commit()
```

**At WO completion** (snapshot pre-fix state):

Files to modify:
- `app/backend/modules/technicien/technicien_work_orders.py` — `complete` route
- `app/backend/modules/chetop/routes/work_orders.py` — `complete` route

Pattern (both files, before setting `date_fin` / `statut = COMPLETED`):
```python
score = await recovery_service.snapshot_health(machine_id, db)
if score is not None:
    work_order.health_score_at_completion = score
```
(Within same transaction as completion — committed once.)

### 4. API Changes

**Existing: `GET /api/v1/ml/machines/{id}/unified-health`** (`app/backend/modules/ml/router.py`)

Add `recovery` object to response:
```json
"recovery": {
  "delta": 23.0,
  "status": "Recovering",
  "score_before": 42.0,
  "score_after_completion": 44.0,
  "current_score": 65.0,
  "days_since_completion": 2,
  "within_recovery_window": true,
  "work_order_id": 47
}
```
- Fetches the most recent COMPLETED/VALIDATED/CLOSED WO for this machine
- Calls `compute_recovery(wо, current_score=unified_health_score)`

**Existing: WO detail response**

`app/backend/modules/shared/routes/ordres_travail/` — add `health_score_at_creation`, `health_score_at_completion`, and computed `recovery_delta` to the serialized WO response.

### 5. Frontend Changes

**A — `MLIntelligenceTab.tsx`** (`app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx`)

New card: **"Post-Maintenance Recovery"** (only rendered when `recovery` is present in unified-health response):

```
┌─────────────────────────────────────┐
│ Post-Maintenance Recovery           │
│ WO #47 · 2 days ago                 │
├─────────────────────────────────────┤
│ Before   42 ──────→  Now   65       │
│             +23 pts                 │
│ Status: Recovering  🟡              │
│ Recovery window: 5 days remaining   │
└─────────────────────────────────────┘
```

Color logic:
- Recovered → green card accent
- Recovering → orange/amber card accent
- No improvement → red card accent

**B — Work order detail page**

Add a "Health Impact" row to the completion summary section:
```
Before (WO opened):    42
At completion:         44
Now:                   65
Net improvement:       +23 pts
```

**C — Machine header / overview badge**

Add a small badge next to machine status during the 7-day window:
- "Recovered" → green badge
- "Recovering" → amber badge
- Only shown if `within_recovery_window = true`

---

## Data Flow

```
WO Created
  └─ async: snapshot_health(machine_id) → health_score_at_creation

Technician/ChefOp completes WO
  └─ snapshot_health(machine_id) → health_score_at_completion
  └─ WO saved (COMPLETED)

GET unified-health endpoint called
  └─ fetch latest completed WO for machine
  └─ compute_recovery(wo, current_unified_health_score)
  └─ append recovery object to response

Frontend renders:
  └─ MLIntelligenceTab: Recovery card
  └─ WO detail: Health Impact row
  └─ Machine header: recovery badge
```

---

## Error Handling

- ML service down at WO creation → `health_score_at_creation = NULL` → status becomes `"No baseline"`, no delta shown
- ML service down at completion → `health_score_at_completion = NULL` → delta still computable from creation snapshot + current
- No completed WO in last 7 days → `recovery` object omitted from response entirely
- Multiple WOs: only the most recently completed WO within the 7-day window is used

---

## Verification

1. Create a work order for a machine with poor health — confirm `health_score_at_creation` populated
2. Complete the WO — confirm `health_score_at_completion` populated
3. `GET /api/v1/ml/machines/{id}/unified-health` — confirm `recovery` object present with delta
4. Frontend: MLIntelligenceTab shows Recovery card with correct before/after values
5. Work order detail shows Health Impact row
6. Machine header shows recovery badge
7. After 7 days past `date_fin`, `within_recovery_window = false`, badge disappears

---

## Files Modified

| File | Change |
|------|--------|
| `app/backend/models/ordres_travail.py` | +2 nullable Float columns |
| `app/backend/alembic/versions/XXXX_add_health_snapshots.py` | New migration |
| `app/backend/services/ml/recovery.py` | New service (create) |
| `app/backend/modules/ml/router.py` | Add `recovery` to unified-health response |
| `app/backend/modules/admin/admin_work_orders.py` | Snapshot at creation |
| `app/backend/modules/cheftech/cheftech_work_orders.py` | Snapshot at creation |
| `app/backend/modules/technicien/technicien_work_orders.py` | Snapshot at completion |
| `app/backend/modules/chetop/routes/work_orders.py` | Snapshot at completion |
| `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` | New Recovery card |
| `app/frontend/src/lib/types.ts` | Add `RecoveryResult` type |
| WO detail page component | Health Impact row (file TBD from frontend exploration) |
| Machine header/overview component | Recovery badge (file TBD from frontend exploration) |
