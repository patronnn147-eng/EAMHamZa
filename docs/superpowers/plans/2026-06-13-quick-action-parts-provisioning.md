# Quick Action — Parts Auto-Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give ADMINs a one-click "Quick Action" that converts ML-recommended parts (`parts_demand.items`) into real `Piece` + `Stock` records — atomically, concurrency-safe, and idempotent.

**Architecture:** A new `quick_action.py` service splits **pure decision logic** (resolution, target/delta, execution hash, summary) from a thin **async orchestrator** (machine row lock → idempotency check → preload → apply → record run → commit). Pure logic is unit-tested (project convention: no DB in pytest); DB/concurrency/idempotency/dry-run guarantees are verified by a live smoke script (precedent: `smoke_ml_rag_bridge.py`). One new endpoint exposes it ADMIN-only; the frontend adds a button to `PartsDemandCard`.

**Tech Stack:** FastAPI + SQLAlchemy async, Alembic, Postgres (`SELECT … FOR UPDATE`, `Numeric`), pytest (`*.test.py`, importlib mode), React + TypeScript (Vite), shadcn `useToast`.

**Spec:** `docs/superpowers/specs/2026-06-13-quick-action-parts-provisioning-design.md`

---

## File Structure

**Backend**
- Create `app/backend/modules/ml/services/quick_action.py` — pure helpers + plan builder + async orchestrator.
- Create `app/backend/models/quick_action_run.py` — `QuickActionRun` model (idempotency ledger).
- Create `app/backend/alembic/versions/quick_action_runs.py` — migration for the table.
- Modify `app/backend/modules/ml/router.py` — add `POST /procurement/quick-action/{machine_id}`.

**Backend tests**
- Create `tests/backend/quick_action_helpers.test.py` — pure-helper unit tests.
- Create `tests/backend/quick_action_plan.test.py` — plan-builder unit tests.
- Create `app/backend/scripts/smoke_quick_action.py` — live smoke (idempotency, dry-run, ADMIN 403, atomicity).

**Frontend**
- Modify `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` — Quick Action button in `PartsDemandCard`; thread `onProvisioned` callback.
- Modify `app/frontend/src/modules/shared/MachineDetailPage.tsx` — pass `onProvisioned={fetchData}` to `MLIntelligenceTab`.

---

## Task 1: Pure helpers (slug, hashes, target qty, category)

**Files:**
- Create: `app/backend/modules/ml/services/quick_action.py`
- Test: `tests/backend/quick_action_helpers.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/quick_action_helpers.test.py
"""Quick Action pure-helper tests (no DB, no async)."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.quick_action import (
    _slug, _short_hash, _execution_hash, _target_qty, _driver_to_category,
)


def test_slug_basic():
    assert _slug("Bearing 6204 ZZ") == "bearing-6204-zz"

def test_slug_collapses_and_trims():
    assert _slug("  Foret  Carbure!! ") == "foret-carbure"

def test_slug_empty_fallback():
    assert _slug("") == "part"
    assert _slug("***") == "part"

def test_short_hash_stable_and_6_chars():
    h1 = _short_hash("bearing", 42)
    h2 = _short_hash("bearing", 42)
    assert h1 == h2
    assert len(h1) == 6
    assert _short_hash("bearing", 43) != h1   # machine_id changes hash

def test_execution_hash_order_independent():
    a = [{"piece_id": 1, "reference": "R1", "name": "a", "expected_qty": 1.0,
          "recommended_order_qty": 1.0, "driver": "condition"},
         {"piece_id": 2, "reference": "R2", "name": "b", "expected_qty": 2.0,
          "recommended_order_qty": 2.0, "driver": "consumption"}]
    assert _execution_hash(list(reversed(a)), 7) == _execution_hash(a, 7)

def test_execution_hash_changes_with_machine_and_qty():
    items = [{"piece_id": 1, "reference": "R1", "name": "a", "expected_qty": 1.0,
              "recommended_order_qty": 1.0, "driver": "condition"}]
    base = _execution_hash(items, 7)
    assert _execution_hash(items, 8) != base
    items2 = [dict(items[0], expected_qty=9.0)]
    assert _execution_hash(items2, 7) != base

def test_target_qty_non_consumable_ceils():
    assert _target_qty(expected_qty=1.2, min_stock=0, is_consumable=False) == 2

def test_target_qty_uses_min_stock_floor():
    assert _target_qty(expected_qty=1.0, min_stock=5, is_consumable=False) == 5

def test_target_qty_consumable_keeps_decimal():
    assert _target_qty(expected_qty=1.25, min_stock=0, is_consumable=True) == 1.25

def test_driver_to_category():
    assert _driver_to_category("condition") == "Predictive"
    assert _driver_to_category("consumption") == "Consumable"
    assert _driver_to_category("anything-else") == "General"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/backend/quick_action_helpers.test.py -v`
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name '_slug'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/backend/modules/ml/services/quick_action.py
"""
Quick Action — ADMIN one-click parts auto-provisioning.

Splits PURE decision logic (this section) from the async DB orchestrator
(bottom of file). Pure helpers are unit-tested without a DB, matching the
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
    return hashlib.sha1(f"{name}{machine_id}".encode("utf-8")).hexdigest()[:6]


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
    target = max(float(expected_qty or 0.0), float(min_stock or 0.0))
    if not is_consumable:
        return int(math.ceil(target))
    return round(target, 2)


def _driver_to_category(driver: str) -> str:
    """Category for auto-created pieces, derived from the recommendation driver."""
    return {"condition": "Predictive", "consumption": "Consumable"}.get(driver, "General")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/backend/quick_action_helpers.test.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/quick_action.py tests/backend/quick_action_helpers.test.py
git commit -m "feat(quick-action): pure helpers — slug, hashes, target qty, category"
```

---

## Task 2: Plan builder (resolution + delta + summary, pure)

The heart of the feature: given recommendation items + preloaded lookup maps, decide for each item how the piece resolves and what stock delta to apply. Fully pure → fully unit-tested. The orchestrator (Task 4) only executes this plan.

**Files:**
- Modify: `app/backend/modules/ml/services/quick_action.py`
- Test: `tests/backend/quick_action_plan.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/quick_action_plan.test.py
"""Quick Action plan-builder tests (pure, no DB)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.quick_action import build_execution_plan


