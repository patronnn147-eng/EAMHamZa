"""
seed_ml_data_all.py — ML Seed Data Script (ALL machines)

Same Planning → ITV (ordre_travail_id=None) → OT → ITV.ordre_travail_id = OT.id
cycle generator as seed_ml_data.py / seed_ml_data_m13.py, but loops over every
machine currently in the `machines` table instead of one hardcoded id.

Each machine gets its own degradation arc (severity randomized per machine_id,
reproducible via seeded RNG) so the fleet isn't N identical copies of the same
curve — closer to what P1-P6 retraining expects to see across machines.

Run:
    docker cp app/backend/seed_ml_data_all.py asset_management_backend:/app/seed_ml_data_all.py
    docker exec asset_management_backend python seed_ml_data_all.py
    docker exec asset_management_backend python seed_ml_data_all.py --clean
    docker exec asset_management_backend python seed_ml_data_all.py --cycles 30
"""

import argparse
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from core.database import db_manager
from models.alertes import Alert  # noqa: F401 — registers Alert mapper
from models.machine_telemetry import MachineTelemetry
from models.machines import Machines
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail
from models.planning_machines import PlanningMachines
from models.planning_ordres_travail import PlanningOrdresTravail
from models.planning_taches import PlanningTaches
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings
from seed_common import (
    _failure_prob,
    _lerp,
    _noise,
    _risk_level,
    create_seed_cycle_records,
    generate_cycle_telemetry,
    run_seed_driver,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
TELEMETRY_PER_CYCLE = 10
DAYS_SPAN_PER_CYCLE = 10  # each cycle spans ~10 days, backdated from now
IDEMPOTENCY_THRESHOLD = 15  # existing telemetry rows → assume machine already seeded


# ── Degradation curve helpers ──────────────────────────────────────────────────


def _cycle_params(cycle_idx: int, num_cycles: int, severity: float) -> dict:
    """
    Return sensor ranges and metadata for cycle_idx (0-based).
    `severity` (0.7-1.3) scales how far the arc degrades, so different
    machines land on different end states instead of an identical curve.
    """
    t = cycle_idx / max(num_cycles - 1, 1)  # 0.0 → 1.0

    tool_wear_start = _lerp(5.0, 180.0 * severity, t)
    tool_wear_end = _lerp(10.0, 230.0 * severity, t)
    torque_start = _lerp(26.0, 68.0 * severity, t)
    torque_end = _lerp(32.0, 78.0 * severity, t)
    rpm_start = int(_lerp(1620, 1080 / severity, t))
    rpm_end = int(_lerp(1580, 1050 / severity, t))
    air_start = _lerp(296.0, 309.0, t)
    air_end = _lerp(297.0, 311.0, t)

    expected_wear = tool_wear_end
    expected_rpm = rpm_end
    expected_air_end = air_end
    expected_proc_end = expected_air_end + 10.0

    if expected_wear >= 190:
        failure_type = "TWF"
        priority = "URGENTE"
        itv_type = "CORRECTIVE"
    elif expected_wear >= 155:
        failure_type = "OSF"
        priority = "URGENTE"
        itv_type = "CORRECTIVE"
    elif (expected_proc_end - expected_air_end) < 8.6 and expected_rpm < 1380:
        failure_type = "HDF"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"
    elif expected_wear >= 100:
        failure_type = "PWF"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"
    elif expected_wear >= 60:
        failure_type = "RNF"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"
    else:
        failure_type = "NONE"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"

    return {
        "tool_wear": (tool_wear_start, tool_wear_end),
        "torque": (torque_start, torque_end),
        "rpm": (rpm_start, rpm_end),
        "air_temp": (air_start, air_end),
        "failure_type": failure_type,
        "priority": priority,
        "itv_type": itv_type,
    }


# ── Cleanup ────────────────────────────────────────────────────────────────────


async def _clean_seed_data(db, machine_id: int) -> None:
    """Delete all seed data for one machine. Safe to call multiple times."""
    logger.info(f"Cleaning seed data for machine_id={machine_id}...")

    seed_ot_rows = await db.execute(
        select(OrdresTravail.id).where(
            OrdresTravail.machine_id == machine_id,
            OrdresTravail.titre.like("OT-SEED-%"),
        )
    )
    seed_ot_ids = [r[0] for r in seed_ot_rows.all()]

    seed_plan_rows = await db.execute(
        select(Plannings.id).where(
            Plannings.identifiant_planning.like(f"SEED-%-M{machine_id}")
        )
    )
    seed_plan_ids = [r[0] for r in seed_plan_rows.all()]

    await db.execute(
        delete(MachineTelemetry).where(MachineTelemetry.machine_id == machine_id)
    )
    await db.execute(
        delete(MlPredictionLog).where(MlPredictionLog.machine_id == machine_id)
    )
    await db.execute(
        delete(OrdresIntervention).where(OrdresIntervention.machine_id == machine_id)
    )

    if seed_ot_ids:
        await db.execute(
            delete(PlanningOrdresTravail).where(
                PlanningOrdresTravail.ordre_travail_id.in_(seed_ot_ids)
            )
        )
        await db.execute(delete(OrdresTravail).where(OrdresTravail.id.in_(seed_ot_ids)))

    if seed_plan_ids:
        await db.execute(
            delete(PlanningTaches).where(PlanningTaches.planning_id.in_(seed_plan_ids))
        )
        await db.execute(
            delete(PlanningMachines).where(
                PlanningMachines.planning_id.in_(seed_plan_ids)
            )
        )
        await db.execute(
            delete(PlanningUtilisateurs).where(
                PlanningUtilisateurs.planning_id.in_(seed_plan_ids)
            )
        )
        await db.execute(delete(Plannings).where(Plannings.id.in_(seed_plan_ids)))

    logger.info(f"Cleanup complete for machine_id={machine_id}.")


# ── Per-machine seed ─────────────────────────────────────────────────────────


async def _seed_machine(
    db, machine: Machines, techniciens: list, cheftech, chetop, num_cycles: int
) -> dict:
    machine_id = machine.id
    rng = random.Random(1000 + machine_id)  # reproducible, distinct per machine
    severity = rng.uniform(0.7, 1.3)

    now = datetime.now(timezone.utc)
    days_span = DAYS_SPAN_PER_CYCLE * num_cycles
    days_per_cycle = days_span / num_cycles

    # Stagger this machine's whole timeline further into the past by a random
    # amount (0..1 cycle length) so 4 machines don't all land on identical
    # calendar days — always shifts backward, so it never pushes past `now`.
    time_offset = timedelta(days=rng.uniform(0, days_per_cycle))

    failure_type_counts: dict = {}

    for cycle_idx in range(num_cycles):
        cycle_num = cycle_idx + 1
        cfg = _cycle_params(cycle_idx, num_cycles, severity)

        # Round-robin technician across the whole crew so every tech gets
        # planning tasks / ITVs / telemetry attributed to them.
        technicien = techniciens[cycle_idx % len(techniciens)]

        days_from_end = days_span - (cycle_idx + 1) * days_per_cycle
        c_start = now - timedelta(days=days_span - cycle_idx * days_per_cycle) - time_offset
        c_end = now - timedelta(days=max(0.5, days_from_end)) - time_offset
        c_mid = c_start + (c_end - c_start) / 2
        itv_requested_at = c_mid

        failure_type_counts[cfg["failure_type"]] = (
            failure_type_counts.get(cfg["failure_type"], 0) + 1
        )

        # ── Steps 1-7: Planning → bridge rows → PlanningTaches → ITV → OT → links ──
        _planning, _itv, ot = await create_seed_cycle_records(
            db, machine_id, cheftech, chetop, technicien, cycle_num,
            c_start, c_mid, c_end, itv_requested_at, cfg,
            descriptions={
                "diag": f"Diagnostic — cycle {cycle_num} ({cfg['failure_type']})",
                "corr": f"Correction — cycle {cycle_num} ({cfg['failure_type']})",
                "itv_problem": f"Seed cycle {cycle_num} — {cfg['failure_type']}",
                "ot": f"OT seed cycle {cycle_num} — {cfg['failure_type']}",
            },
        )

        # ── Step 8: Telemetry + shadow logs ─────────────────────────────────
        await generate_cycle_telemetry(
            db, ot, machine, technicien, cfg, rng, cycle_num, TELEMETRY_PER_CYCLE,
            c_start, c_end,
            clamps={
                "wear": (0.0, 300.0), "torque": (1.0, 100.0), "rpm": (500, 3000),
                "air": (290.0, 320.0), "proc": (295.0, 330.0),
            },
            priority_fn=lambda f_prob: "P1" if f_prob > 75 else "P2",
        )

    return failure_type_counts


# ── Main seed ──────────────────────────────────────────────────────────────────


async def seed(num_cycles: int, clean_mode: bool, machine_ids: list = None) -> None:
    summary = await run_seed_driver(
        db_manager, num_cycles, clean_mode, machine_ids, IDEMPOTENCY_THRESHOLD,
        _clean_seed_data, _seed_machine, cycles_label="cycles",
    )
    if summary is None:
        return

    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Open localhost:3000/machines/<id> → sensors + failure prob > 0%")
    logger.info("  2. POST /api/v1/ml/retrain → models_retrained: [p1, p2, p3, p5]")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Delete existing seed data per machine before re-seeding")
    parser.add_argument("--cycles", type=int, default=60, help="Maintenance cycles per machine (default: 60)")
    parser.add_argument("--machines", type=str, default=None, help="Comma-separated machine ids to seed (default: all)")
    args = parser.parse_args()

    machine_ids = None
    if args.machines:
        machine_ids = [int(x.strip()) for x in args.machines.split(",") if x.strip()]

    asyncio.run(seed(num_cycles=args.cycles, clean_mode=args.clean, machine_ids=machine_ids))
