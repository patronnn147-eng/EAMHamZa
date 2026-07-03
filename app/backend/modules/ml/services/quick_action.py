"""
Quick Action — ADMIN one-click parts auto-provisioning.

Splits PURE decision logic (this section) from the async DB orchestrator
(added in a later task). Pure helpers are unit-tested without a DB, matching the
project's pure-function test convention (see parts_drafts / readiness tests).

Guarantees enforced by the orchestrator: atomicity, machine-row lock
(concurrency), idempotency via execution hash, server-side source of truth.
"""

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional


# ── Pure helpers (no DB) ───────────────────────────────────────────────────


def _slug(name: str) -> str:
    """lowercase, non-alphanumeric → '-', collapse repeats, trim. Fallback 'part'."""
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "part"


def _short_hash(name: str, machine_id: int) -> str:
    """First 6 hex chars of sha1(name + machine_id) — collision guard for refs."""
    return hashlib.sha1(f"{name}{machine_id}".encode("utf-8"), usedforsecurity=False).hexdigest()[:6]  # nosemgrep: insecure-hash-algorithm-sha1 -- non-cryptographic use (short reference-id generator), usedforsecurity=False


def _canonical_item(item: Dict[str, Any]) -> List[Any]:
    """Stable, comparable projection of a recommendation item."""
    return [
        item.get("piece_id"),
        item.get("reference") or "",
        (item.get("name") or "").strip().lower(),
        round(float(item.get("expected_qty", 0.0) or 0.0), 3),
        round(float(item.get("recommended_order_qty", 0.0) or 0.0), 3),
        item.get("driver") or "",
    ]


