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
    return hashlib.sha1(
        f"{name}{machine_id}".encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:6]


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
    canon = sorted((_canonical_item(i) for i in items), key=lambda c: json.dumps(c, sort_keys=True))
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
    return {"condition": "Predictive", "consumption": "Consumable"}.get(driver, "General")


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
    planned_creates: Dict[str, Dict[str, Any]] = {}   # new_ref → op (intra-run dedup)

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
                    prev["qty_added"] = target          # on_hand for a new piece is 0
                    prev["create_spec"]["min_stock"] = max(prev["create_spec"]["min_stock"], min_stock)
                    prev["create_spec"]["category"] = _driver_to_category(driver)
                continue
            op = {
                "name": name, "driver": driver, "resolution": "create",
                "action": "created", "piece_id": None, "reference": new_ref,
                "create_spec": {
                    "reference": new_ref, "name": name,
                    "category": _driver_to_category(driver),
                    "min_stock": min_stock, "default_unit": "pcs",
                    "is_consumable": False,
                },
                "on_hand_before": 0.0, "target_qty": target,
                "qty_added": target, "stock_action": "added" if target > 0 else "skipped",
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
        qty_added = (int(delta) if not is_consumable else round(delta, 2)) if delta > 0 else 0
        ops.append({
            "name": name, "driver": driver, "resolution": resolution,
            "action": "existing", "piece_id": piece["id"], "reference": piece.get("reference"),
            "on_hand_before": on_hand, "target_qty": target,
            "qty_added": qty_added,
            "stock_action": "added" if delta > 0 else "skipped",
        })

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
