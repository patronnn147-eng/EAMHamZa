"""
seed_ml_data_m13.py — ML Seed Data Script for Machine #13

Generates 60 full EAM maintenance cycles for machine_id=13.
Mixed arc — some stable WOs, some degraded, reflecting a machine
that runs fine, develops recurring overstraining + heat issues,
partially recovers after intervention, then enters critical wear.

Degradation arc across 60 cycles (600 days backdated):
  Cycles  1-18  → Healthy           (NONE)
  Cycles 19-26  → Early friction     (RNF)
  Cycles 27-33  → Heat buildup       (HDF)
  Cycles 34-38  → Post-repair good   (NONE)   ← recovery window
  Cycles 39-47  → Power + heat       (PWF / HDF)
  Cycles 48-54  → Overstrain         (OSF)
  Cycles 55-60  → Tool wear critical (TWF)

WO breakdown: ~38 stable/acceptable + 22 clearly problematic.

Run:
    docker cp app/backend/seed_ml_data_m13.py asset_management_backend:/app/seed_ml_data_m13.py
    docker exec asset_management_backend python seed_ml_data_m13.py
    docker exec asset_management_backend python seed_ml_data_m13.py --clean   # reset + re-seed
"""

import asyncio
import logging
import random
import sys
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
from models.planning_OrdresTravail import PlanningOrdresTravail
from models.planning_taches import PlanningTaches, TaskType
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings, PlanningStatut, PlanningType
from models.utilisateurs import UserRole, UserStatus, Utilisateurs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────────
TARGET_MACHINE_ID = 13
NUM_CYCLES = 60
TELEMETRY_PER_CYCLE = 10
DAYS_SPAN = 600  # 60 cycles × 10 days
random.seed(13)
CLEAN_MODE = "--clean" in sys.argv


# ── Degradation helpers ─────────────────────────────────────────────────────────


def _lerp(start: float, end: float, t: float) -> float:
    return start + t * (end - start)


def _noise(sigma: float) -> float:
    return random.gauss(0, sigma)


