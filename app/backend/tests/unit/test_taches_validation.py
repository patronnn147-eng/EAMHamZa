"""
Unit tests — validate_task_dates logic in planning/taches.py

Tests the pure date-range guard without hitting the database.
All cases use a mock Planning object with just the two date fields needed.
"""

import pytest
from datetime import datetime
from types import SimpleNamespace
from fastapi import HTTPException


# ── Import the function under test ────────────────────────────────────────────
# taches.py lives at modules/shared/routes/planning/taches.py
# We import it directly so tests don't need the full FastAPI app to start.
from modules.shared.routes.planning.taches import validate_task_dates


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_planning(start: str, end: str) -> SimpleNamespace:
    """Return a minimal planning-like object with date_debut / date_fin."""
    fmt = "%Y-%m-%d %H:%M"
    return SimpleNamespace(
        date_debut=datetime.strptime(start, fmt),
        date_fin=datetime.strptime(end, fmt),
    )


def dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestValidateTaskDates:
    def test_valid_task_within_planning_range(self):
        """Happy path — task fully inside planning window."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        # Should not raise
        validate_task_dates(planning, dt("2026-01-16 08:00"), dt("2026-01-18 17:00"))

    def test_task_starts_exactly_on_planning_start(self):
        """Task start == planning start is allowed."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        validate_task_dates(planning, dt("2026-01-15 08:00"), dt("2026-01-17 12:00"))

    def test_task_ends_exactly_on_planning_end(self):
        """Task end == planning end is allowed."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        validate_task_dates(planning, dt("2026-01-16 08:00"), dt("2026-01-20 18:00"))

    def test_task_spans_full_planning_window(self):
        """Task exactly matches planning window — edge case that must pass."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        validate_task_dates(planning, dt("2026-01-15 08:00"), dt("2026-01-20 18:00"))

    def test_task_starts_before_planning_raises_400(self):
        """date_debut before planning.date_debut → 400."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        with pytest.raises(HTTPException) as exc_info:
            validate_task_dates(
                planning, dt("2026-01-14 07:00"), dt("2026-01-17 12:00")
            )
        assert exc_info.value.status_code == 400
        assert "start date" in exc_info.value.detail.lower()

    def test_task_ends_after_planning_raises_400(self):
        """date_fin after planning.date_fin → 400."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        with pytest.raises(HTTPException) as exc_info:
            validate_task_dates(
                planning, dt("2026-01-16 08:00"), dt("2026-01-21 09:00")
            )
        assert exc_info.value.status_code == 400
        assert "end date" in exc_info.value.detail.lower()

    def test_task_completely_outside_planning_raises_400(self):
        """Task entirely outside window — start violation fires first."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        with pytest.raises(HTTPException) as exc_info:
            validate_task_dates(
                planning, dt("2026-01-01 08:00"), dt("2026-01-05 18:00")
            )
        assert exc_info.value.status_code == 400

    def test_task_one_minute_before_planning_start_raises_400(self):
        """Off-by-one at minute granularity."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        with pytest.raises(HTTPException) as exc_info:
            validate_task_dates(
                planning, dt("2026-01-15 07:59"), dt("2026-01-17 12:00")
            )
        assert exc_info.value.status_code == 400

    def test_task_one_minute_after_planning_end_raises_400(self):
        """Off-by-one at minute granularity on end."""
        planning = make_planning("2026-01-15 08:00", "2026-01-20 18:00")
        with pytest.raises(HTTPException) as exc_info:
            validate_task_dates(
                planning, dt("2026-01-16 08:00"), dt("2026-01-20 18:01")
            )
        assert exc_info.value.status_code == 400
