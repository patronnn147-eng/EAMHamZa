"""
seed_ml_data.py — ML Seed Data Script

Simulates 50 full EAM maintenance cycles for machine_id=20, generating
realistic degrading telemetry + shadow ML logs required for retraining.

Degradation arc across 50 cycles (500 days backdated):
  Cycles  1-10  → Healthy       (NONE)
  Cycles 11-20  → Early wear    (NONE / RNF)
  Cycles 21-30  → Heat failure  (HDF)
  Cycles 31-40  → Power / heat  (PWF / HDF)
  Cycles 41-46  → Overstrain    (OSF)
  Cycles 47-50  → Tool wear     (TWF)

Correct workflow per cycle: Planning → ITV (ordre_travail_id=None) → OT → ITV.ordre_travail_id = OT.id

Run:
    docker cp app/backend/seed_ml_data.py asset_management_backend:/app/seed_ml_data.py
    docker exec asset_management_backend python seed_ml_data.py
"""

import asyncio
import logging
import math
import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from core.database import db_manager
import models  # registers all SQLAlchemy mappers
from models.alertes import Alert  # Alert referenced by Utilisateurs.dismissed_alerts
from models.machine_telemetry import MachineTelemetry
from models.machines import Machines
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.planning_machines import Planning_machines
from models.planning_ordres_travail import Planning_ordres_travail
from models.planning_taches import Planning_taches, TaskType
from models.planning_utilisateurs import Planning_utilisateurs
from models.plannings import Plannings, PlanningStatut, PlanningType
from models.utilisateurs import UserRole, UserStatus, Utilisateurs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
TARGET_MACHINE_ID   = 20
NUM_CYCLES          = 50
TELEMETRY_PER_CYCLE = 10
DAYS_SPAN           = 500   # total window backdated from now (50 cycles × ~10 days)
random.seed(42)
CLEAN_MODE = "--clean" in sys.argv


# ── Degradation curve helpers ──────────────────────────────────────────────────