def _cycle_params(cycle_idx: int) -> dict:
    """
    Non-linear degradation arc for machine #13.
    Four phases: healthy → degrading → recovery → critical.
    """
    c = cycle_idx  # 0-based

    # ── Phase A: Healthy (0-17) ──────────────────────────────────────────────
    if c < 18:
        t = c / 17.0
        wear_s = _lerp(3.0, 25.0, t)
        wear_e = _lerp(8.0, 32.0, t)
        torq_s = _lerp(26.0, 30.0, t)
        torq_e = _lerp(29.0, 34.0, t)
        rpm_s = int(_lerp(1620, 1590, t))
        rpm_e = int(_lerp(1590, 1560, t))
        air_s = _lerp(295.0, 298.0, t)
        air_e = _lerp(296.0, 299.5, t)
        failure_type = "NONE"
        priority = "BASSE"
        itv_type = "PREVENTIVE"

    # ── Phase B: Early friction (18-25) ─────────────────────────────────────
    elif c < 26:
        t = (c - 18) / 7.0
        wear_s = _lerp(32.0, 65.0, t)
        wear_e = _lerp(48.0, 85.0, t)
        torq_s = _lerp(34.0, 44.0, t)
        torq_e = _lerp(40.0, 52.0, t)
        rpm_s = int(_lerp(1555, 1480, t))
        rpm_e = int(_lerp(1520, 1440, t))
        air_s = _lerp(299.0, 302.5, t)
        air_e = _lerp(300.5, 304.0, t)
        failure_type = "RNF"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"

    # ── Phase C: Heat buildup (26-32) ───────────────────────────────────────
    elif c < 33:
        t = (c - 26) / 6.0
        wear_s = _lerp(65.0, 95.0, t)
        wear_e = _lerp(82.0, 115.0, t)
        torq_s = _lerp(44.0, 55.0, t)
        torq_e = _lerp(52.0, 63.0, t)
        rpm_s = int(_lerp(1475, 1380, t))
        rpm_e = int(_lerp(1430, 1330, t))
        air_s = _lerp(302.0, 306.0, t)
        air_e = _lerp(303.5, 308.0, t)
        failure_type = "HDF"
        priority = "MOYENNE"
        itv_type = "PREVENTIVE"

    # ── Phase D: Recovery after repair (33-37) ──────────────────────────────
    elif c < 38:
        t = (c - 33) / 4.0
        wear_s = _lerp(8.0, 18.0, t)
        wear_e = _lerp(14.0, 26.0, t)
        torq_s = _lerp(26.0, 29.0, t)
        torq_e = _lerp(30.0, 34.0, t)
        rpm_s = int(_lerp(1600, 1575, t))
        rpm_e = int(_lerp(1575, 1550, t))
        air_s = _lerp(295.5, 297.0, t)
        air_e = _lerp(297.0, 298.5, t)
        failure_type = "NONE"
        priority = "BASSE"
        itv_type = "PREVENTIVE"

    # ── Phase E: Power + heat (38-46) ───────────────────────────────────────
    elif c < 47:
        t = (c - 38) / 8.0
        wear_s = _lerp(28.0, 105.0, t)
        wear_e = _lerp(52.0, 130.0, t)
        torq_s = _lerp(42.0, 62.0, t)
        torq_e = _lerp(54.0, 72.0, t)
        rpm_s = int(_lerp(1540, 1240, t))
        rpm_e = int(_lerp(1490, 1180, t))
        air_s = _lerp(298.0, 305.5, t)
        air_e = _lerp(300.0, 307.0, t)
        failure_type = "PWF" if t > 0.4 else "HDF"
        priority = "HAUTE" if t > 0.5 else "MOYENNE"
        itv_type = "CORRECTIVE" if t > 0.5 else "PREVENTIVE"

    # ── Phase F: Overstrain (47-53) ─────────────────────────────────────────
    elif c < 54:
        t = (c - 47) / 6.0
        wear_s = _lerp(125.0, 168.0, t)
        wear_e = _lerp(148.0, 192.0, t)
        torq_s = _lerp(62.0, 74.0, t)
        torq_e = _lerp(70.0, 82.0, t)
        rpm_s = int(_lerp(1175, 1060, t))
        rpm_e = int(_lerp(1120, 1020, t))
        air_s = _lerp(305.0, 308.5, t)
        air_e = _lerp(307.0, 311.0, t)
        failure_type = "OSF"
        priority = "URGENTE"
        itv_type = "CORRECTIVE"

    # ── Phase G: Tool wear critical (54-59) ─────────────────────────────────
    else:
        t = (c - 54) / 5.0
        wear_s = _lerp(170.0, 200.0, t)
        wear_e = _lerp(205.0, 240.0, t)
        torq_s = _lerp(72.0, 78.0, t)
        torq_e = _lerp(78.0, 86.0, t)
        rpm_s = int(_lerp(1055, 1010, t))
        rpm_e = int(_lerp(1010, 970, t))
        air_s = _lerp(308.0, 311.0, t)
        air_e = _lerp(310.0, 313.0, t)
        failure_type = "TWF"
        priority = "URGENTE"
        itv_type = "CORRECTIVE"

    return {
        "tool_wear": (wear_s, wear_e),
        "torque": (torq_s, torq_e),
        "rpm": (rpm_s, rpm_e),
        "air_temp": (air_s, air_e),
        "failure_type": failure_type,
        "priority": priority,
        "itv_type": itv_type,
    }


def _failure_prob(tool_wear: float) -> float:
    if tool_wear < 80:
        return 0.0
    return min(95.0, (tool_wear - 80.0) / 160.0 * 95.0)


def _risk_level(prob: float) -> str:
    if prob >= 70:
        return "CRITICAL"
    if prob >= 50:
        return "HIGH"
    if prob >= 30:
        return "MEDIUM"
    return "LOW"


# ── Clean helper ────────────────────────────────────────────────────────────────


