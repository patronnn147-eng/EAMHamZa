"""
seed_common.py — shared helpers for the seed_ml_data*.py scripts.

Extracted because seed_ml_data.py, seed_ml_data_all.py, seed_ml_data_healthy.py,
and seed_ml_data_m13.py had independently copy-pasted the same curve-interpolation
helpers and (for _all/_healthy) the same per-cycle DB-write pipeline (Planning ->
bridge rows -> PlanningTaches -> ITV -> OT -> link -> telemetry/shadow-log loop).
Behavior-preserving extraction only — no formula or write-order changes.
"""
from datetime import timedelta

from models.machine_telemetry import MachineTelemetry
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail, OrdreStatut
from models.planning_taches import PlanningTaches, TaskType
from models.planning_machines import PlanningMachines
from models.planning_ordres_travail import PlanningOrdresTravail
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings, PlanningStatut, PlanningType


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


async def create_seed_cycle_records(
    db, machine_id: int, cheftech, chetop, technicien, cycle_num: int,
    c_start, c_mid, c_end, itv_requested_at, cfg: dict,
    diag_description: str, corr_description: str, itv_problem_description: str, ot_description: str,
):
    """Steps 1-7 of one seed cycle: Planning -> bridge rows -> PlanningTaches ->
    ITV (ordre_travail_id=None) -> OT -> link ITV->OT -> link Planning->OT.
    Returns (planning, itv, ot)."""
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
    c_start, c_end, wear_clamp: tuple, torque_clamp: tuple, rpm_clamp: tuple,
    air_clamp: tuple, proc_clamp: tuple, priority_fn, notes_suffix: str = "",
):
    """Step 8 of one seed cycle: interpolated telemetry + shadow ML-prediction-log rows."""
    wear_start, wear_end = cfg["tool_wear"]
    torque_start, torque_end = cfg["torque"]
    rpm_start, rpm_end = cfg["rpm"]
    air_start, air_end = cfg["air_temp"]

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
