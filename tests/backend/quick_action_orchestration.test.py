"""Unit tests for the DB-touching orchestration functions in
app/backend/modules/ml/services/quick_action.py: _preload_maps,
_apply_plan_ops, and quick_provision_parts. See quick_action_helpers.test.py
and quick_action_plan.test.py for the already-covered pure helpers."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.pieces import Piece
import modules.ml.services.quick_action as qa_mod
from modules.ml.services.quick_action import (
    _apply_plan_ops,
    _preload_maps,
    quick_provision_parts,
)


class FakeExecuteResult:
    def __init__(self, scalars_list=None, rows=None):
        self._scalars_list = scalars_list or []
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list

    def fetchall(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results=None, scalars=None):
        self._results = list(execute_results or [])
        self._scalars = list(scalars or [])
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self.flushed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    async def flush(self):
        self.flushed += 1

    def add(self, obj):
        self.added.append(obj)
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = 999  # simulate DB-assigned PK after flush


# ── _preload_maps ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_preload_maps_empty_items_skips_queries():
    db = FakeDb()
    pid_map, ref_map, lname_map, stock_map = await _preload_maps(db, [])
    assert pid_map == {} and ref_map == {} and lname_map == {} and stock_map == {}


@pytest.mark.asyncio
async def test_preload_maps_indexes_pieces_and_stock():
    piece = SimpleNamespace(
        id=1, reference="REF-1", name="Belt", min_stock=2.0,
        is_consumable=True, default_unit="pcs",
    )
    db = FakeDb(execute_results=[
        FakeExecuteResult(scalars_list=[piece]),
        FakeExecuteResult(rows=[(1, 5.0)]),
    ])
    items = [{"piece_id": 1, "reference": "REF-1", "name": "Belt"}]
    pid_map, ref_map, lname_map, stock_map = await _preload_maps(db, items)
    assert pid_map[1]["name"] == "Belt"
    assert ref_map["REF-1"] is pid_map[1]
    assert lname_map["belt"] is pid_map[1]
    assert stock_map[1] == 5.0


@pytest.mark.asyncio
async def test_preload_maps_no_stock_when_no_pieces_found():
    db = FakeDb(execute_results=[FakeExecuteResult(scalars_list=[])])
    items = [{"piece_id": 999}]
    pid_map, ref_map, lname_map, stock_map = await _preload_maps(db, items)
    assert stock_map == {}


# ── _apply_plan_ops ──────────────────────────────────────────────────────────

class FakeStockService:
    def __init__(self, db):
        self.db = db
        self.add_stock_calls = []

    async def add_stock(self, **kwargs):
        self.add_stock_calls.append(kwargs)


@pytest.mark.asyncio
async def test_apply_plan_ops_creates_new_piece_and_adds_stock():
    db = FakeDb(scalars=[None])  # no existing piece with that reference
    ops = [{
        "resolution": "create",
        "create_spec": {
            "reference": "REF-NEW", "name": "New Part", "category": "misc",
            "min_stock": 1.0, "default_unit": "pcs", "is_consumable": True,
        },
        "stock_action": "added", "qty_added": 3.0, "piece_id": None,
    }]
    await _apply_plan_ops(db, ops, Piece, FakeStockService)
    assert len(db.added) == 1
    assert ops[0]["piece_id"] == 999  # simulated DB-assigned id
    assert db.flushed == 1


@pytest.mark.asyncio
async def test_apply_plan_ops_reuses_existing_piece_by_reference():
    existing = Piece(id=42, reference="REF-EXIST", name="Existing", is_consumable=True, default_unit="pcs")
    db = FakeDb(scalars=[existing])
    ops = [{
        "resolution": "create",
        "create_spec": {
            "reference": "REF-EXIST", "name": "Existing Part", "category": "misc",
            "min_stock": 1.0, "default_unit": "pcs", "is_consumable": True,
        },
        "stock_action": "none", "qty_added": 0, "piece_id": None,
    }]
    await _apply_plan_ops(db, ops, Piece, FakeStockService)
    assert ops[0]["piece_id"] == 42
    assert len(db.added) == 0  # no new piece created


@pytest.mark.asyncio
async def test_apply_plan_ops_skips_stock_add_when_no_qty():
    db = FakeDb()
    ops = [{
        "resolution": "found", "stock_action": "none", "qty_added": 0, "piece_id": 5,
    }]
    await _apply_plan_ops(db, ops, Piece, FakeStockService)
    assert db.added == []  # no create branch touched


@pytest.mark.asyncio
async def test_apply_plan_ops_adds_stock_for_found_piece(monkeypatch):
    calls = []

    class _TrackedStockService(FakeStockService):
        async def add_stock(self, **kwargs):
            calls.append(kwargs)

    db = FakeDb()
    ops = [{
        "resolution": "found", "stock_action": "added", "qty_added": 4.0, "piece_id": 7,
    }]
    await _apply_plan_ops(db, ops, Piece, _TrackedStockService)
    assert calls[0]["piece_id"] == 7
    assert calls[0]["quantity"] == 4.0


# ── quick_provision_parts ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_provision_parts_no_items_returns_message():
    db = FakeDb()
    result = await quick_provision_parts(machine_id=1, actor_user_id=1, db=db, parts_demand={"items": []})
    assert result["success"] is False
    assert "No recommended parts" in result["message"]


class _MachineNotFoundResult:
    def scalar_one_or_none(self):
        return None


@pytest.mark.asyncio
async def test_quick_provision_parts_machine_not_found():
    db = FakeDb(execute_results=[_MachineNotFoundResult()])
    parts_demand = {"items": [{"piece_id": 1, "name": "Belt", "expected_qty": 2, "on_hand": 0, "driver": "condition"}]}
    result = await quick_provision_parts(machine_id=99, actor_user_id=1, db=db, parts_demand=parts_demand)
    assert result["success"] is False
    assert "not found" in result["error"]
    assert db.rolled_back == 1


@pytest.mark.asyncio
async def test_quick_provision_parts_idempotent_replay(monkeypatch):
    import json as _json

    class _MachineFoundResult:
        def scalar_one_or_none(self):
            return 1

    class _PriorRunResult:
        def scalar_one_or_none(self):
            return _json.dumps({"success": True, "machine_id": 1, "summary": {}})

    db = FakeDb(execute_results=[_MachineFoundResult(), _PriorRunResult()])
    parts_demand = {"items": [{"piece_id": 1, "name": "Belt", "expected_qty": 2, "on_hand": 0, "driver": "condition"}]}
    result = await quick_provision_parts(machine_id=1, actor_user_id=1, db=db, parts_demand=parts_demand)
    assert result["idempotent"] is True
    assert db.rolled_back == 1


@pytest.mark.asyncio
async def test_quick_provision_parts_dry_run_rolls_back_no_commit(monkeypatch):
    class _MachineFoundResult:
        def scalar_one_or_none(self):
            return 1

    class _NoPriorRunResult:
        def scalar_one_or_none(self):
            return None

    db = FakeDb(execute_results=[
        _MachineFoundResult(), _NoPriorRunResult(),
        FakeExecuteResult(scalars_list=[]),  # _preload_maps pieces query (empty since no piece_id conds match... )
    ])
    monkeypatch.setattr(qa_mod, "_preload_maps", AsyncMock(return_value=({}, {}, {}, {})))
    monkeypatch.setattr(qa_mod, "_apply_plan_ops", AsyncMock())
    parts_demand = {"items": [{"piece_id": 1, "name": "Belt", "expected_qty": 2, "on_hand": 0, "driver": "condition"}]}
    result = await quick_provision_parts(machine_id=1, actor_user_id=1, db=db, parts_demand=parts_demand, dry_run=True)
    assert result["success"] is True
    assert result["dry_run"] is True
    assert db.committed == 0
    assert db.rolled_back == 1  # dry-run rollback


@pytest.mark.asyncio
async def test_quick_provision_parts_success_commits_and_records_run(monkeypatch):
    class _MachineFoundResult:
        def scalar_one_or_none(self):
            return 1

    class _NoPriorRunResult:
        def scalar_one_or_none(self):
            return None

    db = FakeDb(execute_results=[_MachineFoundResult(), _NoPriorRunResult()])
    monkeypatch.setattr(qa_mod, "_preload_maps", AsyncMock(return_value=({}, {}, {}, {})))
    monkeypatch.setattr(qa_mod, "_apply_plan_ops", AsyncMock())
    parts_demand = {"items": [{"piece_id": 1, "name": "Belt", "expected_qty": 2, "on_hand": 0, "driver": "condition"}]}
    result = await quick_provision_parts(machine_id=1, actor_user_id=1, db=db, parts_demand=parts_demand, dry_run=False)
    assert result["success"] is True
    assert db.committed == 1
    assert len(db.added) == 1  # QuickActionRun recorded


@pytest.mark.asyncio
async def test_quick_provision_parts_swallows_exception():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    db = _RaisingDb()
    parts_demand = {"items": [{"piece_id": 1, "name": "Belt", "expected_qty": 2, "on_hand": 0, "driver": "condition"}]}
    result = await quick_provision_parts(machine_id=1, actor_user_id=1, db=db, parts_demand=parts_demand)
    assert result["success"] is False
    assert "db down" in result["error"]
