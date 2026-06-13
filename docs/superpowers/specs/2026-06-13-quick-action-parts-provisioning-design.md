# Quick Action — Parts Auto-Provisioning (Design Spec V2)

**Date:** 2026-06-13
**Branch:** `clean_Phase_1`
**Version:** V2 — Atomic + Concurrency-Safe + Idempotent
**Status:** Approved (brainstorming) → ready for implementation plan

## Goal

One ADMIN click converts ML-recommended parts (`parts_demand.items` from
unified-health) into:

- valid `Piece` records (created if missing)
- correct `Stock` levels (auto-adjusted up to need)

executed **safely, atomically, and without duplication, even under concurrent use.**

Deliberate **fast path** that writes inventory directly — distinct from the existing
guarded draft-work-order flow (`parts_drafts.py` / `ProcurementRecommendationModal`),
which stays unchanged.

## Core Guarantees (non-negotiable)

1. **Atomicity (strict)** — all operations succeed or all roll back. No partial success.
2. **Concurrency safety** — multiple clicks (same or different admins) must not corrupt stock.
3. **Idempotency** — same action triggered twice → no duplicate effects.
4. **Server authority** — all logic derived from server-side `get_unified_health`. Client payload never trusted for what gets written.

## Decisions (locked)

| Question | Decision |
|----------|----------|
| Guard model | Direct write, **ADMIN-only**. |
| Quantity logic | Bring stock up to need: `target = max(expected_qty, min_stock)`; add only the delta. |
| Scope | **All** recommended items in `parts_demand`. |
| Piece resolution | **Strict** (no fuzzy): `piece_id` (must exist, else ignore that hint) → `reference` exact → `name` exact (case-insensitive) → else create. |
| Source of truth | Server re-fetches `parts_demand` via `get_unified_health(machine_id, db)`. |
| Concurrency | Row lock on `machines` (`SELECT … FOR UPDATE`). |
| Idempotency | Deterministic execution hash persisted in `quick_action_runs`. |
| Dry run | `?dry_run=true` returns the plan, writes nothing. |

## High-Level Flow

1. User clicks **Quick Action**.
2. Backend:
   - locks the machine row (`FOR UPDATE`),
   - re-fetches fresh `parts_demand`,
   - computes deterministic execution hash; if already run → return stored result (no-op),
   - preloads pieces + stock (no N+1),
   - computes a deterministic execution plan,
   - executes all writes in one transaction, records the run, commits.
3. Returns a structured summary.

## Backend Architecture

### New table — `quick_action_runs`

```
quick_action_runs(
  id           SERIAL PK,
  machine_id   INTEGER NOT NULL,          -- FK machines.id (no cascade needed)
  hash         VARCHAR(64) NOT NULL UNIQUE,
  result_json  TEXT NOT NULL,             -- the structured response, replayed on idempotent hit
  executed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
-- UNIQUE(hash) is the idempotency guard. Index on machine_id for lookups.
```

- **Model:** `app/backend/models/quick_action_run.py` (`QuickActionRun`).
- **Migration:** new Alembic version `quick_action_runs` under
  `app/backend/alembic/versions/`. `down_revision` = current head (resolve via
  `alembic heads` at implementation time). Idempotent guard using the existing
  `information_schema` table-exists pattern (mirror `p7_parts_demand_column.py`).

### New service — `app/backend/modules/ml/services/quick_action.py`

```python
async def quick_provision_parts(
    machine_id: int,
    actor_user_id: int | None,
    db: AsyncSession,
    dry_run: bool = False,
) -> dict
```

Pure helpers (DB-free, unit-testable): `_slug`, `_short_hash`, `_execution_hash`,
`_target_qty`, `_driver_to_category`, `_summarize`.

#### Step 1 — Concurrency control

Before any work, acquire a row lock on the machine inside the transaction:

```python
await db.execute(select(Machines.id).where(Machines.id == machine_id).with_for_update())
```

Serializes Quick Action for the same machine. Parallel requests queue; the second
sees the first run's `quick_action_runs` row and short-circuits (idempotency).

#### Step 2 — Idempotency

- Build canonical payload from the recommendation: sorted list of
  `(piece_id, reference, name, round(expected_qty,3), round(recommended_order_qty,3), driver)`
  plus `machine_id`.
- `execution_hash = sha256(canonical_json).hexdigest()`.
- Look up `quick_action_runs.hash`:
  - **hit** → return stored `result_json` with `idempotent: true` (no writes).
  - **miss** → proceed.
- `dry_run=true` computes the hash and plan but **never** inserts a run row and never commits.

#### Step 3 — Data preloading (no N+1)

From the recommendation items collect candidate references / names / piece_ids, then:

```python
SELECT * FROM pieces WHERE id IN (:ids) OR reference IN (:refs) OR lower(name) IN (:lnames)
SELECT * FROM stock  WHERE piece_id IN (:resolved_piece_ids)
```

Build maps: `pieces_by_id`, `pieces_by_ref`, `pieces_by_lname`, `stock_by_piece_id`.
(Stock for newly created pieces loaded/assumed absent → on_hand 0.)

#### Step 4 — Piece resolution (strict, no fuzzy)

For each item, in order:

1. `item.piece_id` → use **only if** it resolves to an existing row in `pieces_by_id`; otherwise ignore the hint.
2. `item.reference` → **exact** match in `pieces_by_ref`.
3. `item.name` → **exact** match, case-insensitive, in `pieces_by_lname`.
4. Else → **create** (Step 5).

