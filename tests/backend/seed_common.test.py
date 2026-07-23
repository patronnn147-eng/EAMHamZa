"""Unit tests for app/backend/seed_common.py — shared helpers extracted from the
seed_ml_data*.py scripts during the 2026-07 SonarQube duplication cleanup."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
import seed_common as sc


# ── Pure math/formula helpers ────────────────────────────────────────────────

def test_lerp_endpoints_and_midpoint():
    assert sc._lerp(0.0, 10.0, 0.0) == 0.0
    assert sc._lerp(0.0, 10.0, 1.0) == 10.0
    assert sc._lerp(0.0, 10.0, 0.5) == 5.0


def test_noise_uses_provided_rng():
    class FixedRng:
        def gauss(self, mu, sigma):
            return mu + sigma  # deterministic stand-in

    assert sc._noise(FixedRng(), 2.0) == 2.0


def test_failure_prob_below_threshold_is_zero():
    assert sc._failure_prob(50.0) == 0.0
    assert sc._failure_prob(99.9) == 0.0


def test_failure_prob_scales_above_threshold():
    assert sc._failure_prob(100.0) == 0.0
    assert sc._failure_prob(230.0) == pytest.approx(95.0)
    assert 0 < sc._failure_prob(165.0) < 95.0


def test_risk_level_thresholds():
    assert sc._risk_level(75) == "CRITICAL"
    assert sc._risk_level(55) == "HIGH"
    assert sc._risk_level(35) == "MEDIUM"
    assert sc._risk_level(10) == "LOW"
    assert sc._risk_level(70) == "CRITICAL"
    assert sc._risk_level(50) == "HIGH"
    assert sc._risk_level(30) == "MEDIUM"


# ── Fake async session (no real DB) ──────────────────────────────────────────

class FakeAsyncSession:
    """Minimal add/flush/commit fake — enough for the write-only helpers below,
    which never issue a SELECT of their own."""

    def __init__(self):
        self.added = []
        self._next_id = 1

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    async def commit(self):
        pass


def _person(pid):
    return SimpleNamespace(id=pid)


@pytest.mark.asyncio
async def test_create_seed_cycle_records_links_itv_to_ot():
    db = FakeAsyncSession()
    now = datetime.now(timezone.utc)
    cfg = {"failure_type": "NONE", "itv_type": "PREVENTIVE", "priority": "BASSE"}

    planning, itv, ot = await sc.create_seed_cycle_records(
        db, machine_id=7, cheftech=_person(1), chetop=_person(2), technicien=_person(3),
        cycle_num=1, c_start=now - timedelta(days=1), c_mid=now - timedelta(hours=12),
        c_end=now, itv_requested_at=now - timedelta(hours=12), cfg=cfg,
        descriptions={"diag": "d", "corr": "c", "itv_problem": "p", "ot": "o"},
    )

    assert planning.identifiant_planning == "SEED-PLAN-C01-M7"
    assert itv.actual_failure_type == "NONE"
    assert itv.ordre_travail_id == ot.id  # Step 6 link
    assert ot.id is not None


@pytest.mark.asyncio
async def test_generate_cycle_telemetry_clamps_and_counts_rows():
    db = FakeAsyncSession()
    now = datetime.now(timezone.utc)
    machine = SimpleNamespace(id=1, nom="M1")
    ot = SimpleNamespace(id=99)
    technicien = _person(3)
    cfg = {
        "tool_wear": (-500.0, 500.0),  # deliberately out-of-clamp-range
        "torque": (10.0, 20.0),
        "rpm": (1000, 1100),
        "air_temp": (295.0, 296.0),
    }

    await sc.generate_cycle_telemetry(
        db, ot, machine, technicien, cfg, rng=__import__("random").Random(1),
        cycle_num=1, telemetry_per_cycle=5, c_start=now - timedelta(hours=1), c_end=now,
        clamps={
            "wear": (0.0, 90.0), "torque": (1.0, 100.0), "rpm": (500, 3000),
            "air": (290.0, 320.0), "proc": (295.0, 330.0),
        },
        priority_fn=lambda f_prob: "P1" if f_prob > 75 else "P2",
    )

    telemetry_rows = [o for o in db.added if type(o).__name__ == "MachineTelemetry"]
    shadow_rows = [o for o in db.added if type(o).__name__ == "MlPredictionLog"]
    assert len(telemetry_rows) == 5
    assert len(shadow_rows) == 5
    assert all(0.0 <= t.tool_wear <= 90.0 for t in telemetry_rows)
    assert all(r.predicted_priority in ("P1", "P2") for r in shadow_rows)


@pytest.mark.asyncio
async def test_clean_seed_data_deletes_when_seed_rows_exist():
    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeSessionWithQueries:
        def __init__(self):
            self.executed = []

        async def execute(self, stmt):
            self.executed.append(stmt)
            # First two SELECTs (seed OT ids, seed Planning ids) return one row each;
            # every subsequent call is a DELETE (return value unused by clean_seed_data).
            if len(self.executed) == 1:
                return FakeResult([(101,)])
            if len(self.executed) == 2:
                return FakeResult([(201,)])
            return FakeResult([])

    db = FakeSessionWithQueries()
    await sc.clean_seed_data(db, machine_id=1)

    # 2 selects + 3 unconditional deletes (telemetry/log/intervention)
    # + 2 for seed_ot_ids branch + 4 for seed_plan_ids branch = 11
    assert len(db.executed) == 11


@pytest.mark.asyncio
async def test_clean_seed_data_no_seed_rows_skips_conditional_deletes():
    class FakeResult:
        def all(self):
            return []

    class FakeSessionEmpty:
        def __init__(self):
            self.call_count = 0

        async def execute(self, stmt):
            self.call_count += 1
            return FakeResult()

    db = FakeSessionEmpty()
    await sc.clean_seed_data(db, machine_id=1)

    # 2 selects (both empty) + 3 unconditional deletes = 5, no conditional deletes fire
    assert db.call_count == 5
