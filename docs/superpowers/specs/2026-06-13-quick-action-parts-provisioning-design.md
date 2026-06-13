# Quick Action — Parts Auto-Provisioning (Design Spec)

**Date:** 2026-06-13
**Branch:** `clean_Phase_1`
**Status:** Approved (brainstorming) → ready for implementation plan

## Goal

One ADMIN click on a machine's ML Intelligence tab turns the **recommended pieces**
(`parts_demand.items` from unified-health) into real catalog **pieces** and **stock
entries**, in a single atomic transaction.

This is a deliberate **fast path** that writes inventory directly — distinct from the
existing guarded draft-work-order flow (`parts_drafts.py` / `ProcurementRecommendationModal`),
which stays unchanged.

## Decisions (locked during brainstorming)

| Question | Decision |
|----------|----------|
| Guard model | **Direct write, ADMIN-only.** One click commits pieces + stock. |
| Quantity logic | **Bring stock up to need:** target = `max(expected_qty, min_stock)`; add only the delta. `ceil()` for non-consumables. |
| Scope | **All recommended items** in `parts_demand` (not just shortfall rows). |
| Piece resolution | Resolve-or-create: `piece_id` (existing row) → `reference` match → `name` match (case-insensitive) → else **create** new `Piece`. |
| Source of truth | Server re-fetches `parts_demand` via `get_unified_health(machine_id, db)`. Client payload is NOT trusted for what gets written. |

## Architecture

### Backend

#### New service — `app/backend/modules/ml/services/quick_action.py`

Single public async function plus small pure helpers. Reuses `StockService` and
`PieceService` rather than re-implementing stock/piece logic.

```
async def quick_provision_parts(
    machine_id: int,
    parts_demand: dict,
    actor_user_id: int | None,
    db: AsyncSession,
) -> dict
```

Behaviour:

- **One transaction.** All stock writes use `auto_commit=False`. Single `db.commit()`
  at the end. Any fatal error → `db.rollback()`, return `{success: False, error: ...}`.
- **Per recommended item:**
  1. `_resolve_piece(item, db)` →
     - if `item.piece_id` resolves to an existing `Piece` row → use it (`existing`);
     - else lookup by `reference` (exact) → use it (`existing`);
     - else lookup by `name` (case-insensitive `ilike`) → use it (`existing`);
     - else **create** `Piece(reference=<resolved or auto-gen>, name, category=<driver→category>, min_stock=ceil(expected_qty), default_unit="pcs")` (`created`).
       Auto-gen reference when item carries none: `QA-{machine_id}-{slug(name)}` (slug = lowercased, non-alnum→`-`, trimmed). Dedup-safe: if that reference collides, reuse the colliding row.
  2. **Target qty** = `max(expected_qty, piece.min_stock or 0)`. Non-consumable (`is_consumable == False`) → `math.ceil()`. Consumable → keep fractional (`Numeric(10,2)`).
  3. **Live on_hand** read from `Stock` server-side (ignore client `on_hand`).
  4. **Delta** = `target - on_hand`. If `delta > 0` → `StockService.add_stock(piece_id, delta, reference="quick-action", intervention_id=None, auto_commit=False)` (creates stock row if absent, tops up if present, logs `MouvementStock` movement_type=`in`). If `delta <= 0` → skip, record `stock_action="skipped"`.
- **Per-item errors are caught** and pushed to `errors[]` with the item name; one bad
  item does not abort the others UNLESS it's a transaction-fatal DB error (then rollback all).

**Structured return:**

```json
{
  "success": true,
  "machine_id": 42,
  "summary": {
    "pieces_created": 2,
    "pieces_existing": 5,
    "stock_updated": 4,
    "skipped": 3,
    "total_qty_added": 17.0
  },
  "items": [
    {"piece_id": 12, "name": "Bearing 6204", "action": "existing",
     "stock_action": "added", "qty_added": 4.0, "target_qty": 6, "on_hand_before": 2}
  ],
  "errors": []
}
```

