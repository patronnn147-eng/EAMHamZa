"""Unit tests for the newly extracted helpers in
app/backend/services/inventory/reservation.py (InventoryReservationService)."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401
from services.inventory.reservation import InventoryReservationService


class FakeDb:
    def __init__(self, scalar_results=None):
        self._scalar_results = list(scalar_results or [])
        self.added = []

    async def scalar(self, *_a, **_k):
        return self._scalar_results.pop(0)

    def add(self, obj):
        self.added.append(obj)


# ── _compute_deficits ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_deficits_no_deficit_when_stock_sufficient():
    db = FakeDb()
    svc = InventoryReservationService(db)
    wanted = {1: Decimal("5")}
    avail_map = {1: {"available": Decimal("10")}}
    deficits = await svc._compute_deficits(wanted, avail_map)
    assert deficits == []


@pytest.mark.asyncio
async def test_compute_deficits_reports_shortfall():
    db = FakeDb(scalar_results=["Bolt M6"])
    svc = InventoryReservationService(db)
    wanted = {1: Decimal("10")}
    avail_map = {1: {"available": Decimal("3")}}
    deficits = await svc._compute_deficits(wanted, avail_map)
    assert len(deficits) == 1
    d = deficits[0]
    assert d.piece_id == 1
    assert d.piece_name == "Bolt M6"
    assert d.requested == Decimal("10")
    assert d.available == Decimal("3")
    assert d.deficit == Decimal("7")


@pytest.mark.asyncio
async def test_compute_deficits_falls_back_to_placeholder_name_when_piece_missing():
    db = FakeDb(scalar_results=[None])
    svc = InventoryReservationService(db)
    wanted = {99: Decimal("5")}
    avail_map = {}
    deficits = await svc._compute_deficits(wanted, avail_map)
    assert deficits[0].piece_name == "piece-99"


@pytest.mark.asyncio
async def test_compute_deficits_treats_missing_avail_entry_as_zero():
    db = FakeDb(scalar_results=["Nut"])
    svc = InventoryReservationService(db)
    wanted = {5: Decimal("1")}
    deficits = await svc._compute_deficits(wanted, avail_map={})
    assert deficits[0].available == Decimal("0")
    assert deficits[0].deficit == Decimal("1")


@pytest.mark.asyncio
async def test_compute_deficits_multiple_pieces_only_flags_short_ones():
    db = FakeDb(scalar_results=["Short part"])
    svc = InventoryReservationService(db)
    wanted = {1: Decimal("2"), 2: Decimal("20")}
    avail_map = {1: {"available": Decimal("5")}, 2: {"available": Decimal("1")}}
    deficits = await svc._compute_deficits(wanted, avail_map)
    assert len(deficits) == 1
    assert deficits[0].piece_id == 2


# ── _mark_rows_reserved ───────────────────────────────────────────────────────

def _required_piece(piece_id=1, quantity_planned="4.0", unit="pcs"):
    return SimpleNamespace(
        piece_id=piece_id, quantity_planned=quantity_planned, unit=unit,
        quantity_reserved=None, reservation_expires_at=None, approved=False,
    )


def test_mark_rows_reserved_sets_row_fields_and_logs_movement():
    db = FakeDb()
    svc = InventoryReservationService(db)
    row = _required_piece(piece_id=7, quantity_planned="3.5")
    expires_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    svc._mark_rows_reserved([row], expires_at, intervention_id=42)

    assert row.quantity_reserved == Decimal("3.5")
    assert row.reservation_expires_at == expires_at
    assert row.approved is True
    assert len(db.added) == 1
    movement = db.added[0]
    assert movement.piece_id == 7
    assert movement.quantity == Decimal("3.5")
    assert movement.movement_type == "RESERVED"
    assert movement.reference == "OT-itv-42"
    assert movement.intervention_id == 42


def test_mark_rows_reserved_handles_multiple_rows():
    db = FakeDb()
    svc = InventoryReservationService(db)
    rows = [_required_piece(piece_id=1), _required_piece(piece_id=2)]
    svc._mark_rows_reserved(rows, datetime.now(timezone.utc), intervention_id=1)
    assert len(db.added) == 2
    assert all(r.approved is True for r in rows)


def test_mark_rows_reserved_empty_list_is_noop():
    db = FakeDb()
    svc = InventoryReservationService(db)
    svc._mark_rows_reserved([], datetime.now(timezone.utc), intervention_id=1)
    assert db.added == []
