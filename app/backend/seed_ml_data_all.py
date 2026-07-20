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

from sqlalchemy import delete, func, select

from core.database import db_manager
from models.alertes import Alert  # noqa: F401 — registers Alert mapper
from models.machine_telemetry import MachineTelemetry
from models.machines import Machines
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail, OrdreStatut
from models.planning_machines import PlanningMachines
from models.planning_ordres_travail import PlanningOrdresTravail
from models.planning_taches import PlanningTaches, TaskType
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings, PlanningStatut, PlanningType
from models.utilisateurs import UserRole, UserStatus, Utilisateurs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
TELEMETRY_PER_CYCLE = 10
DAYS_SPAN_PER_CYCLE = 10  # each cycle spans ~10 days, backdated from now
IDEMPOTENCY_THRESHOLD = 15  # existing telemetry rows → assume machine already seeded


# ── Degradation curve helpers ──────────────────────────────────────────────────


def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation. t in [0, 1]."""
    return start + t * (end - start)


def _noise(rng: random.Random, sigma: float) -> float:
    return rng.gauss(0, sigma)


def _cycle_params(rng: random.Random, cycle_idx: int, num_cycles: int, severity: float) -> dict:
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


def _failure_prob(tool_wear: float) -> float:
    if tool_wear < 100:
        return 0.0
    return min(95.0, (tool_wear - 100.0) / 130.0 * 95.0)


def _risk_level(prob: float) -> str:
    if prob >= 70:
        return "CRITICAL"
    if prob >= 50:
        return "HIGH"
    if prob >= 30:
        return "MEDIUM"
    return "LOW"


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
        cfg = _cycle_params(rng, cycle_idx, num_cycles, severity)

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

        # ── Step 1: Planning ────────────────────────────────────────────────
        planning = Plannings(
            identifiant_planning=f"SEED-PLAN-C{cycle_num:02d}-M{machine_id}",
            date_debut=c_start,
            date_fin=c_end,
            type=PlanningType.MAINTENANCE,
            planning_statut=PlanningStatut.APPROVED,
            chef_operation_id=chetop.id,
            chef_technique_id=cheftech.id,
            zone_travail="Zone-SEED",
            created_at=c_start,
        )
        db.add(planning)
        await db.flush()

        # ── Step 2: Bridge records ──────────────────────────────────────────
        db.add(
            PlanningMachines(
                planning_id=planning.id, machine_id=machine_id, created_at=c_start
            )
        )
        db.add(
            PlanningUtilisateurs(
                planning_id=planning.id, utilisateur_id=technicien.id, created_at=c_start
            )
        )
        db.add(
            PlanningUtilisateurs(
                planning_id=planning.id, utilisateur_id=cheftech.id, created_at=c_start
            )
        )

        # ── Step 3: Planning taches ─────────────────────────────────────────
        tache_diag = PlanningTaches(
            planning_id=planning.id,
            titre=f"Diagnostic C{cycle_num:02d}",
            description=f"Diagnostic — cycle {cycle_num} ({cfg['failure_type']})",
            technicien_id=technicien.id,
            machine_id=machine_id,
            task_type=TaskType.DIAGNOSTIC,
            date_debut=c_start,
            date_fin=c_mid,
            statut="APPROVED",
            created_by=cheftech.id,
        )
        tache_corr = PlanningTaches(
            planning_id=planning.id,
            titre=f"Correction C{cycle_num:02d}",
            description=f"Correction — cycle {cycle_num} ({cfg['failure_type']})",
            technicien_id=technicien.id,
            machine_id=machine_id,
            task_type=TaskType.CORRECTION,
            date_debut=c_mid,
            date_fin=c_end,
            statut="APPROVED",
            created_by=cheftech.id,
        )
        db.add(tache_diag)
        db.add(tache_corr)
        await db.flush()

        # ── Step 4: ITV (ordre_travail_id=None — created BEFORE OT) ─────────
        itv = OrdresIntervention(
            machine_id=machine_id,
            planning_id=planning.id,
            planning_tache_id=tache_diag.id,
            ordre_travail_id=None,
            technician_id=technicien.id,
            requested_by=chetop.id,
            approved_by=chetop.id,
            approved_at=c_start + timedelta(hours=12),
            statut="TERMINEE",
            date_intervention=c_end,
            date_debut=c_start,
            date_fin=c_end,
            requested_at=itv_requested_at,
            actual_failure_type=cfg["failure_type"],
            ml_prediction_matched=False,
            retrained=False,
            is_synthetic=True,
            intervention_type=cfg["itv_type"],
            machine_status_after="OPERATIONNELLE",
            priority=cfg["priority"],
            problem_description=f"Seed cycle {cycle_num} — {cfg['failure_type']}",
        )
        db.add(itv)
        await db.flush()

        # ── Step 5: OT ───────────────────────────────────────────────────────
        ot = OrdresTravail(
            titre=f"OT-SEED-C{cycle_num:02d}-M{machine_id}",
            description=f"OT seed cycle {cycle_num} — {cfg['failure_type']}",
            priorite=cfg["priority"],
            machine_id=machine_id,
            utilisateur_id=cheftech.id,
            statut=OrdreStatut.CLOSED,
            created_by=chetop.id,
            date_debut=c_start,
            date_fin=c_end,
        )
        db.add(ot)
        await db.flush()

        # ── Step 6: Link ITV → OT ───────────────────────────────────────────
        itv.ordre_travail_id = ot.id

        # ── Step 7: Link Planning → OT ──────────────────────────────────────
        db.add(
            PlanningOrdresTravail(
                planning_id=planning.id, ordre_travail_id=ot.id, created_at=c_start
            )
        )

        # ── Step 8: Telemetry + shadow logs ─────────────────────────────────
        wear_start, wear_end = cfg["tool_wear"]
        torque_start, torque_end = cfg["torque"]
        rpm_start, rpm_end = cfg["rpm"]
        air_start, air_end = cfg["air_temp"]

        telemetry_span_secs = (c_end - c_start).total_seconds()
        step_interval_secs = telemetry_span_secs / max(TELEMETRY_PER_CYCLE - 1, 1)

        for step in range(TELEMETRY_PER_CYCLE):
            frac = step / max(TELEMETRY_PER_CYCLE - 1, 1)

            wear = _lerp(wear_start, wear_end, frac) + _noise(rng, 1.5)
            torq = _lerp(torque_start, torque_end, frac) + _noise(rng, 0.5)
            rpm = int(_lerp(rpm_start, rpm_end, frac)) + int(_noise(rng, 15))
            air = _lerp(air_start, air_end, frac) + _noise(rng, 0.3)
            proc = air + 10.0 + _noise(rng, 0.2)

            wear = max(0.0, min(300.0, wear))
            torq = max(1.0, min(100.0, torq))
            rpm = max(500, min(3000, rpm))
            air = max(290.0, min(320.0, air))
            proc = max(295.0, min(330.0, proc))

            recorded_at = c_start + timedelta(seconds=step * step_interval_secs)

            telemetry = MachineTelemetry(
                machine_id=machine_id,
                work_order_id=ot.id,
                technician_id=technicien.id,
                air_temperature=round(air, 2),
                process_temperature=round(proc, 2),
                rotational_speed=rpm,
                torque=round(torq, 2),
                tool_wear=round(wear, 2),
                recorded_at=recorded_at,
                notes=f"Seed C{cycle_num:02d} step {step + 1}/{TELEMETRY_PER_CYCLE}",
                is_synthetic=True,
            )
            db.add(telemetry)
            await db.flush()

            f_prob = _failure_prob(wear)
            shadow = MlPredictionLog(
                machine_id=machine_id,
                machine_name=machine.nom,
                risk_level=_risk_level(f_prob),
                failure_probability=round(f_prob, 2),
                rul_days=round(max(0.0, (230.0 - wear) / 2.0), 1),
                predicted_priority="P1" if f_prob > 75 else "P2",
                is_anomaly=wear > 180,
                anomaly_score=round(max(0.0, (wear - 100.0) / 130.0), 4),
                air_temperature=round(air, 2),
                process_temperature=round(proc, 2),
                rotational_speed=rpm,
                torque=round(torq, 2),
                tool_wear=int(wear),
                ml_model_used=False,
                created_at=recorded_at,
                is_synthetic=True,
            )
            db.add(shadow)

        await db.flush()

    return failure_type_counts


# ── Main seed ──────────────────────────────────────────────────────────────────


async def seed(num_cycles: int, clean_mode: bool, machine_ids: list = None) -> None:
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        # ── 1. Fetch every machine in the fleet (optionally filtered) ────────
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

            logger.info(f"── Seeding machine_id={machine.id} ({machine.nom}) — {num_cycles} cycles ──")
            failure_counts = await _seed_machine(
                db, machine, techniciens, cheftech, chetop, num_cycles
            )
            await db.commit()
            summary[machine.id] = failure_counts
            logger.info(f"machine_id={machine.id} done. Failure mix: {failure_counts}")

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Done. Seeded {len(summary)}/{len(machines)} machine(s), {num_cycles} cycles each.")
        for mid, counts in summary.items():
            logger.info(f"  machine_id={mid}: {counts}")
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