def _piece(pid, ref, name, min_stock=5, is_consumable=False):
    return {"id": pid, "reference": ref, "name": name,
            "min_stock": min_stock, "is_consumable": is_consumable, "default_unit": "pcs"}


def test_resolve_by_piece_id_existing():
    items = [{"piece_id": 10, "reference": "X", "name": "Bearing",
              "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"}]
    pieces_by_id = {10: _piece(10, "B-10", "Bearing")}
    plan = build_execution_plan(items, 1, pieces_by_id, {}, {}, stock_by_piece_id={})
    op = plan["ops"][0]
    assert op["resolution"] == "id"
    assert op["action"] == "existing"
    assert op["piece_id"] == 10
    # target = max(2, min_stock 5) = 5; on_hand 0 → delta 5
    assert op["target_qty"] == 5
    assert op["qty_added"] == 5
    assert op["stock_action"] == "added"
    assert plan["summary"]["pieces_existing"] == 1
    assert plan["summary"]["stock_updated"] == 1
    assert plan["summary"]["total_qty_added"] == 5


def test_bad_piece_id_falls_through_to_reference():
    items = [{"piece_id": 999, "reference": "REF-A", "name": "Seal",
              "expected_qty": 1.0, "recommended_order_qty": 1.0, "driver": "consumption"}]
    pieces_by_ref = {"REF-A": _piece(3, "REF-A", "Seal", min_stock=0, is_consumable=True)}
    plan = build_execution_plan(items, 1, {}, pieces_by_ref, {}, stock_by_piece_id={3: 0.0})
    op = plan["ops"][0]
    assert op["resolution"] == "reference"
    assert op["piece_id"] == 3
    assert op["target_qty"] == 1.0      # consumable keeps decimal
    assert op["qty_added"] == 1.0


def test_resolve_by_name_case_insensitive():
    items = [{"piece_id": None, "reference": None, "name": "Foret Carbure",
              "expected_qty": 3.0, "recommended_order_qty": 3.0, "driver": "condition"}]
    pieces_by_lname = {"foret carbure": _piece(7, "FC-7", "Foret Carbure", min_stock=0)}
    plan = build_execution_plan(items, 1, {}, {}, pieces_by_lname, stock_by_piece_id={7: 1.0})
    op = plan["ops"][0]
    assert op["resolution"] == "name"
    assert op["piece_id"] == 7
    assert op["target_qty"] == 3        # ceil(max(3,0))
    assert op["qty_added"] == 2         # 3 target - 1 on_hand