def _execution_hash(items: List[Dict[str, Any]], machine_id: int) -> str:
    """Deterministic, order-independent sha256 over canonical items + machine_id."""
    canon = sorted(
        (_canonical_item(i) for i in items), key=lambda c: json.dumps(c, sort_keys=True)
    )
    payload = json.dumps({"machine_id": machine_id, "items": canon}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _target_qty(expected_qty: float, min_stock: float, is_consumable: bool):
    """target = max(expected_qty, min_stock). Non-consumable → ceil to whole units."""
    target = max(float(expected_qty or 0.0), float(min_stock or 0.0), 0.0)
    if not is_consumable:
        return int(math.ceil(target))
    return round(target, 2)


def _driver_to_category(driver: str) -> str:
    """Category for auto-created pieces, derived from the recommendation driver."""
    return {"condition": "Predictive", "consumption": "Consumable"}.get(
        driver, "General"
    )


# ── Plan builder (pure) ────────────────────────────────────────────────────


def _new_ref(name: str, machine_id: int) -> str:
    # Normalise to lower so "Gasket" and "gasket" produce the same ref (intra-run dedup).
    norm = (name or "").strip().lower()
    return f"QA-{machine_id}-{_slug(norm)}-{_short_hash(norm, machine_id)}"


def build_execution_plan(
    items: List[Dict[str, Any]],
    machine_id: int,
    pieces_by_id: Dict[int, Dict[str, Any]],
    pieces_by_ref: Dict[str, Dict[str, Any]],
    pieces_by_lname: Dict[str, Dict[str, Any]],
    stock_by_piece_id: Dict[int, float],
) -> Dict[str, Any]:
    """
    Decide, per recommendation item: how the piece resolves, the target qty,
    and the stock delta. Pure — no DB. The orchestrator executes the result.

    Maps:
      pieces_by_id     {piece_id: piece_dict}
      pieces_by_ref    {reference: piece_dict}        (exact)
      pieces_by_lname  {name.lower(): piece_dict}     (exact, case-insensitive)
      stock_by_piece_id{piece_id: on_hand_float}

    Each piece_dict has: id, reference, name, min_stock, is_consumable, default_unit.

    Returns {"ops": [op...], "summary": {...}}. For 'create' ops piece_id is None
    (DB assigns later); op carries 'reference' + 'create_spec'. Intra-run creates
    with the same generated reference are merged (one piece, max target; the
    larger-target item's driver also sets the category).

    Quantity is driven by ``expected_qty`` (+ piece min_stock); ``recommended_order_qty``
    is part of the idempotency hash but is NOT used for sizing here. Unresolved
    items with a blank name are skipped (no junk catalog rows).
    """
    ops: List[Dict[str, Any]] = []
    planned_creates: Dict[str, Dict[str, Any]] = {}  # new_ref → op (intra-run dedup)

    def _resolve(item):
        pid = item.get("piece_id")
        if pid is not None and pid in pieces_by_id:
            return "id", pieces_by_id[pid]
        ref = item.get("reference")
        if ref and ref in pieces_by_ref:
            return "reference", pieces_by_ref[ref]
        lname = (item.get("name") or "").strip().lower()
        if lname and lname in pieces_by_lname:
            return "name", pieces_by_lname[lname]
        return "create", None

    for item in items:
        name = item.get("name") or ""
        expected = float(item.get("expected_qty", 0.0) or 0.0)
        driver = item.get("driver") or ""
        resolution, piece = _resolve(item)

        if resolution == "create":
            # Never auto-create a piece from a nameless recommendation — the
            # generated reference would collapse to "QA-{id}-part-…" and the
            # catalog row would have a blank name. Skip such items entirely.
            if not name.strip():
                continue
            new_ref = _new_ref(name, machine_id)
            min_stock = int(math.ceil(expected))
            target = _target_qty(expected, min_stock, is_consumable=False)
            if new_ref in planned_creates:
                # Merge duplicate within the same run — keep the larger target.
                # When the larger-target item wins, its driver also wins (category).
                prev = planned_creates[new_ref]
                if target > prev["target_qty"]:
                    prev["target_qty"] = target
                    prev["qty_added"] = target  # on_hand for a new piece is 0
                    prev["create_spec"]["min_stock"] = max(
                        prev["create_spec"]["min_stock"], min_stock
                    )
                    prev["create_spec"]["category"] = _driver_to_category(driver)
                continue
            op = {
                "name": name,
                "driver": driver,
                "resolution": "create",
                "action": "created",
                "piece_id": None,
                "reference": new_ref,
                "create_spec": {
                    "reference": new_ref,
                    "name": name,
                    "category": _driver_to_category(driver),
                    "min_stock": min_stock,
                    "default_unit": "pcs",
                    "is_consumable": False,
                },
                "on_hand_before": 0.0,
                "target_qty": target,
                "qty_added": target,
                "stock_action": "added" if target > 0 else "skipped",
            }
            planned_creates[new_ref] = op
            ops.append(op)
            continue

        # Existing piece (id / reference / name)
        min_stock = float(piece.get("min_stock") or 0)
        is_consumable = bool(piece.get("is_consumable"))
        target = _target_qty(expected, min_stock, is_consumable)
        on_hand = float(stock_by_piece_id.get(piece["id"], 0.0) or 0.0)
        delta = target - on_hand
        if delta < 0:
            delta = 0
        # quantize like the rest of the codebase (2 dp) but keep ints clean
        qty_added = (
            (int(delta) if not is_consumable else round(delta, 2)) if delta > 0 else 0
        )
        ops.append(
            {
                "name": name,
                "driver": driver,
                "resolution": resolution,
                "action": "existing",
                "piece_id": piece["id"],
                "reference": piece.get("reference"),
                "on_hand_before": on_hand,
                "target_qty": target,
                "qty_added": qty_added,
                "stock_action": "added" if delta > 0 else "skipped",
            }
        )

    summary = _summarize(ops)
    return {"ops": ops, "summary": summary}


def _summarize(ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "pieces_created": sum(1 for o in ops if o["action"] == "created"),
        "pieces_existing": sum(1 for o in ops if o["action"] == "existing"),
        "stock_updated": sum(1 for o in ops if o["stock_action"] == "added"),
        "skipped": sum(1 for o in ops if o["stock_action"] == "skipped"),
        "total_qty_added": round(sum(float(o["qty_added"]) for o in ops), 2),
    }


# ── Async orchestrator (DB) ────────────────────────────────────────────────
import logging  # noqa: E402
from typing import Tuple  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

logger = logging.getLogger(__name__)


async def _preload_maps(
    db: AsyncSession, items: List[Dict[str, Any]]
) -> Tuple[dict, dict, dict, dict]:
    """One batched read for pieces (by id/ref/name) + their stock. Avoids N+1."""
    from models.pieces import Piece
    from models.stock import Stock
    from sqlalchemy import or_, func as sa_func

    ids = {i["piece_id"] for i in items if i.get("piece_id") is not None}
    refs = {i["reference"] for i in items if i.get("reference")}
    lnames = {(i.get("name") or "").strip().lower() for i in items if i.get("name")}

    pieces_by_id, pieces_by_ref, pieces_by_lname = {}, {}, {}
    if ids or refs or lnames:
        conds = []
        if ids:
            conds.append(Piece.id.in_(ids))
        if refs:
            conds.append(Piece.reference.in_(refs))
        if lnames:
            conds.append(sa_func.lower(Piece.name).in_(lnames))
        rows = (await db.execute(select(Piece).where(or_(*conds)))).scalars().all()
        for p in rows:
            pd = {
                "id": p.id,
                "reference": p.reference,
                "name": p.name,
                "min_stock": p.min_stock,
                "is_consumable": p.is_consumable,
                "default_unit": p.default_unit,
            }
            pieces_by_id[p.id] = pd
            if p.reference:
                pieces_by_ref[p.reference] = pd
            pieces_by_lname[(p.name or "").strip().lower()] = pd

    stock_by_piece_id: Dict[int, float] = {}
    if pieces_by_id:
        srows = (
            await db.execute(
                select(Stock.piece_id, Stock.quantity).where(
                    Stock.piece_id.in_(pieces_by_id.keys())
                )
            )
        ).fetchall()
        for piece_id, qty in srows:
            stock_by_piece_id[piece_id] = float(qty or 0.0)

    return pieces_by_id, pieces_by_ref, pieces_by_lname, stock_by_piece_id


async def quick_provision_parts(
    machine_id: int,
    actor_user_id: Optional[int],
    db: AsyncSession,
    parts_demand: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Provision recommended parts → pieces + stock, atomically.

    Caller passes `parts_demand` already fetched server-side (router does this
    via get_unified_health). One transaction: machine row lock → idempotency
    check → preload → apply plan → record run → commit. dry_run rolls back.
    Never raises; returns {"success": False, "error": ...} on failure.
    """
    from models.machines import Machines
    from models.pieces import Piece
    from models.quick_action_run import QuickActionRun
    from services.inventory.stock import StockService

    items = (parts_demand or {}).get("items") or []
    if not items:
        return {"success": False, "message": "No recommended parts for this machine"}

    try:
        # Inside the try so the "never raises" contract holds even if an item
        # carries a non-serializable value.
        exec_hash = _execution_hash(items, machine_id)

        # 1. Lock the machine row (serialize per machine).
        locked = await db.execute(
            select(Machines.id).where(Machines.id == machine_id).with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            await db.rollback()  # release the lock; no writes
            return {"success": False, "error": f"Machine {machine_id} not found"}

        # 2. Idempotency: replay a prior run with the same machine + hash.
        prior = await db.execute(
            select(QuickActionRun.result_json).where(
                QuickActionRun.hash == exec_hash,
                QuickActionRun.machine_id == machine_id,
            )
        )
        prior_json = prior.scalar_one_or_none()
        if prior_json is not None:
            await db.rollback()  # release the lock; no writes
            stored = json.loads(prior_json)
            stored["idempotent"] = True
            stored["dry_run"] = dry_run
            return stored

        # 3. Preload + build the plan (pure).
        pid_map, ref_map, lname_map, stock_map = await _preload_maps(db, items)
        plan = build_execution_plan(
            items, machine_id, pid_map, ref_map, lname_map, stock_map
        )

        # 4. Apply: create pieces, then top up stock.
        stock_svc = StockService(db)
        for op in plan["ops"]:
            if op["resolution"] == "create":
                spec = op["create_spec"]
                # Re-check for an existing piece with the generated reference (collision-safe).
                existing = await db.scalar(
                    select(Piece).where(Piece.reference == spec["reference"])
                )
                if existing is None:
                    piece = Piece(
                        reference=spec["reference"],
                        name=spec["name"],
                        category=spec["category"],
                        min_stock=spec["min_stock"],
                        default_unit=spec["default_unit"],
                        is_consumable=spec["is_consumable"],
                    )
                    db.add(piece)
                    await db.flush()  # assign id, no commit
                    op["piece_id"] = piece.id
                else:
                    op["piece_id"] = existing.id
            if (
                op["stock_action"] == "added"
                and op["qty_added"]
                and op["piece_id"] is not None
            ):
                await stock_svc.add_stock(
                    piece_id=op["piece_id"],
                    quantity=op["qty_added"],
                    reference="quick-action",
                    auto_commit=False,
                )

        result = {
            "success": True,
            "machine_id": machine_id,
            "execution_hash": exec_hash,
            "idempotent": False,
            "dry_run": dry_run,
            "summary": plan["summary"],
            "items": [
                {
                    "piece_id": o["piece_id"],
                    "name": o["name"],
                    "action": o["action"],
                    "stock_action": o["stock_action"],
                    "qty_added": o["qty_added"],
                    "target_qty": o["target_qty"],
                    "on_hand_before": o["on_hand_before"],
                }
                for o in plan["ops"]
            ],
            "message": "Quick Action completed successfully",
        }

        if dry_run:
            await db.rollback()  # guarantee zero writes
            result["message"] = "Dry run — no changes applied"
            return result

        # 5. Record the run (inside the same tx) and commit.
        db.add(
            QuickActionRun(
                machine_id=machine_id,
                hash=exec_hash,
                result_json=json.dumps(result),
            )
        )
        await db.commit()
        logger.info(
            f"[quick_action] machine {machine_id}: {plan['summary']} (actor={actor_user_id})"
        )
        return result

    except Exception as e:
        await db.rollback()
        logger.error(f"[quick_action] machine {machine_id} failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
