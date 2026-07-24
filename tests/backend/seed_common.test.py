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


def _person(pid, nom="P"):
    return SimpleNamespace(id=pid, nom=nom)


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


# ── run_seed_driver ──────────────────────────────────────────────────────────

class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class FakeDriverSession:
    """FIFO fake: each queued response is returned by the next db.execute()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.commit_count = 0

    async def execute(self, stmt):
        return self._responses.pop(0)

    async def commit(self):
        self.commit_count += 1


class FakeDbManager:
    def __init__(self, session):
        self._session = session
        self.init_db_called = False

    async def init_db(self):
        self.init_db_called = True

    def async_session_maker(self):
        session = self._session

        class _Ctx:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


def _machine(mid, nom="M"):
    return SimpleNamespace(id=mid, nom=nom)


@pytest.mark.asyncio
async def test_run_seed_driver_aborts_when_no_machines_found():
    session = FakeDriverSession([_ScalarsResult([])])
    db_manager = FakeDbManager(session)

    result = await sc.run_seed_driver(
        db_manager, num_cycles=5, clean_mode=False, machine_ids=None,
        idempotency_threshold=10, clean_seed_data_fn=None, seed_machine_fn=None,
    )

    assert result is None
    assert db_manager.init_db_called is True


@pytest.mark.asyncio
async def test_run_seed_driver_aborts_when_required_users_missing():
    session = FakeDriverSession([
        _ScalarsResult([_machine(1)]),  # machines
        _ScalarsResult([]),  # techniciens (missing)
        _ScalarsResult([_person(2)]),  # cheftechs
        _ScalarsResult([_person(3)]),  # chetops
    ])
    db_manager = FakeDbManager(session)

    result = await sc.run_seed_driver(
        db_manager, num_cycles=5, clean_mode=False, machine_ids=None,
        idempotency_threshold=10, clean_seed_data_fn=None, seed_machine_fn=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_run_seed_driver_skips_already_seeded_machine():
    session = FakeDriverSession([
        _ScalarsResult([_machine(1)]),  # machines
        _ScalarsResult([_person(10)]),  # techniciens
        _ScalarsResult([_person(20)]),  # cheftechs
        _ScalarsResult([_person(30)]),  # chetops
        _ScalarResult(50),  # existing telemetry count >= threshold
    ])
    db_manager = FakeDbManager(session)

    async def seed_machine_fn(*args, **kwargs):
        raise AssertionError("should not be called for an already-seeded machine")

    result = await sc.run_seed_driver(
        db_manager, num_cycles=5, clean_mode=False, machine_ids=None,
        idempotency_threshold=10, clean_seed_data_fn=None, seed_machine_fn=seed_machine_fn,
    )

    assert result == {}


@pytest.mark.asyncio
async def test_run_seed_driver_seeds_machine_and_builds_summary():
    session = FakeDriverSession([
        _ScalarsResult([_machine(1, "M1"), _machine(2, "M2")]),  # machines
        _ScalarsResult([_person(10)]),  # techniciens
        _ScalarsResult([_person(20)]),  # cheftechs
        _ScalarsResult([_person(30)]),  # chetops
        _ScalarResult(0),  # machine 1: existing count below threshold
        _ScalarResult(0),  # machine 2: existing count below threshold
    ])
    db_manager = FakeDbManager(session)

    seeded_machines = []

    async def seed_machine_fn(db, machine, techniciens, cheftech, chetop, num_cycles):
        seeded_machines.append(machine.id)
        return {"NONE": num_cycles}

    result = await sc.run_seed_driver(
        db_manager, num_cycles=7, clean_mode=False, machine_ids=None,
        idempotency_threshold=10, clean_seed_data_fn=None, seed_machine_fn=seed_machine_fn,
    )

    assert seeded_machines == [1, 2]
    assert result == {1: {"NONE": 7}, 2: {"NONE": 7}}
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_run_seed_driver_clean_mode_reseeds_despite_high_existing_count():
    session = FakeDriverSession([
        _ScalarsResult([_machine(1)]),  # machines
        _ScalarsResult([_person(10)]),  # techniciens
        _ScalarsResult([_person(20)]),  # cheftechs
        _ScalarsResult([_person(30)]),  # chetops
        _ScalarResult(999),  # existing count is way above threshold
    ])
    db_manager = FakeDbManager(session)

    clean_calls = []

    async def clean_seed_data_fn(db, machine_id):
        clean_calls.append(machine_id)

    seeded_machines = []

    async def seed_machine_fn(db, machine, techniciens, cheftech, chetop, num_cycles):
        seeded_machines.append(machine.id)
        return {"NONE": 1}

    result = await sc.run_seed_driver(
        db_manager, num_cycles=3, clean_mode=True, machine_ids=None,
        idempotency_threshold=10, clean_seed_data_fn=clean_seed_data_fn,
        seed_machine_fn=seed_machine_fn,
    )

    assert clean_calls == [1]
    assert seeded_machines == [1]
    assert result == {1: {"NONE": 1}}