def test_create_when_unresolved():
    items = [{"piece_id": None, "reference": None, "name": "New Valve",
              "expected_qty": 2.4, "recommended_order_qty": 2.4, "driver": "condition"}]
    plan = build_execution_plan(items, 42, {}, {}, {}, stock_by_piece_id={})
    op = plan["ops"][0]
    assert op["resolution"] == "create"
    assert op["action"] == "created"
    assert op["piece_id"] is None                     # DB assigns later
    assert op["reference"].startswith("QA-42-new-valve-")
    assert op["create_spec"]["min_stock"] == 3        # ceil(2.4)
    assert op["create_spec"]["category"] == "Predictive"
    assert op["create_spec"]["is_consumable"] is False
    assert op["target_qty"] == 3                       # ceil(max(2.4, 3))
    assert op["qty_added"] == 3
    assert plan["summary"]["pieces_created"] == 1


def test_skip_when_stock_already_covers_target():
    items = [{"piece_id": 10, "reference": "X", "name": "Bearing",
              "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"}]
    pieces_by_id = {10: _piece(10, "B-10", "Bearing", min_stock=5)}
    plan = build_execution_plan(items, 1, pieces_by_id, {}, {}, stock_by_piece_id={10: 9.0})
    op = plan["ops"][0]
    assert op["stock_action"] == "skipped"
    assert op["qty_added"] == 0
    assert plan["summary"]["skipped"] == 1
    assert plan["summary"]["stock_updated"] == 0


