"""
seed_common.py — shared helpers for the seed_ml_data*.py scripts.

Extracted because seed_ml_data.py, seed_ml_data_all.py, seed_ml_data_healthy.py,
and seed_ml_data_m13.py had independently copy-pasted the same curve-interpolation
helpers and (for _all/_healthy) the same per-cycle DB-write pipeline (Planning ->
bridge rows -> PlanningTaches -> ITV -> OT -> link -> telemetry/shadow-log loop).
Behavior-preserving extraction only — no formula or write-order changes.
"""
import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import delete, func, select

from models.machine_telemetry import MachineTelemetry
from models.machines import Machines
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail, OrdreStatut
from models.planning_taches import PlanningTaches, TaskType
from models.planning_machines import PlanningMachines
from models.planning_ordres_travail import PlanningOrdresTravail
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings, PlanningStatut, PlanningType
from models.utilisateurs import UserRole, UserStatus, Utilisateurs

# Same format as each script's own logging.basicConfig (no %(name)s in the
# format string), so moving these log calls here changes nothing in output.
logger = logging.getLogger(__name__)


def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation. t in [0, 1]."""
    return start + t * (end - start)


def _noise(rng, sigma: float) -> float:
    return rng.gauss(0, sigma)


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


async def clean_seed_data(db, machine_id: int) -> None:
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


async def create_seed_cycle_records(
    db, machine_id: int, cheftech, chetop, technicien, cycle_num: int,
    c_start, c_mid, c_end, itv_requested_at, cfg: dict, descriptions: dict,
):
    """Steps 1-7 of one seed cycle: Planning -> bridge rows -> PlanningTaches ->
    ITV (ordre_travail_id=None) -> OT -> link ITV->OT -> link Planning->OT.

    `descriptions` keys: diag, corr, itv_problem, ot.
    Returns (planning, itv, ot)."""
    diag_description = descriptions["diag"]
    corr_description = descriptions["corr"]
    itv_problem_description = descriptions["itv_problem"]
    ot_description = descriptions["ot"]
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
        description=diag_description,
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
        description=corr_description,
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
        problem_description=itv_problem_description,
    )
    db.add(itv)
    await db.flush()

    # ── Step 5: OT ───────────────────────────────────────────────────────
    ot = OrdresTravail(
        titre=f"OT-SEED-C{cycle_num:02d}-M{machine_id}",
        description=ot_description,
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

    return planning, itv, ot


async def generate_cycle_telemetry(
    db, ot, machine, technicien, cfg: dict, rng, cycle_num: int, telemetry_per_cycle: int,
    c_start, c_end, clamps: dict, priority_fn, notes_suffix: str = "",
):
    """Step 8 of one seed cycle: interpolated telemetry + shadow ML-prediction-log rows.

    `clamps` keys: wear, torque, rpm, air, proc — each a (min, max) tuple."""
    wear_start, wear_end = cfg["tool_wear"]
    torque_start, torque_end = cfg["torque"]
    rpm_start, rpm_end = cfg["rpm"]
    air_start, air_end = cfg["air_temp"]
    wear_clamp, torque_clamp, rpm_clamp, air_clamp, proc_clamp = (
        clamps["wear"], clamps["torque"], clamps["rpm"], clamps["air"], clamps["proc"],
    )

    telemetry_span_secs = (c_end - c_start).total_seconds()
    step_interval_secs = telemetry_span_secs / max(telemetry_per_cycle - 1, 1)

    for step in range(telemetry_per_cycle):
        frac = step / max(telemetry_per_cycle - 1, 1)

        wear = _lerp(wear_start, wear_end, frac) + _noise(rng, 1.5)
        torq = _lerp(torque_start, torque_end, frac) + _noise(rng, 0.5)
        rpm = int(_lerp(rpm_start, rpm_end, frac)) + int(_noise(rng, 15))
        air = _lerp(air_start, air_end, frac) + _noise(rng, 0.3)
        proc = air + 10.0 + _noise(rng, 0.2)

        wear = max(wear_clamp[0], min(wear_clamp[1], wear))
        torq = max(torque_clamp[0], min(torque_clamp[1], torq))
        rpm = max(rpm_clamp[0], min(rpm_clamp[1], rpm))
        air = max(air_clamp[0], min(air_clamp[1], air))
        proc = max(proc_clamp[0], min(proc_clamp[1], proc))

        recorded_at = c_start + timedelta(seconds=step * step_interval_secs)

        telemetry = MachineTelemetry(
            machine_id=machine.id,
            work_order_id=ot.id,
            technician_id=technicien.id,
            air_temperature=round(air, 2),
            process_temperature=round(proc, 2),
            rotational_speed=rpm,
            torque=round(torq, 2),
            tool_wear=round(wear, 2),
            recorded_at=recorded_at,
            notes=f"Seed C{cycle_num:02d} step {step + 1}/{telemetry_per_cycle}{notes_suffix}",
            is_synthetic=True,
        )
        db.add(telemetry)
        await db.flush()

        f_prob = _failure_prob(wear)
        shadow = MlPredictionLog(
            machine_id=machine.id,
            machine_name=machine.nom,
            risk_level=_risk_level(f_prob),
            failure_probability=round(f_prob, 2),
            rul_days=round(max(0.0, (230.0 - wear) / 2.0), 1),
            predicted_priority=priority_fn(f_prob),
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


async def run_seed_driver(
    db_manager, num_cycles: int, clean_mode: bool, machine_ids,
    idempotency_threshold: int, clean_seed_data_fn, seed_machine_fn,
    seeding_label: str = "", mix_label: str = "Failure mix", cycles_label: str = "cycles",
) -> Optional[dict]:
    """Shared driver for seed_ml_data_all.py / seed_ml_data_healthy.py's `seed()`
    entrypoint: fetch machines -> validate prerequisite users -> per-machine
    idempotency-checked seed loop -> summary log. Returns None if the run
    aborted early (no machines / missing prerequisite users), else the summary
    dict (which may legitimately be empty if every machine was already seeded).
    Caller still owns its own "Next steps" log block (content differs per
    script) and should only print it when this returns non-None."""
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        query = select(Machines).order_by(Machines.id)
        if machine_ids:
            query = query.where(Machines.id.in_(machine_ids))
        machines = (await db.execute(query)).scalars().all()
        if not machines:
            logger.error("No matching machines found in DB. Aborting.")
            return None

        logger.info(f"Found {len(machines)} machine(s): {[m.id for m in machines]}")

        async def _get_users(role):
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
            return None

        cheftech = cheftechs[0]
        chetop = chetops[0]

        logger.info(
            f"Users — {len(techniciens)} TECH(s): "
            f"{', '.join(f'{t.nom}(id={t.id})' for t in techniciens)} | "
            f"CHEFTECH: {cheftech.nom} (id={cheftech.id}), "
            f"CHETOP: {chetop.nom} (id={chetop.id})"
        )

        summary = {}
        for machine in machines:
            if clean_mode:
                await clean_seed_data_fn(db, machine.id)
                await db.commit()

            count_result = await db.execute(
                select(func.count(MachineTelemetry.id)).where(
                    MachineTelemetry.machine_id == machine.id
                )
            )
            existing_count = count_result.scalar() or 0
            if existing_count >= idempotency_threshold and not clean_mode:
                logger.info(
                    f"machine_id={machine.id} already has {existing_count} telemetry rows. "
                    "Skipping (use --clean to re-seed)."
                )
                continue

            logger.info(
                f"── Seeding {seeding_label}machine_id={machine.id} ({machine.nom}) "
                f"— {num_cycles} {cycles_label} ──"
            )
            failure_counts = await seed_machine_fn(
                db, machine, techniciens, cheftech, chetop, num_cycles
            )
            await db.commit()
            summary[machine.id] = failure_counts
            logger.info(f"machine_id={machine.id} done. {mix_label}: {failure_counts}")

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Done. Seeded {len(summary)}/{len(machines)} machine(s), {num_cycles} {cycles_label} each.")
        for mid, counts in summary.items():
            logger.info(f"  machine_id={mid}: {counts}")

    return summary
