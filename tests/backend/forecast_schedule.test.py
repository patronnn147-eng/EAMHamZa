import pytest
from modules.ml.services.schedule_optimizer import optimize_schedule, _greedy_schedule


WOS = [
    {"id": 1, "priority": 5, "estimated_hours": 8.0, "parts_ready": True},
    {"id": 2, "priority": 3, "estimated_hours": 4.0, "parts_ready": True},
    {"id": 3, "priority": 1, "estimated_hours": 2.0, "parts_ready": False},
]
TECH_IDS = [101, 102]


def test_greedy_assigns_all_wos():
    result = _greedy_schedule(WOS, TECH_IDS, 30)
    assert len(result["assignments"]) == len(WOS)


def test_greedy_each_wo_has_required_fields():
    result = _greedy_schedule(WOS, TECH_IDS, 30)
    for a in result["assignments"]:
        assert "wo_id" in a
        assert "technician_id" in a
        assert "start_day" in a
        assert "end_day" in a
        assert a["end_day"] >= a["start_day"]


def test_greedy_parts_not_ready_deferred():
    result = _greedy_schedule(WOS, TECH_IDS, 30)
    deferred = next(a for a in result["assignments"] if a["wo_id"] == 3)
    assert deferred["start_day"] >= 3  # parts_ready=False → min 3-day defer


def test_greedy_fallback_flag():
    result = _greedy_schedule(WOS, TECH_IDS, 30)
    assert result["fallback"] is True
    assert result["solved"] is True


def test_greedy_empty_wos():
    result = _greedy_schedule([], TECH_IDS, 30)
    assert result["assignments"] == []


def test_greedy_empty_technicians():
    result = _greedy_schedule(WOS, [], 30)
    assert result["assignments"] == []


# --- OR-Tools path (skip if not installed) ---

def test_ortools_path_returns_valid_structure():
    pytest.importorskip("ortools", reason="ortools not installed — skipping CP-SAT path")
    result = optimize_schedule(WOS, TECH_IDS, horizon_days=30)
    assert "assignments" in result
    assert "solved" in result
    assert "fallback" in result
    assert isinstance(result["assignments"], list)


def test_ortools_high_priority_scheduled_earlier():
    pytest.importorskip("ortools", reason="ortools not installed — skipping CP-SAT path")
    result = optimize_schedule(WOS, TECH_IDS, horizon_days=30)
    if result["solved"] and not result["fallback"]:
        p5 = next((a for a in result["assignments"] if a["wo_id"] == 1), None)
        p1 = next((a for a in result["assignments"] if a["wo_id"] == 3), None)
        if p5 and p1:
            assert p5["start_day"] <= p1["start_day"]
