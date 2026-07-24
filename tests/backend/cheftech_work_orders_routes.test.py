"""Unit tests for app/backend/modules/cheftech/cheftech_work_orders.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.utilisateurs import UserRole
from modules.cheftech.cheftech_work_orders import (
    _build_export_flat_row,
    _build_wo_row,
    _calc_duration,
    _fetch_consumed_summary,
    _itv_attr,
    _require_cheftech,
    export_cheftech_work_order_report,
    list_cheftech_work_orders,
)


def _cheftech_user():
    return SimpleNamespace(role=UserRole.CHEFTECH)


def _admin_user():
    return SimpleNamespace(role=UserRole.ADMIN)


def _other_user():
    return SimpleNamespace(role=UserRole.TECHNICIEN)


# ── _require_cheftech ────────────────────────────────────────────────────────

def test_require_cheftech_allows_cheftech():
    _require_cheftech(_cheftech_user())  # no raise


def test_require_cheftech_allows_admin():
    _require_cheftech(_admin_user())  # no raise


def test_require_cheftech_rejects_other_roles():
    with pytest.raises(HTTPException) as exc_info:
        _require_cheftech(_other_user())
    assert exc_info.value.status_code == 403


# ── _itv_attr ────────────────────────────────────────────────────────────────

def test_itv_attr_returns_default_when_itv_none():
    assert _itv_attr(None, "technician_id", "fallback") == "fallback"


def test_itv_attr_returns_attribute_value():
    itv = SimpleNamespace(technician_id=7)
    assert _itv_attr(itv, "technician_id") == 7


# ── _calc_duration ───────────────────────────────────────────────────────────

def test_calc_duration_completed_wo():
    debut = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    fin = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    wo = SimpleNamespace(date_debut=debut, date_fin=fin)
    duration, live = _calc_duration(wo, datetime.now(timezone.utc))
    assert duration == 30
    assert live is None


def test_calc_duration_in_progress_wo():
    # Regression: `now` (tz-aware, from datetime.now(timezone.utc)) minus a
    # tz-aware date_debut used to crash with "can't subtract offset-naive
    # and offset-aware datetimes" because only date_debut was stripped of
    # tzinfo. Every in-progress WO hit this path, 500ing the whole listing.
    debut = datetime.now(timezone.utc) - timedelta(minutes=10)
    wo = SimpleNamespace(date_debut=debut, date_fin=None)
    duration, live = _calc_duration(wo, datetime.now(timezone.utc))
    assert duration is None
    assert live is not None and live >= 0


def test_calc_duration_in_progress_wo_naive_date_debut():
    # DB-sourced date_debut typically comes back naive (no tzinfo).
    debut = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    wo = SimpleNamespace(date_debut=debut, date_fin=None)
    duration, live = _calc_duration(wo, datetime.now(timezone.utc))
    assert duration is None
    assert live is not None and live >= 0


def test_calc_duration_not_started_wo():
    wo = SimpleNamespace(date_debut=None, date_fin=None)
    duration, live = _calc_duration(wo, datetime.now(timezone.utc))
    assert duration is None
    assert live is None


# ── _build_wo_row ─────────────────────────────────────────────────────────────

def test_build_wo_row_with_intervention():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="EN_COURS", priorite="HAUTE",
        created_at=now, date_debut=now, date_fin=None, rapport=None,
    )
    itv = SimpleNamespace(
        id=5, technician_id=3, intervention_type="CORRECTIVE",
        machine_status_after=None, plan_hypothesis=None, root_cause_category=None,
        root_cause_description=None, actions_performed=None, legacy_parts_text=None,
        tools_used=None, check_resolved=None, check_verification_method=None,
        act_preventive_actions=None, act_recommendations=None,
    )
    row = _build_wo_row(wo, "Press-1", "Bob", "bob@x.com", itv, now)
    assert row["machine_nom"] == "Press-1"
    assert row["technicien_id"] == 3
    assert row["intervention_id"] == 5


def test_build_wo_row_without_intervention_uses_na_defaults():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="ASSIGNÉ", priorite="BASSE",
        created_at=None, date_debut=None, date_fin=None, rapport=None,
    )
    row = _build_wo_row(wo, None, None, None, None, now)
    assert row["machine_nom"] == "N/A"
    assert row["technicien_nom"] == "N/A"
    assert row["technicien_id"] is None
    assert row["created_at"] is None


# ── _fetch_consumed_summary ────────────────────────────────────────────────────

class FakeFirstResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_fetch_consumed_summary_none_intervention():
    assert await _fetch_consumed_summary(FakeDb(), None) is None


@pytest.mark.asyncio
async def test_fetch_consumed_summary_no_row():
    db = FakeDb([FakeFirstResult(None)])
    itv = SimpleNamespace(id=1)
    assert await _fetch_consumed_summary(db, itv) is None


@pytest.mark.asyncio
async def test_fetch_consumed_summary_formats_parts():
    import json
    data = json.dumps([
        {"piece_name": "Belt", "used": "2", "unit": "pcs", "returned": "0", "wasted": "1"},
    ])
    db = FakeDb([FakeFirstResult((data,))])
    itv = SimpleNamespace(id=1)
    result = await _fetch_consumed_summary(db, itv)
    assert "Belt" in result
    assert "rebut=1" in result


@pytest.mark.asyncio
async def test_fetch_consumed_summary_swallows_query_failure():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("view missing")

    itv = SimpleNamespace(id=1)
    assert await _fetch_consumed_summary(_RaisingDb(), itv) is None


# ── _build_export_flat_row ─────────────────────────────────────────────────────

def test_build_export_flat_row_with_intervention():
    now = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="TERMINÉ", priorite="HAUTE",
        created_at=now, date_debut=now, date_fin=now, rapport="Done",
    )
    itv = SimpleNamespace(
        id=5, priority="HAUTE", symptoms="noise", impact="low", frequency="daily",
        risk_score=0.5, intervention_type="CORRECTIVE", machine_status_after="OK",
        plan_hypothesis="worn belt", root_cause_category="MECH", root_cause_description="belt",
        actions_performed="replaced", legacy_parts_text="belt x1", tools_used="wrench",
        check_resolved=True, check_verification_method="visual",
        act_preventive_actions="inspect monthly", act_recommendations="none",
    )
    row = _build_export_flat_row(wo, "Press-1", "Bob", "bob@x.com", itv, None, 30)
    assert row["ID Intervention"] == 5
    assert row["CHECK - Problème Résolu?"] == "OUI"
    assert row["DO - Pièces Remplacées"] == "belt x1"


def test_build_export_flat_row_prefers_consumed_summary_over_legacy_text():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="TERMINÉ", priorite="HAUTE",
        created_at=now, date_debut=now, date_fin=now, rapport="Done",
    )
    itv = SimpleNamespace(
        id=5, priority=None, symptoms=None, impact=None, frequency=None, risk_score=None,
        intervention_type=None, machine_status_after=None, plan_hypothesis=None,
        root_cause_category=None, root_cause_description=None, actions_performed=None,
        legacy_parts_text="fallback text", tools_used=None, check_resolved=False,
        check_verification_method=None, act_preventive_actions=None, act_recommendations=None,
    )
    row = _build_export_flat_row(wo, None, None, None, itv, "Belt (2pcs)", 30)
    assert row["DO - Pièces Remplacées"] == "Belt (2pcs)"
    assert row["CHECK - Problème Résolu?"] == "NON"


def test_build_export_flat_row_without_intervention():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="ASSIGNÉ", priorite="BASSE",
        created_at=None, date_debut=None, date_fin=None, rapport=None,
    )
    row = _build_export_flat_row(wo, None, None, None, None, None, "N/A")
    assert row["ID Intervention"] == "N/A"
    assert row["Date Création"] == "N/A"


# ── list_cheftech_work_orders ───────────────────────────────────────────────────

class FakeQueryResult:
    def __init__(self, scalar_value=None, all_rows=None):
        self._scalar_value = scalar_value
        self._all_rows = all_rows or []

    def scalar(self):
        return self._scalar_value

    def all(self):
        return self._all_rows


@pytest.mark.asyncio
async def test_list_cheftech_work_orders_non_cheftech_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await list_cheftech_work_orders(page=1, size=10, current_user=_other_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_list_cheftech_work_orders_empty():
    db = FakeDb([FakeQueryResult(scalar_value=0), FakeQueryResult(all_rows=[])])
    result = await list_cheftech_work_orders(page=1, size=10, current_user=_cheftech_user(), db=db)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_cheftech_work_orders_maps_rows():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="EN_COURS", priorite="HAUTE",
        created_at=now, date_debut=now, date_fin=None, rapport=None,
    )
    db = FakeDb([
        FakeQueryResult(scalar_value=1),
        FakeQueryResult(all_rows=[(wo, "Press-1", "Bob", "bob@x.com", None)]),
    ])
    result = await list_cheftech_work_orders(page=1, size=10, current_user=_cheftech_user(), db=db)
    assert result.total == 1
    assert result.items[0]["machine_nom"] == "Press-1"


@pytest.mark.asyncio
async def test_list_cheftech_work_orders_exception_raises_500():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await list_cheftech_work_orders(page=1, size=10, current_user=_cheftech_user(), db=_RaisingDb())
    assert exc_info.value.status_code == 500


# ── export_cheftech_work_order_report ───────────────────────────────────────────

class FakeFirstRowResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_export_report_non_cheftech_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await export_cheftech_work_order_report(order_id=1, current_user=_other_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_export_report_not_found():
    db = FakeDb([FakeFirstRowResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await export_cheftech_work_order_report(order_id=99, current_user=_cheftech_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_export_report_success_returns_xlsx_stream():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = SimpleNamespace(
        id=1, titre="Fix pump", statut="TERMINÉ", priorite="HAUTE",
        created_at=now, date_debut=now, date_fin=now, rapport="Done",
    )
    db = FakeDb([
        FakeFirstRowResult((wo, "Press-1", "Bob", "bob@x.com", None)),
        FakeFirstResult(None),  # _fetch_consumed_summary's own execute call
    ])
    result = await export_cheftech_work_order_report(order_id=1, current_user=_cheftech_user(), db=db)
    assert isinstance(result, StreamingResponse)
    assert "attachment" in result.headers["Content-Disposition"]


@pytest.mark.asyncio
async def test_export_report_unexpected_exception_raises_500():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await export_cheftech_work_order_report(order_id=1, current_user=_cheftech_user(), db=_RaisingDb())
    assert exc_info.value.status_code == 500
