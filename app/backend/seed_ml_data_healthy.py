"""
seed_ml_data_healthy.py — ML Seed Data Script (HEALTHY telemetry, ALL machines)

Mirror of seed_ml_data_all.py's Planning -> ITV -> OT -> Telemetry cycle chain,
but every cycle simulates a machine operating in normal conditions instead of
degrading toward failure. Sensor bands are grounded in ai4i2020.csv's overall
mean/std (the same dataset P1-P4 train on) so healthy readings sit close to
the training distribution instead of drifting toward the tails that read as
anomalous.

Per cycle, tool wear follows one of two stationary (non-trending) patterns,
chosen once per machine via seeded RNG so the fleet isn't uniform:
  - "sawtooth": wear rises within the cycle (normal use) then resets low next
    cycle (preventive service replaces/reconditions the tool)
  - "flat": wear hovers near a fixed baseline +/- noise, no cycle structure

Both patterns stay well under the 100min risk threshold used by
_failure_prob() and the P4 IF thresholds, so failure_probability and
anomaly_score come out ~0 by construction — never by clamping.

Same relationships/schema as the abnormal generator: Telemetry.work_order_id
-> OrdresTravail, OrdresIntervention.ordre_travail_id -> OrdresTravail,
Planning -> PlanningMachines/PlanningUtilisateurs/PlanningTaches, and
is_synthetic=True on both Telemetry and MlPredictionLog rows.

Run:
    docker cp app/backend/seed_ml_data_healthy.py asset_management_backend:/app/seed_ml_data_healthy.py
    docker exec asset_management_backend python seed_ml_data_healthy.py
    docker exec asset_management_backend python seed_ml_data_healthy.py --clean
    docker exec asset_management_backend python seed_ml_data_healthy.py --cycles 30
    docker exec asset_management_backend python seed_ml_data_healthy.py --machines 1,2

For a mixed fleet (some healthy, some abnormal), run this script with
--machines scoped to a subset, and seed_ml_data_all.py --machines with the
disjoint remainder.
"""