Never raises to the router for per-item issues; only a transaction-fatal failure
returns `{success: False}`.

#### New endpoint — `app/backend/modules/ml/router.py`

```
POST /api/v1/ml/procurement/quick-action/{machine_id}
```

- `current_user = Depends(get_current_user)`, `db = Depends(get_db)`.
- **ADMIN guard** replicating the `rag_docs._require_admin` pattern: read role from
  user, `raise HTTPException(403)` if `!= "ADMIN"`.
- Re-fetch `parts_demand` server-side: `raw = await get_unified_health(machine_id, db)`;
  `parts_demand = raw.get("parts_demand")`. If missing/empty items →
  `{success: False, message: "No recommended parts for this machine"}`.
- Call `quick_provision_parts(...)`, return its dict.

### Frontend

#### Button — `PartsDemandCard` in `MLIntelligenceTab.tsx`

- Placed in the card **header**, in the existing right-aligned button row next to
  "Why?" and the "Order Required" badge.
- Label: **"Quick Action"**. Pill style matching siblings: Space Grotesk, rounded
  `999`, accent background/border (use `accentColor` already computed in the card).
- **ADMIN-only:** `const role = useUserRole()` (from `@/hooks/usePermission`); render
  button only when `role === 'ADMIN'`. Only shown when `demand.items.length > 0`.

#### Flow

- `useToast()` from `@/hooks/use-toast`.
- Click handler:
  1. set `loading=true` (button shows `Loader2` spinner, disabled).
  2. `POST ${API}/api/v1/ml/procurement/quick-action/${machineId}` with `Authorization: Bearer <token>`.
  3. On `success`: toast success — `"{pieces_created} created · {stock_updated} stock entries updated"`; trigger a refetch of unified-health so the card refreshes (lift a `onProvisioned` callback or reuse existing refetch mechanism in the tab).
  4. On failure / network error: toast destructive variant with `message`/`error`.
  5. `finally`: `loading=false`.
- **No new modal** — inline button + toast (satisfies Step 4: loading + feedback).

## Atomicity / Dedup / Quality

- Single DB transaction; rollback-all on fatal error.
- Dedup is structural: resolve-before-create never duplicates a piece by reference;
  `add_stock` tops up the existing stock row, never inserts a second.
- No hardcoded quantities — every number derived from the recommendation + live stock.
- Modular: service composes `StockService` + `PieceService`; pure helpers
  (`_slug`, `_target_qty`, `_driver_to_category`) unit-testable without a DB.

## Testing

- **Unit (no DB):** `_slug`, `_target_qty` (ceil vs fractional), `_driver_to_category`,
  summary aggregation from a list of item-results.
- **Backend (DB):**
  - all-new pieces → created + stock added, correct deltas;
  - mix of existing/new → no duplicate pieces, existing topped up;
  - item already at/above target → `skipped`, no movement;
  - empty `parts_demand` → `success:False` message, no writes;
  - non-ADMIN → 403;
  - forced mid-transaction error → full rollback (no partial pieces/stock).

## Assumptions

1. `get_unified_health(machine_id, db)` is the trusted server-side source for
   `parts_demand` (already used by `chat_context.get_ml_snapshot`).
2. Recommended `piece_id` may or may not reference a real row — resolution handles both.
3. Auto-generated reference format `QA-{machine_id}-{slug(name)}` is acceptable for
   pieces created without a reference.
4. Audit trail via the existing `MouvementStock` row (`reference="quick-action"`) is
   sufficient — no separate audit table.
5. Default unit `"pcs"`, `is_consumable=False` for auto-created pieces unless the
   recommendation/category implies a consumable (kept simple: non-consumable default).

## Out of scope

- Changing the existing guarded draft-WO flow.
- Reservation logic (`required_pieces`) — Quick Action only provisions catalog + stock.
- Supplier / purchase-order integration.
