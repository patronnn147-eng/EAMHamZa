"""Unit tests for app/backend/modules/admin/admin_work_orders.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.utilisateurs import UserRole
from modules.admin.admin_work_orders import (
    _build_admin_export_flat_row,
    _fetch_consumed_summary,
    export_work_order_report,
    list_work_orders,
)


def _admin_user():
    return SimpleNamespace(role=UserRole.ADMIN)


def _non_admin_user():
    return SimpleNamespace(role=UserRole.TECHNICIEN)


class FakeQueryResult:
    def __init__(self, scalar_value=None, all_rows=None, first_row=None):
        self._scalar_value = scalar_value
        self._all_rows = all_rows or []
        self._first_row = first_row

    def scalar(self):
        return self._scalar_value

    def all(self):
        return self._all_rows

    def first(self):
        return self._first_row


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _wo(id=1, statut="ASSIGNÉ", date_debut=None, date_fin=None):
    return SimpleNamespace(
        id=id, titre="WO1", description="desc", priorite="HAUTE", statut=statut,
        machine_id=5, utilisateur_id=2, created_at=None, date_debut=date_debut,
        date_fin=date_fin, rapport=None,
    )


# ── list_work_orders ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_work_orders_non_admin_raises_403():
    # Regression: the role check lives inside the try block with no
    # `except HTTPException: raise` guard before the generic `except
    # Exception` — the deliberate 403 was always getting rewrapped into a
    # 500 (same bug family as commits 0015af8/d65fba5/fcbabb5/1533fb4).
    with pytest.raises(HTTPException) as exc_info:
        await list_work_orders(page=1, size=10, current_user=_non_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_list_work_orders_empty():
    db = FakeDb([FakeQueryResult(scalar_value=0), FakeQueryResult(all_rows=[])])
    result = await list_work_orders(page=1, size=10, current_user=_admin_user(), db=db)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_work_orders_computes_duration_for_completed_wo():
    debut = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    fin = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    wo = _wo(date_debut=debut, date_fin=fin)
    db = FakeDb([
        FakeQueryResult(scalar_value=1),
        FakeQueryResult(all_rows=[(wo, "Press-1", "Bob", "bob@x.com", 7)]),
    ])
    result = await list_work_orders(page=1, size=10, current_user=_admin_user(), db=db)
    assert result.items[0]["duration_minutes"] == 30
    assert result.items[0]["machine_nom"] == "Press-1"


@pytest.mark.asyncio
async def test_list_work_orders_computes_live_duration_for_in_progress_wo():
    debut = datetime.now(timezone.utc) - timedelta(minutes=15)
    wo = _wo(statut="EN_COURS", date_debut=debut, date_fin=None)
    db = FakeDb([
        FakeQueryResult(scalar_value=1),
        FakeQueryResult(all_rows=[(wo, None, None, None, None)]),
    ])
    result = await list_work_orders(page=1, size=10, current_user=_admin_user(), db=db)
    assert result.items[0]["duration_minutes"] >= 14
    assert result.items[0]["machine_nom"] == "N/A"


@pytest.mark.asyncio
async def test_list_work_orders_exception_raises_500():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await list_work_orders(page=1, size=10, current_user=_admin_user(), db=_RaisingDb())
    assert exc_info.value.status_code == 500


# ── _fetch_consumed_summary ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_consumed_summary_none_intervention():
    assert await _fetch_consumed_summary(FakeDb(), None) is None


@pytest.mark.asyncio
async def test_fetch_consumed_summary_no_row():
    db = FakeDb([FakeQueryResult(first_row=None)])
    itv = SimpleNamespace(id=1)
    assert await _fetch_consumed_summary(db, itv) is None


@pytest.mark.asyncio
async def test_fetch_consumed_summary_formats_parts():
    import json
    data = json.dumps([{"piece_name": "Belt", "used": "2", "unit": "pcs", "returned": "1", "wasted": "0"}])
    db = FakeDb([FakeQueryResult(first_row=(data,))])
    itv = SimpleNamespace(id=1)
    result = await _fetch_consumed_summary(db, itv)
    assert "Belt" in result and "retour=1" in result


@pytest.mark.asyncio
async def test_fetch_consumed_summary_swallows_failure():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("view missing")

    itv = SimpleNamespace(id=1)
    assert await _fetch_consumed_summary(_RaisingDb(), itv) is None


# ── _build_admin_export_flat_row ─────────────────────────────────────────────

def test_build_admin_export_flat_row_with_intervention():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = _wo(date_debut=now, date_fin=now)
    wo.created_at = now
    itv = SimpleNamespace(
        id=9, priority="HAUTE", symptoms="noise", impact="low", frequency="daily",
        risk_score=0.5, intervention_type="CORRECTIVE", machine_status_after="OK",
        plan_hypothesis="worn belt", root_cause_category="MECH", root_cause_description="belt",
        actions_performed="replaced", legacy_parts_text="belt x1", tools_used="wrench",
        check_resolved=True, check_verification_method="visual",
        act_preventive_actions="inspect", act_recommendations="none",
    )
    row = _build_admin_export_flat_row(wo, "Press-1", "Bob", "bob@x.com", itv, None, 30)
    assert row["ID Intervention"] == 9
    assert row["CHECK - Problème Résolu?"] == "OUI"
    assert row["DO - Pièces Remplacées"] == "belt x1"


def test_build_admin_export_flat_row_without_intervention():
    wo = _wo()
    wo.created_at = None
    row = _build_admin_export_flat_row(wo, None, None, None, None, None, "N/A")
    assert row["ID Intervention"] == "N/A"
    assert row["Date Création"] == "N/A"


# ── export_work_order_report ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_non_admin_raises_403():
    with pytest.raises(HTTPException) as exc_info:
        await export_work_order_report(order_id=1, current_user=_non_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_export_not_found():
    db = FakeDb([FakeQueryResult(first_row=None)])
    with pytest.raises(HTTPException) as exc_info:
        await export_work_order_report(order_id=99, current_user=_admin_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_export_success_returns_xlsx_stream():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = _wo(date_debut=now, date_fin=now)
    wo.created_at = now
    db = FakeDb([
        FakeQueryResult(first_row=(wo, "Press-1", "Bob", "bob@x.com", None)),
        FakeQueryResult(first_row=None),  # _fetch_consumed_summary's own execute call
    ])
    result = await export_work_order_report(order_id=1, current_user=_admin_user(), db=db)
    assert isinstance(result, StreamingResponse)
    assert "attachment" in result.headers["Content-Disposition"]


@pytest.mark.asyncio
async def test_export_unexpected_exception_raises_500():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await export_work_order_report(order_id=1, current_user=_admin_user(), db=_RaisingDb())
    assert exc_info.value.status_code == 500