import argparse
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

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
from models.utilisateurs import UserRole, UserStatus, Utilisateurs
from seed_common import (
    _failure_prob,
    _lerp,
    _noise,
    _risk_level,
    create_seed_cycle_records,
    generate_cycle_telemetry,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
TELEMETRY_PER_CYCLE = 10
# Healthy machines get infrequent, well-spaced PREVENTIVE visits (~quarterly),
# not the abnormal script's 10-day corrective-repair cadence. rul_calculator's
# hist_mtbf_days is literally the mean gap between OrdresIntervention.date_intervention
# timestamps — a 10-day cadence would read as "this machine breaks every 10 days"
# regardless of sensor values, collapsing rul_days and forcing risk_level=CRITICAL.
DAYS_SPAN_PER_CYCLE = 45  # each cycle spans ~45 days, backdated from now
IDEMPOTENCY_THRESHOLD = 15  # existing telemetry rows → assume machine already seeded


# ── Healthy sensor-curve helpers ────────────────────────────────────────────────
# Ranges grounded in ai4i2020.csv full-dataset mean/std: air 300±2K,
# process 310±1.5K, rpm 1539±179, torque 40±10Nm, tool_wear 108±64min.
# Every cycle is drawn independently (stationary) — no across-cycle trend —
# so nothing here can be mistaken for a degradation arc.


def _healthy_cycle_params(rng: random.Random, wear_pattern: str) -> dict:
    """Return sensor ranges + metadata for one healthy cycle."""
    if wear_pattern == "sawtooth":
        wear_start = rng.uniform(3.0, 10.0)
        wear_end = rng.uniform(45.0, 70.0)
    else:  # "flat"
        baseline = rng.uniform(18.0, 30.0)
        wear_start = baseline + rng.uniform(-3.0, 3.0)
        wear_end = baseline + rng.uniform(-3.0, 3.0)

    torque_start = rng.uniform(28.0, 36.0)
    torque_end = rng.uniform(34.0, 45.0)
    rpm_start = int(rng.uniform(1450.0, 1650.0))
    rpm_end = rpm_start + int(rng.uniform(-30.0, 30.0))
    air_start = rng.uniform(297.0, 300.0)
    air_end = air_start + rng.uniform(-0.5, 0.8)

    return {
        "tool_wear": (wear_start, wear_end),
        "torque": (torque_start, torque_end),
        "rpm": (rpm_start, rpm_end),
        "air_temp": (air_start, air_end),
        "failure_type": "NONE",
        "priority": "BASSE",
        "itv_type": "PREVENTIVE",
    }


# ── Cleanup ────────────────────────────────────────────────────────────────────


async def _clean_seed_data(db, machine_id: int) -> None:
    """Delete all seed data for one machine (same prefixes as the abnormal script,
    so re-seeding a machine with a different profile doesn't leave stale rows)."""
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
    rng = random.Random(2000 + machine_id)  # reproducible, distinct per machine
    wear_pattern = rng.choice(["sawtooth", "flat"])

    now = datetime.now(timezone.utc)
    days_span = DAYS_SPAN_PER_CYCLE * num_cycles
    days_per_cycle = days_span / num_cycles
    time_offset = timedelta(days=rng.uniform(0, days_per_cycle))

    failure_type_counts: dict = {}

    for cycle_idx in range(num_cycles):
        cycle_num = cycle_idx + 1
        cfg = _healthy_cycle_params(rng, wear_pattern)

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
        _planning, itv, ot = await create_seed_cycle_records(
            db, machine_id, cheftech, chetop, technicien, cycle_num,
            c_start, c_mid, c_end, itv_requested_at, cfg,
            diag_description=f"Routine preventive check — cycle {cycle_num}",
            corr_description=f"Routine preventive service — cycle {cycle_num}",
            itv_problem_description=f"Seed cycle {cycle_num} — routine preventive check",
            ot_description=f"OT seed cycle {cycle_num} — routine preventive check",
        )

        # ── Step 8: Telemetry + shadow logs ─────────────────────────────────
        await generate_cycle_telemetry(
            db, ot, machine, technicien, cfg, rng, cycle_num, TELEMETRY_PER_CYCLE,
            c_start, c_end,
            wear_clamp=(0.0, 90.0),  # hard ceiling well under the 100min risk threshold
            torque_clamp=(20.0, 55.0), rpm_clamp=(1300, 1800),
            air_clamp=(295.0, 303.0), proc_clamp=(304.0, 313.0),
            priority_fn=lambda f_prob: "P2",
            notes_suffix=" (healthy)",
        )

    return failure_type_counts


# ── Main seed ──────────────────────────────────────────────────────────────────


async def seed(num_cycles: int, clean_mode: bool, machine_ids: list) -> None:
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        # ── 1. Fetch machines (optionally filtered) ─────────────────────────
        query = select(Machines).order_by(Machines.id)
        if machine_ids:
            query = query.where(Machines.id.in_(machine_ids))
        machines = (await db.execute(query)).scalars().all()
        if not machines:
            logger.error("No matching machines found in DB. Aborting.")
            return

        logger.info(f"Found {len(machines)} machine(s): {[m.id for m in machines]}")

        # ── 2. Validate prerequisite users (shared across all machines) ─────
        async def _get_users(role: UserRole):
            result = await db.execute(
                select(Utilisateurs).where(
                    Utilisateurs.role == role,
                    Utilisateurs.status == UserStatus.APPROVED,
                )
            )
            return result.scalars().all()

        techniciens = await _get_users(UserRole.TECHNICIEN)
        cheftechs = await _get_users(UserRole.CHEFTECH)
        chetops = await _get_users(UserRole.CHETOP)

        missing = []
        if not techniciens:
            missing.append("TECHNICIEN (APPROVED)")
        if not cheftechs:
            missing.append("CHEFTECH (APPROVED)")
        if not chetops:
            missing.append("CHETOP (APPROVED)")
        if missing:
            logger.error(f"Missing required users: {', '.join(missing)}. Aborting.")
            return

        cheftech = cheftechs[0]
        chetop = chetops[0]

        logger.info(
            f"Users — {len(techniciens)} TECH(s): "
            f"{', '.join(f'{t.nom}(id={t.id})' for t in techniciens)} | "
            f"CHEFTECH: {cheftech.nom} (id={cheftech.id}), "
            f"CHETOP: {chetop.nom} (id={chetop.id})"
        )

        # ── 3. Seed each machine ─────────────────────────────────────────────
        summary = {}
        for machine in machines:
            if clean_mode:
                await _clean_seed_data(db, machine.id)
                await db.commit()

            count_result = await db.execute(
                select(func.count(MachineTelemetry.id)).where(
                    MachineTelemetry.machine_id == machine.id
                )
            )
            existing_count = count_result.scalar() or 0
            if existing_count >= IDEMPOTENCY_THRESHOLD and not clean_mode:
                logger.info(
                    f"machine_id={machine.id} already has {existing_count} telemetry rows. "
                    "Skipping (use --clean to re-seed)."
                )
                continue

            logger.info(f"── Seeding HEALTHY machine_id={machine.id} ({machine.nom}) — {num_cycles} cycles ──")
            failure_counts = await _seed_machine(
                db, machine, techniciens, cheftech, chetop, num_cycles
            )
            await db.commit()
            summary[machine.id] = failure_counts
            logger.info(f"machine_id={machine.id} done. Cycle mix: {failure_counts}")

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Done. Seeded {len(summary)}/{len(machines)} machine(s), {num_cycles} healthy cycles each.")
        for mid, counts in summary.items():
            logger.info(f"  machine_id={mid}: {counts}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Open localhost:3000/machines/<id> → sensors normal, failure prob ~0%")
        logger.info("  2. GET /api/v1/ml/predict/anomaly → is_anomaly=false, low anomaly_score")
        logger.info("  3. POST /api/v1/ml/retrain → models_retrained: [p1, p2, p3, p5]")
        logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Delete existing seed data per machine before re-seeding")
    parser.add_argument("--cycles", type=int, default=12, help="Preventive-maintenance cycles per machine, ~45 days apart (default: 12, ~1.5yr history)")
    parser.add_argument("--machines", type=str, default=None, help="Comma-separated machine ids to seed (default: all)")
    args = parser.parse_args()

    machine_ids = None
    if args.machines:
        machine_ids = [int(x.strip()) for x in args.machines.split(",") if x.strip()]

    asyncio.run(seed(num_cycles=args.cycles, clean_mode=args.clean, machine_ids=machine_ids))