def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation. t in [0, 1]."""
    return start + t * (end - start)


def _noise(sigma: float) -> float:
    return random.gauss(0, sigma)


def _cycle_params(cycle_idx: int) -> dict:
    """
    Return sensor ranges and metadata for cycle_idx (0-based, 0..49).
    Degradation is continuous across 50 cycles.
    """
    t = cycle_idx / (NUM_CYCLES - 1)   # 0.0 → 1.0

    # Sensor endpoints — full arc healthy → critical
    tool_wear_start = _lerp(5.0,   180.0, t)
    tool_wear_end   = _lerp(10.0,  230.0, t)
    torque_start    = _lerp(26.0,  68.0,  t)
    torque_end      = _lerp(32.0,  78.0,  t)
    rpm_start       = int(_lerp(1620, 1080, t))
    rpm_end         = int(_lerp(1580, 1050, t))
    air_start       = _lerp(296.0, 309.0, t)
    air_end         = _lerp(297.0, 311.0, t)

    # Failure type determination based on expected end-of-cycle conditions
    expected_wear     = tool_wear_end
    expected_rpm      = rpm_end
    expected_air_end  = air_end
    expected_proc_end = expected_air_end + 10.0   # proc = air + 10 approximately

    if expected_wear >= 190:
        failure_type = "TWF"
        priority     = "URGENTE"
        itv_type     = "CORRECTIVE"
    elif expected_wear >= 155:
        failure_type = "OSF"
        priority     = "URGENTE"
        itv_type     = "CORRECTIVE"
    elif (expected_proc_end - expected_air_end) < 8.6 and expected_rpm < 1380:
        failure_type = "HDF"
        priority     = "MOYENNE"
        itv_type     = "PREVENTIVE"
    elif expected_wear >= 100:
        failure_type = "PWF"
        priority     = "MOYENNE"
        itv_type     = "PREVENTIVE"
    elif expected_wear >= 60:
        failure_type = "RNF"
        priority     = "MOYENNE"
        itv_type     = "PREVENTIVE"
    else:
        failure_type = "NONE"
        priority     = "MOYENNE"
        itv_type     = "PREVENTIVE"

    return {
        "tool_wear":     (tool_wear_start, tool_wear_end),
        "torque":        (torque_start,    torque_end),
        "rpm":           (rpm_start,       rpm_end),
        "air_temp":      (air_start,       air_end),
        "failure_type":  failure_type,
        "priority":      priority,
        "itv_type":      itv_type,
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


# ── Main seed ──────────────────────────────────────────────────────────────────


async def _clean_seed_data(db) -> None:
    """Delete all seed data for TARGET_MACHINE_ID. Safe to call multiple times."""
    logger.info(f"Cleaning seed data for machine_id={TARGET_MACHINE_ID}...")

    # Collect seed OT ids first (used as FK in ITV + planning_ordres_travail)
    seed_ot_rows = await db.execute(
        select(Ordres_travail.id).where(
            Ordres_travail.machine_id == TARGET_MACHINE_ID,
            Ordres_travail.titre.like("OT-SEED-%"),
        )
    )
    seed_ot_ids = [r[0] for r in seed_ot_rows.all()]

    # Collect seed planning ids
    seed_plan_rows = await db.execute(
        select(Plannings.id).where(Plannings.identifiant_planning.like("SEED-%"))
    )
    seed_plan_ids = [r[0] for r in seed_plan_rows.all()]

    # Delete in safe dependency order
    await db.execute(delete(MachineTelemetry).where(MachineTelemetry.machine_id == TARGET_MACHINE_ID))
    await db.execute(delete(MlPredictionLog).where(MlPredictionLog.machine_id == TARGET_MACHINE_ID))

    if seed_ot_ids:
        await db.execute(delete(Ordres_intervention).where(Ordres_intervention.ordre_travail_id.in_(seed_ot_ids)))
        await db.execute(delete(Planning_ordres_travail).where(Planning_ordres_travail.ordre_travail_id.in_(seed_ot_ids)))
        await db.execute(delete(Ordres_travail).where(Ordres_travail.id.in_(seed_ot_ids)))

    if seed_plan_ids:
        await db.execute(delete(Planning_taches).where(Planning_taches.planning_id.in_(seed_plan_ids)))
        await db.execute(delete(Planning_machines).where(Planning_machines.planning_id.in_(seed_plan_ids)))
        await db.execute(delete(Planning_utilisateurs).where(Planning_utilisateurs.planning_id.in_(seed_plan_ids)))
        await db.execute(delete(Plannings).where(Plannings.id.in_(seed_plan_ids)))

    logger.info("Cleanup complete.")


async def seed():
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        now = datetime.now(timezone.utc)

        # ── 0. Clean old seed data if --clean flag passed ──────────────────────────
        if CLEAN_MODE:
            await _clean_seed_data(db)
            await db.commit()


        # ── 1. Validate prerequisites ──────────────────────────────────────────
        machine = await db.get(Machines, TARGET_MACHINE_ID)
        if not machine:
            logger.error(f"machine_id={TARGET_MACHINE_ID} not found. Aborting.")
            sys.exit(1)

        async def _get_users(role: UserRole):
            result = await db.execute(
                select(Utilisateurs).where(
                    Utilisateurs.role == role,
                    Utilisateurs.status == UserStatus.APPROVED,
                )
            )
            return result.scalars().all()

        techniciens = await _get_users(UserRole.TECHNICIEN)
        cheftechs   = await _get_users(UserRole.CHEFTECH)
        chetops     = await _get_users(UserRole.CHETOP)

        missing = []
        if not techniciens: missing.append("TECHNICIEN (APPROVED)")
        if not cheftechs:   missing.append("CHEFTECH (APPROVED)")
        if not chetops:     missing.append("CHETOP (APPROVED)")
        if missing:
            logger.error(f"Missing required users: {', '.join(missing)}. Aborting.")
            sys.exit(1)

        technicien = techniciens[0]
        cheftech   = cheftechs[0]
        chetop     = chetops[0]

        logger.info(
            f"Users — TECH: {technicien.nom} (id={technicien.id}), "
            f"CHEFTECH: {cheftech.nom} (id={cheftech.id}), "
            f"CHETOP: {chetop.nom} (id={chetop.id})"
        )

        # ── 2. Idempotency check ───────────────────────────────────────────────
        count_result = await db.execute(
            select(func.count(MachineTelemetry.id)).where(
                MachineTelemetry.machine_id == TARGET_MACHINE_ID
            )
        )
        existing_count = count_result.scalar() or 0
        if existing_count >= 15 and not CLEAN_MODE:
            logger.info(
                f"machine_id={TARGET_MACHINE_ID} already has {existing_count} telemetry rows. "
                "Already seeded — skipping. Use --clean to re-seed."
            )
            return

        # ── 3. Compute cycle windows ───────────────────────────────────────────
        # Each cycle spans ~DAYS_SPAN / NUM_CYCLES days
        days_per_cycle = DAYS_SPAN / NUM_CYCLES   # = 10 days per cycle

        # ITV requested_at = cycle_mid for each cycle
        # (always after telemetry readings → retraining join satisfied)

        # ── 4. Create cycles ───────────────────────────────────────────────────
        failure_type_counts: dict = {}

        for cycle_idx in range(NUM_CYCLES):
            cycle_num = cycle_idx + 1
            cfg = _cycle_params(cycle_idx)

            # Cycle date window (backdated from now)
            days_from_end = DAYS_SPAN - (cycle_idx + 1) * days_per_cycle
            c_start = now - timedelta(days=DAYS_SPAN - cycle_idx * days_per_cycle)
            c_end   = now - timedelta(days=max(0.5, days_from_end))
            c_mid   = c_start + (c_end - c_start) / 2
            itv_requested_at = c_mid   # mid of cycle, always after telemetry start

            failure_type_counts[cfg["failure_type"]] = failure_type_counts.get(cfg["failure_type"], 0) + 1

            logger.info(
                f"[{cycle_num:02d}/50] {cfg['failure_type']:4s} | "
                f"wear {cfg['tool_wear'][0]:.0f}→{cfg['tool_wear'][1]:.0f} | "
                f"{c_start.date()} → {c_end.date()}"
            )

            # ── Step 1: Planning ───────────────────────────────────────────────
            planning = Plannings(
                identifiant_planning = f"SEED-PLAN-C{cycle_num:02d}-M{TARGET_MACHINE_ID}",
                date_debut           = c_start,
                date_fin             = c_end,
                type                 = PlanningType.MAINTENANCE,
                planning_statut      = PlanningStatut.APPROVED,
                chef_operation_id    = chetop.id,
                chef_technique_id    = cheftech.id,
                zone_travail         = "Zone-SEED",
                created_at           = c_start,
            )
            db.add(planning)
            await db.flush()

            # ── Step 2: Bridge records ─────────────────────────────────────────
            db.add(Planning_machines(
                planning_id = planning.id,
                machine_id  = TARGET_MACHINE_ID,
                created_at  = c_start,
            ))
            db.add(Planning_utilisateurs(
                planning_id    = planning.id,
                utilisateur_id = technicien.id,
                created_at     = c_start,
            ))
            db.add(Planning_utilisateurs(
                planning_id    = planning.id,
                utilisateur_id = cheftech.id,
                created_at     = c_start,
            ))

            # ── Step 3: Planning taches ────────────────────────────────────────
            tache_diag = Planning_taches(
                planning_id  = planning.id,
                titre        = f"Diagnostic C{cycle_num:02d}",
                description  = f"Diagnostic — cycle {cycle_num} ({cfg['failure_type']})",
                technicien_id= technicien.id,
                machine_id   = TARGET_MACHINE_ID,
                task_type    = TaskType.DIAGNOSTIC,
                date_debut   = c_start,
                date_fin     = c_mid,
                statut       = "APPROVED",
                created_by   = cheftech.id,
            )
            tache_corr = Planning_taches(
                planning_id  = planning.id,
                titre        = f"Correction C{cycle_num:02d}",
                description  = f"Correction — cycle {cycle_num} ({cfg['failure_type']})",
                technicien_id= technicien.id,
                machine_id   = TARGET_MACHINE_ID,
                task_type    = TaskType.CORRECTION,
                date_debut   = c_mid,
                date_fin     = c_end,
                statut       = "APPROVED",
                created_by   = cheftech.id,
            )
            db.add(tache_diag)
            db.add(tache_corr)
            await db.flush()

            # ── Step 4: ITV (ordre_travail_id=None — created BEFORE OT) ────────
            itv = Ordres_intervention(
                machine_id            = TARGET_MACHINE_ID,
                planning_id           = planning.id,
                planning_tache_id     = tache_diag.id,
                ordre_travail_id      = None,        # ← linked after OT created
                technician_id         = technicien.id,
                requested_by          = chetop.id,
                approved_by           = chetop.id,
                approved_at           = c_start + timedelta(hours=12),
                statut                = "TERMINEE",
                date_intervention     = c_end,
                date_debut            = c_start,
                date_fin              = c_end,
                requested_at          = itv_requested_at,
                actual_failure_type   = cfg["failure_type"],
                ml_prediction_matched = False,
                retrained             = False,
                intervention_type     = cfg["itv_type"],
                machine_status_after  = "OPERATIONNELLE",
                priority              = cfg["priority"],
                problem_description   = f"Seed cycle {cycle_num} — {cfg['failure_type']}",
            )
            db.add(itv)
            await db.flush()

            # ── Step 5: OT ────────────────────────────────────────────────────
            ot = Ordres_travail(
                titre          = f"OT-SEED-C{cycle_num:02d}-M{TARGET_MACHINE_ID}",
                description    = f"OT seed cycle {cycle_num} — {cfg['failure_type']}",
                priorite       = cfg["priority"],
                machine_id     = TARGET_MACHINE_ID,
                utilisateur_id = cheftech.id,
                statut         = OrdreStatut.CLOSED,
                created_by     = chetop.id,
                date_debut     = c_start,
                date_fin       = c_end,
            )
            db.add(ot)
            await db.flush()

            # ── Step 6: Link ITV → OT ──────────────────────────────────────────
            itv.ordre_travail_id = ot.id

            # ── Step 7: Link Planning → OT ─────────────────────────────────────
            db.add(Planning_ordres_travail(
                planning_id      = planning.id,
                ordre_travail_id = ot.id,
                created_at       = c_start,
            ))

            # ── Step 8: Telemetry + shadow logs ────────────────────────────────
            wear_start,   wear_end   = cfg["tool_wear"]
            torque_start, torque_end = cfg["torque"]
            rpm_start,    rpm_end    = cfg["rpm"]
            air_start,    air_end    = cfg["air_temp"]

            telemetry_span_secs = (c_end - c_start).total_seconds()
            step_interval_secs  = telemetry_span_secs / max(TELEMETRY_PER_CYCLE - 1, 1)

            for step in range(TELEMETRY_PER_CYCLE):
                frac = step / max(TELEMETRY_PER_CYCLE - 1, 1)

                wear  = _lerp(wear_start,   wear_end,   frac) + _noise(1.5)
                torq  = _lerp(torque_start, torque_end, frac) + _noise(0.5)
                rpm   = int(_lerp(rpm_start, rpm_end, frac))  + int(_noise(15))
                air   = _lerp(air_start,    air_end,    frac) + _noise(0.3)
                proc  = air + 10.0 + _noise(0.2)

                # Clamp
                wear  = max(0.0,   min(300.0, wear))
                torq  = max(1.0,   min(100.0, torq))
                rpm   = max(500,   min(3000,  rpm))
                air   = max(290.0, min(320.0, air))
                proc  = max(295.0, min(330.0, proc))

                recorded_at = c_start + timedelta(seconds=step * step_interval_secs)

                telemetry = MachineTelemetry(
                    machine_id          = TARGET_MACHINE_ID,
                    work_order_id       = ot.id,
                    technician_id       = technicien.id,
                    air_temperature     = round(air,  2),
                    process_temperature = round(proc, 2),
                    rotational_speed    = rpm,
                    torque              = round(torq, 2),
                    tool_wear           = round(wear, 2),
                    recorded_at         = recorded_at,
                    notes               = f"Seed C{cycle_num:02d} step {step + 1}/{TELEMETRY_PER_CYCLE}",
                )
                db.add(telemetry)
                await db.flush()

                f_prob = _failure_prob(wear)
                shadow = MlPredictionLog(
                    machine_id          = TARGET_MACHINE_ID,
                    machine_name        = machine.nom,
                    risk_level          = _risk_level(f_prob),
                    failure_probability = round(f_prob, 2),
                    rul_days            = round(max(0.0, (230.0 - wear) / 2.0), 1),
                    predicted_priority  = "P1" if f_prob > 75 else "P2",
                    is_anomaly          = wear > 180,
                    anomaly_score       = round(max(0.0, (wear - 100.0) / 130.0), 4),
                    air_temperature     = round(air,  2),
                    process_temperature = round(proc, 2),
                    rotational_speed    = rpm,
                    torque              = round(torq, 2),
                    tool_wear           = int(wear),
                    ml_model_used       = False,
                    created_at          = recorded_at,   # ← critical for retraining join
                )
                db.add(shadow)

            await db.flush()

        # ── 5. Commit ──────────────────────────────────────────────────────────
        await db.commit()

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Done. {NUM_CYCLES} cycles seeded for machine_id={TARGET_MACHINE_ID}.")
        logger.info(f"  {NUM_CYCLES} Plannings (APPROVED, MAINTENANCE)")
        logger.info(f"  {NUM_CYCLES * 2} Planning_taches (DIAGNOSTIC + CORRECTION × {NUM_CYCLES})")
        logger.info(f"  {NUM_CYCLES} ITVs  | {NUM_CYCLES} OTs (CLOSED)")
        logger.info(f"  {NUM_CYCLES * TELEMETRY_PER_CYCLE} MachineTelemetry rows")
        logger.info(f"  {NUM_CYCLES * TELEMETRY_PER_CYCLE} MlPredictionLog shadow rows")
        logger.info(f"  Failure type distribution: {failure_type_counts}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Open localhost:3000/machines/20 → sensors + failure prob > 0%")
        logger.info("  2. POST /api/v1/ml/retrain → models_retrained: [p1, p2, p3, p5]")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
