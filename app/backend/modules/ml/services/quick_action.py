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