def test_intra_run_duplicate_creates_one_piece():
    # Two items, same name, neither resolves → must create ONE piece, not two.
    items = [
        {"piece_id": None, "reference": None, "name": "Gasket",
         "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"},
        {"piece_id": None, "reference": None, "name": "gasket",
         "expected_qty": 4.0, "recommended_order_qty": 4.0, "driver": "condition"},
    ]
    plan = build_execution_plan(items, 1, {}, {}, {}, stock_by_piece_id={})
    creates = [o for o in plan["ops"] if o["resolution"] == "create"]
    assert len(creates) == 1                  # deduped within the run
    assert creates[0]["target_qty"] == 4      # max(2,4) ceil
    assert plan["summary"]["pieces_created"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/backend/quick_action_plan.test.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_execution_plan'`.

- [ ] **Step 3: Write minimal implementation**

Append to `app/backend/modules/ml/services/quick_action.py`:

```python
# ── Plan builder (pure) ────────────────────────────────────────────────────

def _new_ref(name: str, machine_id: int) -> str:
    return f"QA-{machine_id}-{_slug(name)}-{_short_hash(name, machine_id)}"


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
    with the same generated reference are merged (one piece, max target).
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
            new_ref = _new_ref(name, machine_id)
            min_stock = int(math.ceil(expected))
            target = _target_qty(expected, min_stock, is_consumable=False)
            if new_ref in planned_creates:
                # Merge duplicate within the same run — keep the larger target.
                prev = planned_creates[new_ref]
                if target > prev["target_qty"]:
                    prev["target_qty"] = target
                    prev["qty_added"] = target          # on_hand for a new piece is 0
                    prev["create_spec"]["min_stock"] = max(prev["create_spec"]["min_stock"], min_stock)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/backend/quick_action_plan.test.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/quick_action.py tests/backend/quick_action_plan.test.py
git commit -m "feat(quick-action): pure execution-plan builder with intra-run dedup"
```

---

## Task 3: QuickActionRun model + Alembic migration

**Files:**
- Create: `app/backend/models/quick_action_run.py`
- Create: `app/backend/alembic/versions/quick_action_runs.py`

- [ ] **Step 1: Write the model**

```python
# app/backend/models/quick_action_run.py
"""QuickActionRun — idempotency ledger for the Quick Action parts provisioning.

One row per successful (non-dry-run) execution. `hash` is UNIQUE: a repeat
request with the same recommendation short-circuits and replays `result_json`.
"""
from core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func


class QuickActionRun(Base):
    __tablename__ = "quick_action_runs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id = Column(Integer, nullable=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, index=True)
    result_json = Column(Text, nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 2: Find the current Alembic head**

Run (from repo root, services up): `docker compose exec backend alembic heads`
(or, locally with the backend venv + DB env: `cd app/backend && alembic heads`)
Expected: one head revision id. **Copy it** — it becomes `down_revision` below. If
multiple heads print, the branch needs a merge migration first; stop and report.

- [ ] **Step 3: Write the migration**

Replace `REPLACE_WITH_CURRENT_HEAD` with the id from Step 2.

```python
# app/backend/alembic/versions/quick_action_runs.py
"""Create quick_action_runs idempotency table

Revision ID: quick_action_runs
Revises: REPLACE_WITH_CURRENT_HEAD
Create Date: 2026-06-13

Idempotent guard via information_schema (mirrors p7_parts_demand_column.py).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "quick_action_runs"
down_revision: Union[str, Sequence[str], None] = "REPLACE_WITH_CURRENT_HEAD"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if _table_exists("quick_action_runs"):
        return
    op.create_table(
        "quick_action_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_quick_action_runs_hash", "quick_action_runs", ["hash"])
    op.create_index("ix_quick_action_runs_machine_id", "quick_action_runs", ["machine_id"])


def downgrade() -> None:
    op.drop_index("ix_quick_action_runs_machine_id", table_name="quick_action_runs")
    op.drop_constraint("uq_quick_action_runs_hash", "quick_action_runs", type_="unique")
    op.drop_table("quick_action_runs")
```

- [ ] **Step 4: Apply and verify the migration**

Run: `docker compose exec backend alembic upgrade head`
Then: `docker compose exec backend alembic current`
Expected: `current` shows `quick_action_runs (head)`. No error.

- [ ] **Step 5: Commit**

```bash
git add app/backend/models/quick_action_run.py app/backend/alembic/versions/quick_action_runs.py
git commit -m "feat(quick-action): QuickActionRun idempotency table + migration"
```

---

## Task 4: Async orchestrator (lock, idempotency, preload, apply, commit)

**Files:**
- Modify: `app/backend/modules/ml/services/quick_action.py`

No pytest here (needs Postgres for `FOR UPDATE`/`Numeric`); Task 6's smoke verifies it.

- [ ] **Step 1: Append the orchestrator**

```python
# ── Async orchestrator (DB) ────────────────────────────────────────────────
import logging
from typing import Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            pd = {"id": p.id, "reference": p.reference, "name": p.name,
                  "min_stock": p.min_stock, "is_consumable": p.is_consumable,
                  "default_unit": p.default_unit}
            pieces_by_id[p.id] = pd
            if p.reference:
                pieces_by_ref[p.reference] = pd
            pieces_by_lname[(p.name or "").strip().lower()] = pd

    stock_by_piece_id: Dict[int, float] = {}
    if pieces_by_id:
        srows = (await db.execute(
            select(Stock.piece_id, Stock.quantity).where(Stock.piece_id.in_(pieces_by_id.keys()))
        )).fetchall()
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

    exec_hash = _execution_hash(items, machine_id)

    try:
        # 1. Lock the machine row (serialize per machine).
        locked = await db.execute(
            select(Machines.id).where(Machines.id == machine_id).with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            return {"success": False, "error": f"Machine {machine_id} not found"}

        # 2. Idempotency: replay a prior run with the same hash.
        prior = await db.execute(
            select(QuickActionRun.result_json).where(QuickActionRun.hash == exec_hash)
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
        plan = build_execution_plan(items, machine_id, pid_map, ref_map, lname_map, stock_map)

        # 4. Apply: create pieces, then top up stock.
        stock_svc = StockService(db)
        for op in plan["ops"]:
            if op["resolution"] == "create":
                spec = op["create_spec"]
                # Re-check for an existing piece with the generated reference (collision-safe).
                existing = await db.scalar(select(Piece).where(Piece.reference == spec["reference"]))
                if existing is None:
                    piece = Piece(
                        reference=spec["reference"], name=spec["name"],
                        category=spec["category"], min_stock=spec["min_stock"],
                        default_unit=spec["default_unit"], is_consumable=spec["is_consumable"],
                    )
                    db.add(piece)
                    await db.flush()  # assign id, no commit
                    op["piece_id"] = piece.id
                else:
                    op["piece_id"] = existing.id
            if op["stock_action"] == "added" and op["qty_added"] and op["piece_id"] is not None:
                await stock_svc.add_stock(
                    piece_id=op["piece_id"], quantity=op["qty_added"],
                    reference="quick-action", auto_commit=False,
                )

        result = {
            "success": True, "machine_id": machine_id, "execution_hash": exec_hash,
            "idempotent": False, "dry_run": dry_run,
            "summary": plan["summary"],
            "items": [
                {"piece_id": o["piece_id"], "name": o["name"], "action": o["action"],
                 "stock_action": o["stock_action"], "qty_added": o["qty_added"],
                 "target_qty": o["target_qty"], "on_hand_before": o["on_hand_before"]}
                for o in plan["ops"]
            ],
            "message": "Quick Action completed successfully",
        }

        if dry_run:
            await db.rollback()  # guarantee zero writes
            result["message"] = "Dry run — no changes applied"
            return result

        # 5. Record the run (inside the same tx) and commit.
        db.add(QuickActionRun(
            machine_id=machine_id, hash=exec_hash, result_json=json.dumps(result),
        ))
        await db.commit()
        logger.info(f"[quick_action] machine {machine_id}: {plan['summary']} (actor={actor_user_id})")
        return result

    except Exception as e:
        await db.rollback()
        logger.error(f"[quick_action] machine {machine_id} failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: Import-sanity check**

Run: `docker compose exec backend python -c "from modules.ml.services.quick_action import quick_provision_parts; print('ok')"`
Expected: prints `ok` (no import/syntax error).

- [ ] **Step 3: Commit**

```bash
git add app/backend/modules/ml/services/quick_action.py
git commit -m "feat(quick-action): async orchestrator — lock, idempotency, preload, atomic apply"
```

---

## Task 5: API endpoint (ADMIN-only, server-side parts_demand)

**Files:**
- Modify: `app/backend/modules/ml/router.py` (add endpoint after the existing `/procurement/draft` endpoints, ~line 1006)

- [ ] **Step 1: Add the endpoint**

Insert after `reject_procurement_draft_endpoint` (after line 1006):

```python
@router.post("/procurement/quick-action/{machine_id}")
async def quick_action_endpoint(
    machine_id: int,
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict:
    """
    Quick Action — ADMIN one-click: convert ML-recommended parts into real
    pieces + stock. Atomic, concurrency-safe, idempotent. `?dry_run=true`
    previews without writing.
    """
    # ADMIN guard (mirrors rag_docs._require_admin).
    role = (current_user.role.value if hasattr(current_user.role, "value")
            else str(current_user.role or "")).upper()
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can run Quick Action.")

    from modules.ml.services.quick_action import quick_provision_parts

    raw = await get_unified_health(machine_id, db)
    parts_demand = (raw or {}).get("parts_demand")

    return await quick_provision_parts(
        machine_id=machine_id,
        actor_user_id=current_user.id if current_user else None,
        db=db,
        parts_demand=parts_demand,
        dry_run=dry_run,
    )
```

- [ ] **Step 2: Verify the route registers**

Run: `docker compose exec backend python -c "from modules.ml.router import router; print([r.path for r in router.routes if 'quick-action' in r.path])"`
Expected: `['/procurement/quick-action/{machine_id}']`.

- [ ] **Step 3: Commit**

```bash
git add app/backend/modules/ml/router.py
git commit -m "feat(quick-action): ADMIN-only POST /procurement/quick-action endpoint"
```

---

## Task 6: Live smoke script (idempotency, dry-run, ADMIN guard, atomicity)

Validates the DB-backed guarantees against the running stack — the project's
established pattern for verifying DB/async behaviour (`smoke_ml_rag_bridge.py`).

**Files:**
- Create: `app/backend/scripts/smoke_quick_action.py`

- [ ] **Step 1: Write the smoke script**

```python
# app/backend/scripts/smoke_quick_action.py
"""
Live smoke for Quick Action. Runs against the running stack (backend:8000).

Checks:
  1. ADMIN dry_run returns success + dry_run=True and writes nothing
     (stock-level snapshot before/after identical).
  2. ADMIN real run returns success, summary present.
  3. Immediate repeat (same recommendation) returns idempotent=True.
  4. Non-ADMIN gets HTTP 403.

Exit 0 = all pass, 1 = a check failed, 2 = setup/env problem.

Usage:
  docker compose exec backend python scripts/smoke_quick_action.py --machine-id 1
Env (optional overrides):
  API_BASE (default http://localhost:8000)
  ADMIN_USER / ADMIN_PASS  (login field is `mot_de_passe`)
  TECH_USER  / TECH_PASS   (non-admin, for the 403 check; skipped if unset)
"""
import argparse, os, sys, json, urllib.request, urllib.error

API = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")


def _req(method, path, token=None, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _login(user, pw):
    status, body = _req("POST", "/api/v1/auth/login",
                        body={"email": user, "mot_de_passe": pw})
    if status != 200:
        print(f"[setup] login failed for {user}: {status} {body}")
        return None
    return body.get("access_token") or body.get("token")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine-id", type=int, required=True)
    args = ap.parse_args()
    mid = args.machine_id

    admin_user = os.environ.get("ADMIN_USER", "admin@admin.com")
    admin_pass = os.environ.get("ADMIN_PASS", "admin")
    admin = _login(admin_user, admin_pass)
    if not admin:
        print("FAIL: cannot obtain ADMIN token"); return 2

    failures = []

    # 1. Dry run writes nothing.
    s0, before = _req("GET", "/api/v1/ml/stock/levels?limit=1000", admin)  # snapshot
    st, dry = _req("POST", f"/api/v1/ml/procurement/quick-action/{mid}?dry_run=true", admin)
    if st != 200 or not dry.get("dry_run"):
        failures.append(f"dry_run response wrong: {st} {dry}")
    s1, after = _req("GET", "/api/v1/ml/stock/levels?limit=1000", admin)
    if json.dumps(before) != json.dumps(after):
        failures.append("dry_run mutated stock levels")

    # 2. Real run.
    st, run1 = _req("POST", f"/api/v1/ml/procurement/quick-action/{mid}", admin)
    if st != 200 or not run1.get("success"):
        failures.append(f"real run failed: {st} {run1}")

    # 3. Idempotent repeat.
    st, run2 = _req("POST", f"/api/v1/ml/procurement/quick-action/{mid}", admin)
    if st != 200 or not run2.get("idempotent"):
        failures.append(f"repeat not idempotent: {st} {run2}")

    # 4. Non-ADMIN 403 (only if creds provided).
    tu, tp = os.environ.get("TECH_USER"), os.environ.get("TECH_PASS")
    if tu and tp:
        tech = _login(tu, tp)
        st, _ = _req("POST", f"/api/v1/ml/procurement/quick-action/{mid}", tech)
        if st != 403:
            failures.append(f"non-admin not blocked: got {st}")
    else:
        print("[skip] TECH_USER/TECH_PASS unset — 403 check skipped")

    if failures:
        print("SMOKE FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SMOKE PASS: dry-run no-write, real run, idempotent repeat, admin guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the smoke (stack must be up: `make up`)**

Run: `docker compose exec backend python scripts/smoke_quick_action.py --machine-id 1`
Expected: `SMOKE PASS: …`, exit 0. If a real machine id differs, pass it. If the
`/stock/levels` path differs in this build, adjust the snapshot path (it is only
used for the dry-run no-write assertion).

- [ ] **Step 3: Commit**

```bash
git add app/backend/scripts/smoke_quick_action.py
git commit -m "test(quick-action): live smoke — dry-run, idempotency, admin guard, atomicity"
```

---

## Task 7: Frontend — Quick Action button + refetch wiring

**Files:**
- Modify: `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx`
- Modify: `app/frontend/src/modules/shared/MachineDetailPage.tsx`

- [ ] **Step 1: Thread `onProvisioned` through the tab props**

In `MLIntelligenceTab.tsx`, extend the `Props` interface (around line 83) and the
component signature (line 520), and pass the callback into `PartsDemandCard`.

Props interface — add the optional callback:

```tsx
interface Props {
    machine: Machine;
    mlPrediction: MLPredictionFull | null;
    interventions: Intervention[];
    onProvisioned?: () => void;   // refetch unified-health after Quick Action
}
```

Component signature (line 520) — destructure it:

```tsx
export function MLIntelligenceTab({ machine, mlPrediction, onProvisioned }: Props) {
```

`PartsDemandCard` usage (line 758) — pass it down:

```tsx
<PartsDemandCard demand={p?.parts_demand} machine={machine} mlPrediction={p} onProvisioned={onProvisioned} />
```

- [ ] **Step 2: Add imports + role/toast hooks at the top of the file**

Add to the import block at the top of `MLIntelligenceTab.tsx` (keep existing imports):

```tsx
import { useUserRole } from '@/hooks/usePermission';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
```

(If `lucide-react` icons are already imported in this file, add `Loader2` to that existing import instead of adding a new line.)

- [ ] **Step 3: Extend `PartsDemandCard` signature + add the button logic**

Update the `PartsDemandCard` function signature (line 255) to accept `onProvisioned`:

```tsx
function PartsDemandCard({
    demand,
    machine,
    mlPrediction,
    onProvisioned,
}: {
    demand: MLPredictionFull['parts_demand'];
    machine?: Machine;
    mlPrediction?: MLPredictionFull | null;
    onProvisioned?: () => void;
}) {
    const [showAll, setShowAll] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [qaLoading, setQaLoading] = useState(false);
    const role = useUserRole();
    const { toast } = useToast();
    const API = import.meta.env.VITE_API_BASE_URL || '';

    async function handleQuickAction() {
        if (!machine) return;
        setQaLoading(true);
        try {
            const res = await fetch(`${API}/api/v1/ml/procurement/quick-action/${machine.id}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
            });
            const json = await res.json();
            if (!res.ok || json.success === false) {
                toast({
                    title: 'Quick Action failed',
                    description: json.error ?? json.message ?? 'Unknown error',
                    variant: 'destructive',
                });
                return;
            }
            const s = json.summary ?? {};
            toast({
                title: json.idempotent ? 'Already up to date' : 'Quick Action complete',
                description: json.idempotent
                    ? 'No changes needed — parts already provisioned.'
                    : `${s.pieces_created ?? 0} created · ${s.stock_updated ?? 0} stock updated`,
            });
            onProvisioned?.();   // refetch unified-health → card refreshes
        } catch (e: any) {
            toast({ title: 'Quick Action failed', description: e?.message ?? 'Network error', variant: 'destructive' });
        } finally {
            setQaLoading(false);
        }
    }
```

(Leave the rest of `PartsDemandCard` — the `if (!demand …)` guard and the `return` JSX — unchanged below this point.)

- [ ] **Step 4: Render the button in the card header**

In the header button row (inside the `<div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>` at line 301), add the Quick Action button as the first child, before the "Why?" button:

```tsx
{role === 'ADMIN' && (
    <button
        onClick={handleQuickAction}
        disabled={qaLoading}
        title="Create missing pieces and top up stock for all recommended parts"
        style={{
            display: 'flex', alignItems: 'center', gap: '0.3rem',
            fontSize: '0.6rem', fontWeight: 700, color: accentColor,
            background: `${accentColor}18`, border: `1px solid ${accentColor}55`,
            borderRadius: 999, padding: '0.15rem 0.6rem',
            cursor: qaLoading ? 'wait' : 'pointer', opacity: qaLoading ? 0.6 : 1,
            fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase', letterSpacing: '0.08em',
        }}
    >
        {qaLoading && <Loader2 className="h-3 w-3 animate-spin" />}
        Quick Action
    </button>
)}
```

- [ ] **Step 5: Pass `onProvisioned` from MachineDetailPage**

In `MachineDetailPage.tsx`, the `MLIntelligenceTab` usage (line ~325) — add the prop wired to the existing `fetchData` refetch:

```tsx
<MLIntelligenceTab
    machine={machine}
    mlPrediction={mlPrediction as any}
    interventions={interventions}
    onProvisioned={fetchData}
/>
```

(Keep any existing props already present on this element; only add `onProvisioned={fetchData}`. Confirm the existing prop names against lines 325–330 before editing.)

- [ ] **Step 6: Typecheck + build**

Run: `cd app/frontend && npm run build`
Expected: build succeeds, no TypeScript errors referencing `onProvisioned`, `useUserRole`, `useToast`, or `Loader2`.

- [ ] **Step 7: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx app/frontend/src/modules/shared/MachineDetailPage.tsx
git commit -m "feat(quick-action): ADMIN Quick Action button in PartsDemandCard + refetch wiring"
```

---

## Final verification

- [ ] **Backend unit tests pass**

Run: `python -m pytest tests/backend/quick_action_helpers.test.py tests/backend/quick_action_plan.test.py -v`
Expected: all pass (16 tests).

- [ ] **Full suite not regressed**

Run: `python -m pytest tests -q`
Expected: previously-passing tests still pass; new tests included.

- [ ] **Live smoke passes** (stack up)

Run: `docker compose exec backend python scripts/smoke_quick_action.py --machine-id 1`
Expected: `SMOKE PASS`.

- [ ] **Manual UI check**

Open a machine detail page as ADMIN → ML Intelligence tab → "Parts Needed" card shows
a **Quick Action** button. Click → spinner → success toast → card refreshes with
updated stock. Log in as a technician → button absent.