async def _clean_seed_data(db) -> None:
    logger.info(f"Cleaning seed data for machine_id={TARGET_MACHINE_ID}...")

    seed_ot_rows = await db.execute(
        select(OrdresTravail.id).where(
            OrdresTravail.machine_id == TARGET_MACHINE_ID,
            OrdresTravail.titre.like("OT-SEED-%"),
        )
    )
    seed_ot_ids = [r[0] for r in seed_ot_rows.all()]

    # Scope plannings to THIS machine only via identifiant pattern
    seed_plan_rows = await db.execute(
        select(Plannings.id).where(
            Plannings.identifiant_planning.like(f"SEED-%-M{TARGET_MACHINE_ID}")
        )
    )
    seed_plan_ids = [r[0] for r in seed_plan_rows.all()]

    await db.execute(
        delete(MachineTelemetry).where(MachineTelemetry.machine_id == TARGET_MACHINE_ID)
    )
    await db.execute(
        delete(MlPredictionLog).where(MlPredictionLog.machine_id == TARGET_MACHINE_ID)
    )

    # Delete ALL interventions for this machine first — covers both
    # ordre_travail_id FK and planning_id FK constraints
    await db.execute(
        delete(OrdresIntervention).where(
            OrdresIntervention.machine_id == TARGET_MACHINE_ID
        )
    )

    if seed_ot_ids:
        await db.execute(
            delete(PlanningOrdresTravail).where(
                PlanningOrdresTravail.ordre_travail_id.in_(seed_ot_ids)
            )
        )
        await db.execute(
            delete(OrdresTravail).where(OrdresTravail.id.in_(seed_ot_ids))
        )

    if seed_plan_ids:
        await db.execute(
            delete(PlanningTaches).where(
                PlanningTaches.planning_id.in_(seed_plan_ids)
            )
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

    logger.info("Cleanup complete.")


# ── Main seed ───────────────────────────────────────────────────────────────────


async def seed():
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        now = datetime.now(timezone.utc)

        if CLEAN_MODE:
            await _clean_seed_data(db)
            await db.commit()

        # ── Validate machine ───────────────────────────────────────────────
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
            sys.exit(1)

        technicien = techniciens[0]
        cheftech = cheftechs[0]
        chetop = chetops[0]

        logger.info(
            f"Users — TECH: {technicien.nom} (id={technicien.id}), "
            f"CHEFTECH: {cheftech.nom} (id={cheftech.id}), "
            f"CHETOP: {chetop.nom} (id={chetop.id})"
        )

        # ── Idempotency check ──────────────────────────────────────────────
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

        days_per_cycle = DAYS_SPAN / NUM_CYCLES  # 10 days per cycle
        failure_type_counts: dict = {}

        for cycle_idx in range(NUM_CYCLES):
            cycle_num = cycle_idx + 1
            cfg = _cycle_params(cycle_idx)

            days_from_end = DAYS_SPAN - (cycle_idx + 1) * days_per_cycle
            c_start = now - timedelta(days=DAYS_SPAN - cycle_idx * days_per_cycle)
            c_end = now - timedelta(days=max(0.5, days_from_end))
            c_mid = c_start + (c_end - c_start) / 2

            failure_type_counts[cfg["failure_type"]] = (
                failure_type_counts.get(cfg["failure_type"], 0) + 1
            )

            logger.info(
                f"[{cycle_num:02d}/{NUM_CYCLES}] {cfg['failure_type']:4s} | "
                f"wear {cfg['tool_wear'][0]:.0f}→{cfg['tool_wear'][1]:.0f} | "
                f"{c_start.date()} → {c_end.date()}"
            )

            # ── Planning ───────────────────────────────────────────────────
            planning = Plannings(
                identifiant_planning=f"SEED-PLAN-C{cycle_num:02d}-M{TARGET_MACHINE_ID}",
                date_debut=c_start,
                date_fin=c_end,
                type=PlanningType.MAINTENANCE,
                planning_statut=PlanningStatut.APPROVED,
                chef_operation_id=chetop.id,
                chef_technique_id=cheftech.id,
                zone_travail="Zone-SEED-M13",
                created_at=c_start,
            )
            db.add(planning)
            await db.flush()

            db.add(
                PlanningMachines(
                    planning_id=planning.id,
                    machine_id=TARGET_MACHINE_ID,
                    created_at=c_start,
                )
            )
            db.add(
                PlanningUtilisateurs(
                    planning_id=planning.id,
                    utilisateur_id=technicien.id,
                    created_at=c_start,
                )
            )
            db.add(
                PlanningUtilisateurs(
                    planning_id=planning.id,
                    utilisateur_id=cheftech.id,
                    created_at=c_start,
                )
            )

            tache_diag = PlanningTaches(
                planning_id=planning.id,
                titre=f"Diagnostic C{cycle_num:02d}",
                description=f"Diagnostic — cycle {cycle_num} ({cfg['failure_type']})",
                technicien_id=technicien.id,
                machine_id=TARGET_MACHINE_ID,
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
                machine_id=TARGET_MACHINE_ID,
                task_type=TaskType.CORRECTION,
                date_debut=c_mid,
                date_fin=c_end,
                statut="APPROVED",
                created_by=cheftech.id,
            )
            db.add(tache_diag)
            db.add(tache_corr)
            await db.flush()

            # ── ITV (created before OT, linked after) ─────────────────────
            itv = OrdresIntervention(
                machine_id=TARGET_MACHINE_ID,
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
                requested_at=c_mid,
                actual_failure_type=cfg["failure_type"],
                ml_prediction_matched=False,
                retrained=False,
                intervention_type=cfg["itv_type"],
                machine_status_after="OPERATIONNELLE",
                priority=cfg["priority"],
                problem_description=f"Seed cycle {cycle_num} — {cfg['failure_type']}",
            )
            db.add(itv)
            await db.flush()

            # ── OT ─────────────────────────────────────────────────────────
            ot = OrdresTravail(
                titre=f"OT-SEED-C{cycle_num:02d}-M{TARGET_MACHINE_ID}",
                description=f"OT seed cycle {cycle_num} — {cfg['failure_type']}",
                priorite=cfg["priority"],
                machine_id=TARGET_MACHINE_ID,
                utilisateur_id=cheftech.id,
                statut=OrdreStatut.CLOSED,
                created_by=chetop.id,
                date_debut=c_start,
                date_fin=c_end,
            )
            db.add(ot)
            await db.flush()

            itv.ordre_travail_id = ot.id

            db.add(
                PlanningOrdresTravail(
                    planning_id=planning.id,
                    ordre_travail_id=ot.id,
                    created_at=c_start,
                )
            )

            # ── Telemetry + shadow logs ─────────────────────────────────────
            wear_start, wear_end = cfg["tool_wear"]
            torque_start, torque_end = cfg["torque"]
            rpm_start, rpm_end = cfg["rpm"]
            air_start, air_end = cfg["air_temp"]

            telemetry_span_secs = (c_end - c_start).total_seconds()
            step_interval_secs = telemetry_span_secs / max(TELEMETRY_PER_CYCLE - 1, 1)

            for step in range(TELEMETRY_PER_CYCLE):
                frac = step / max(TELEMETRY_PER_CYCLE - 1, 1)

                wear = _lerp(wear_start, wear_end, frac) + _noise(1.5)
                torq = _lerp(torque_start, torque_end, frac) + _noise(0.5)
                rpm = int(_lerp(rpm_start, rpm_end, frac)) + int(_noise(15))
                air = _lerp(air_start, air_end, frac) + _noise(0.3)
                proc = air + 10.0 + _noise(0.2)

                wear = max(0.0, min(300.0, wear))
                torq = max(1.0, min(100.0, torq))
                rpm = max(500, min(3000, rpm))
                air = max(290.0, min(320.0, air))
                proc = max(295.0, min(330.0, proc))

                recorded_at = c_start + timedelta(seconds=step * step_interval_secs)

                db.add(
                    MachineTelemetry(
                        machine_id=TARGET_MACHINE_ID,
                        work_order_id=ot.id,
                        technician_id=technicien.id,
                        air_temperature=round(air, 2),
                        process_temperature=round(proc, 2),
                        rotational_speed=rpm,
                        torque=round(torq, 2),
                        tool_wear=round(wear, 2),
                        recorded_at=recorded_at,
                        notes=f"Seed C{cycle_num:02d} step {step + 1}/{TELEMETRY_PER_CYCLE}",
                    )
                )
                await db.flush()

                f_prob = _failure_prob(wear)
                db.add(
                    MlPredictionLog(
                        machine_id=TARGET_MACHINE_ID,
                        machine_name=machine.nom,
                        risk_level=_risk_level(f_prob),
                        failure_probability=round(f_prob, 2),
                        rul_days=round(max(0.0, (240.0 - wear) / 2.0), 1),
                        predicted_priority="P1" if f_prob > 75 else "P2",
                        is_anomaly=wear > 170,
                        anomaly_score=round(max(0.0, (wear - 80.0) / 160.0), 4),
                        air_temperature=round(air, 2),
                        process_temperature=round(proc, 2),
                        rotational_speed=rpm,
                        torque=round(torq, 2),
                        tool_wear=int(wear),
                        ml_model_used=False,
                        created_at=recorded_at,
                    )
                )

            await db.flush()

        await db.commit()

        stable_wos = sum(v for k, v in failure_type_counts.items() if k == "NONE")
        problem_wos = NUM_CYCLES - stable_wos
        logger.info("")
        logger.info("=" * 60)
        logger.info(
            f"Done. {NUM_CYCLES} cycles seeded for machine_id={TARGET_MACHINE_ID}."
        )
        logger.info(f"  {NUM_CYCLES} Work Orders (CLOSED)")
        logger.info(f"  {NUM_CYCLES} Plannings | {NUM_CYCLES * 2} PlanningTaches")
        logger.info(f"  {NUM_CYCLES} ITVs (TERMINEE)")
        logger.info(f"  {NUM_CYCLES * TELEMETRY_PER_CYCLE} MachineTelemetry rows")
        logger.info(f"  {NUM_CYCLES * TELEMETRY_PER_CYCLE} MlPredictionLog shadow rows")
        logger.info(f"  Stable WOs (NONE): {stable_wos} | Problem WOs: {problem_wos}")
        logger.info(f"  Failure type distribution: {failure_type_counts}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Open localhost:3000/machines/13 → sensors + failure prob")
        logger.info("  2. POST /api/v1/ml/retrain → models retrained")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
