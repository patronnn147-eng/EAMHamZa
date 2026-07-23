"""Unit tests for app/backend/modules/admin/routes/analytics.py's pure
aggregation helpers and the verify_admin guard."""
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from models.utilisateurs import UserRole
from modules.admin.routes.analytics import (
    _compute_request_trends,
    _compute_tech_stats,
    verify_admin,
)


# ── verify_admin ───────────────────────────────────────────────────────────────

def test_verify_admin_allows_admin():
    user = SimpleNamespace(role=UserRole.ADMIN)
    assert verify_admin(user) is user


def test_verify_admin_rejects_non_admin():
    with pytest.raises(HTTPException) as exc_info:
        verify_admin(SimpleNamespace(role=UserRole.TECHNICIEN))
    assert exc_info.value.status_code == 403


# ── _compute_tech_stats ────────────────────────────────────────────────────────

def _wo(utilisateur_id, date_debut=None, date_fin=None):
    return SimpleNamespace(utilisateur_id=utilisateur_id, date_debut=date_debut, date_fin=date_fin)


def test_compute_tech_stats_aggregates_by_technician():
    wos = [
        _wo(1, datetime(2026, 1, 1, 8, 0), datetime(2026, 1, 1, 9, 0)),  # 60 min
        _wo(1, datetime(2026, 1, 2, 8, 0), datetime(2026, 1, 2, 8, 30)),  # 30 min
        _wo(2, datetime(2026, 1, 1, 8, 0), datetime(2026, 1, 1, 9, 0)),  # 60 min
    ]
    result = _compute_tech_stats(wos)
    tech1 = next(r for r in result if r["technician_id"] == 1)
    assert tech1["completed"] == 2
    assert tech1["avg_duration"] == 45.0


def test_compute_tech_stats_sorted_by_completed_descending():
    wos = [_wo(1), _wo(2), _wo(2), _wo(2)]
    result = _compute_tech_stats(wos)
    assert result[0]["technician_id"] == 2
    assert result[0]["completed"] == 3


def test_compute_tech_stats_unassigned_bucket():
    wos = [_wo(None)]
    result = _compute_tech_stats(wos)
    assert result[0]["technician_id"] == "Unassigned"


def test_compute_tech_stats_missing_dates_zero_duration():
    wos = [_wo(1, date_debut=None, date_fin=None)]
    result = _compute_tech_stats(wos)
    assert result[0]["avg_duration"] == 0

    result_empty = _compute_tech_stats([])
    assert result_empty == []


# ── _compute_request_trends ────────────────────────────────────────────────────

def _intervention(date_intervention, statut):
    return SimpleNamespace(date_intervention=date_intervention, statut=statut)


def test_compute_request_trends_buckets_by_day_and_status():
    ints = [
        _intervention(datetime(2026, 1, 1), "APPROUVE"),
        _intervention(datetime(2026, 1, 1), "REJETE"),
        _intervention(datetime(2026, 1, 2), "EN_ATTENTE"),
    ]
    result = _compute_request_trends(ints)
    assert result[0]["date"] == "2026-01-01"
    assert result[0]["accepted"] == 1
    assert result[0]["rejected"] == 1
    assert result[1]["date"] == "2026-01-02"
    assert result[1]["pending"] == 1


def test_compute_request_trends_skips_missing_date():
    ints = [_intervention(None, "APPROUVE")]
    assert _compute_request_trends(ints) == []


def test_compute_request_trends_ignores_unknown_status():
    ints = [_intervention(datetime(2026, 1, 1), "SOME_OTHER_STATUS")]
    result = _compute_request_trends(ints)
    assert result[0] == {"date": "2026-01-01", "accepted": 0, "rejected": 0, "pending": 0}


def test_compute_request_trends_sorted_chronologically():
    ints = [
        _intervention(datetime(2026, 1, 3), "APPROUVE"),
        _intervention(datetime(2026, 1, 1), "APPROUVE"),
    ]
    result = _compute_request_trends(ints)
    assert [r["date"] for r in result] == ["2026-01-01", "2026-01-03"]