No `ilike '%…%'` fuzzy matching anywhere.

#### Step 5 — Safe piece creation

```
reference = QA-{machine_id}-{slug(name)}-{short_hash}
short_hash = sha1(f"{name}{machine_id}").hexdigest()[:6]
slug(name) = lowercase, non-alphanumeric → '-', collapse repeats, trim
```

Collision-safe: if that reference already exists (preloaded or unique-violation on
flush), reuse the existing row instead of inserting a duplicate. Defaults:

- `min_stock = ceil(expected_qty)`
- `default_unit = "pcs"`
- `is_consumable = False`

Newly created pieces are added to the in-memory maps so later items in the same run
resolve to them (no intra-run duplicates).

#### Step 6 — Quantity logic

```
target_qty = max(expected_qty, piece.min_stock or 0)
```

- Non-consumable → `ceil(target_qty)`
- Consumable → keep decimal (`Numeric(10,2)`)

#### Step 7 — Stock update

```
delta = target_qty - on_hand            # on_hand from stock_by_piece_id (live, server-side)
```

- `delta > 0` → `StockService.add_stock(piece_id, delta, reference="quick-action", auto_commit=False)` (creates stock row if absent, tops up if present, logs `MouvementStock` type=`in`).
- `delta <= 0` → skip, record `stock_action="skipped"`.

#### Step 8 — Transaction (strict)

```
acquire machine FOR UPDATE
check idempotency hash → maybe short-circuit
preload pieces + stock
for each item: resolve → target → delta → (apply stock change unless dry_run)
if not dry_run:
    INSERT quick_action_runs(hash, machine_id, result_json)
    db.commit()
else:
    db.rollback()   # guarantee zero writes
```

Any error → `db.rollback()`, return `{success: false, error: <message>}`. The
`quick_action_runs` insert is inside the same transaction, so a run is recorded only
if every write succeeded.

### Response format

```json
{
  "success": true,
  "machine_id": 42,
  "execution_hash": "abc123…",
  "idempotent": false,
  "dry_run": false,
  "summary": {
    "pieces_created": 2,
    "pieces_existing": 5,
    "stock_updated": 4,
    "skipped": 3,
    "total_qty_added": 17.0
  },
  "items": [
    {"piece_id": 12, "name": "Bearing 6204", "action": "created|existing",
     "stock_action": "added|skipped", "qty_added": 4.0, "target_qty": 6, "on_hand_before": 2}
  ],
  "message": "Quick Action completed successfully"
}
```

Error: `{"success": false, "error": "Detailed error message"}`.

### API endpoint — `app/backend/modules/ml/router.py`

```
POST /api/v1/ml/procurement/quick-action/{machine_id}?dry_run=false
```

- `current_user = Depends(get_current_user)`, `db = Depends(get_db)`.
- **ADMIN guard** (mirror `rag_docs._require_admin`): `403` if role != `"ADMIN"`.
- Re-fetch `parts_demand` server-side via `get_unified_health(machine_id, db)`. Empty/missing items → `{success: false, message: "No recommended parts for this machine"}`.
- Call `quick_provision_parts(machine_id, current_user.id, db, dry_run=dry_run)`; return its dict.

## Frontend

### Button — `PartsDemandCard` in `MLIntelligenceTab.tsx`

- Card header button row, next to "Why?" / "Order Required" badge.
- Label **"Quick Action"**, pill style matching siblings (Space Grotesk, rounded `999`, `accentColor`).
- Visible only when `role === 'ADMIN' && demand.items.length > 0` (`useUserRole()` from `@/hooks/usePermission`).

### Flow

- `useToast()` from `@/hooks/use-toast`.
- Click → `loading=true` (button spinner, disabled) → `POST …/quick-action/{machineId}`.
- Success → toast summary (`"{pieces_created} created · {stock_updated} stock updated"`; note `idempotent` → "already up to date"); refetch unified-health so the card refreshes.
- Error → destructive toast with `error`/`message`.
- `finally` → `loading=false`.
- No new modal.

## Testing

- **Unit (no DB):** `_slug`, `_short_hash`, `_execution_hash` (stable + order-independent), `_target_qty` (ceil vs decimal), `_driver_to_category`, `_summarize`.
- **Backend (DB):**
  - all-new pieces → created + stock added, correct deltas;
  - mixed existing/new → no duplicate pieces, existing topped up;
  - **double click (same payload)** → second call idempotent no-op, returns stored result;
  - **parallel requests** → row lock serializes, no double stock add;
  - existing stock ≥ target → `skipped`, no movement;
  - empty `parts_demand` → `success:false`, no writes;
  - `dry_run=true` → plan returned, zero DB writes (no pieces, no stock, no run row);
  - non-ADMIN → 403;
  - forced mid-transaction error → full rollback, no run row, no partial pieces/stock.

## Assumptions

1. `get_unified_health(machine_id, db)` is the trusted server-side `parts_demand` source.
2. Recommended `piece_id` may or may not reference a real row; strict resolution handles both.
3. Auto-reference `QA-{machine_id}-{slug(name)}-{short_hash}` is acceptable.
4. Audit via `MouvementStock` (`reference="quick-action"`) + the `quick_action_runs` row is sufficient.
5. Auto-created pieces default to non-consumable, `pcs`.

## Out of scope

- Changing the guarded draft-WO flow.
- Reservation logic (`required_pieces`).
- Supplier / purchase-order integration.
