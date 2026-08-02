"""
seed_demo_staging.py — realistic demo seed for the eam-staging AKS database.

Unlike seed_ml_data_all.py / seed_ml_data_healthy.py (which INSERT terminal-state
rows directly and therefore produce states the real app can never create), this
script drives the application's real workflow endpoints in-process:

    Planning (APPROVED)
      -> create_intervention_from_planning       ITV: PENDING
      -> validate_intervention                   ITV: APPROVED
      -> create_work_order_from_intervention     ITV: CONVERTED_TO_WORKORDER, WO: ASSIGNED
      -> start_work_order                        ITV: EN_COURS,  WO: IN_PROGRESS
      -> complete_work_order (PDCA payload)      ITV: TERMINÉ,   WO: COMPLETED
      -> complete_validation_ordres_intervention ITV: VALIDATED
      -> validate_OrdresTravail(action=VALIDATE) WO: VALIDATED
      -> close_OrdresTravail                     WO: CLOSED

Every hook fires for real (audit log, notifications, inventory reservations,
P4/P7 ML feedback, post-maintenance health snapshots). Those route functions
hardcode datetime.now(), so each finished cycle is backdated afterwards by an
explicit UPDATE pass — the state machine is real, only the clock is rewritten.
Audit-log rows are deliberately NOT backdated and keep their real timestamps.

Run inside the eam-staging backend pod:
    kubectl exec -n eam-staging deployment/backend -- python seed_demo_staging.py
    kubectl exec -n eam-staging deployment/backend -- python seed_demo_staging.py --force
"""

import argparse
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEMO_PASSWORD = "DemoStaging2026!"
HISTORY_DAYS = 30
RNG_SEED = 20260802

# Health mix across the fleet (user decision): 50% healthy, 30% at-risk, 20% critical.
HEALTH_MIX = {"healthy": 0.50, "at_risk": 0.30, "critical": 0.20}

# Sagemcom Ezzahra-style production zones.
MACHINE_CATALOG = [
    {"nom": f"CMS{line} - Pick & Place {idx}", "type": "CMS",
     "zone": "Zone CMS", "sous_zone": f"Ligne {line}", "emplacement": "Atelier 1"}
    for line in (1, 2, 3) for idx in (1, 2)
] + [
    {"nom": f"CMS{line} - Four de Refusion", "type": "Four",
     "zone": "Zone CMS", "sous_zone": f"Ligne {line}", "emplacement": "Atelier 1"}
    for line in (1, 2, 3)
] + [
    {"nom": f"CMS{line} - AOI 3D", "type": "Inspection",
     "zone": "Zone CMS", "sous_zone": f"Ligne {line}", "emplacement": "Atelier 1"}
    for line in (1, 2, 3)
] + [
    {"nom": f"Test Fonctionnel - Banc {idx}", "type": "Banc de test",
     "zone": "Zone Test", "sous_zone": "Test Fonctionnel", "emplacement": "Atelier 2"}
    for idx in range(1, 7)
] + [
    {"nom": f"Test WiFi - Banc {idx}", "type": "Banc de test",
     "zone": "Zone Test", "sous_zone": "Test WiFi", "emplacement": "Atelier 2"}
    for idx in range(1, 5)
] + [
    {"nom": f"Assemblage - Poste {idx}", "type": "Assemblage",
     "zone": "Zone Assemblage", "sous_zone": "Montage final", "emplacement": "Atelier 3"}
    for idx in range(1, 7)
] + [
    {"nom": f"Conditionnement - Ligne {idx}", "type": "Conditionnement",
     "zone": "Zone Emballage", "sous_zone": "Packaging", "emplacement": "Atelier 3"}
    for idx in range(1, 5)
] + [
    {"nom": "Compresseur Central", "type": "Utilité",
     "zone": "Zone Utilités", "sous_zone": "Air comprimé", "emplacement": "Local technique"},
    {"nom": "Groupe Froid", "type": "Utilité",
     "zone": "Zone Utilités", "sous_zone": "Refroidissement", "emplacement": "Local technique"},
]

USER_CATALOG = [
    {"nom": "Sonia Gharbi", "email": "sonia.gharbi@demo.local", "role": "ADMIN"},
    {"nom": "Mohamed Aloui", "email": "mohamed.aloui@demo.local", "role": "CHEFTECH"},
    {"nom": "Leila Ben Salah", "email": "leila.bensalah@demo.local", "role": "CHEFTECH"},
    {"nom": "Karim Trabelsi", "email": "karim.trabelsi@demo.local", "role": "CHETOP"},
    {"nom": "Nadia Jelassi", "email": "nadia.jelassi@demo.local", "role": "CHETOP"},
    {"nom": "Hichem Bouzid", "email": "hichem.bouzid@demo.local", "role": "CHETOP"},
    {"nom": "Youssef Mejri", "email": "youssef.mejri@demo.local", "role": "TECHNICIEN"},
    {"nom": "Amine Chaabane", "email": "amine.chaabane@demo.local", "role": "TECHNICIEN"},
    {"nom": "Rania Khelifi", "email": "rania.khelifi@demo.local", "role": "TECHNICIEN"},
    {"nom": "Bilel Hamdi", "email": "bilel.hamdi@demo.local", "role": "TECHNICIEN"},
    {"nom": "Ines Zouari", "email": "ines.zouari@demo.local", "role": "TECHNICIEN"},
    {"nom": "Walid Nasri", "email": "walid.nasri@demo.local", "role": "TECHNICIEN"},
    {"nom": "Sami Ferchichi", "email": "sami.ferchichi@demo.local", "role": "TECHNICIEN"},
    {"nom": "Olfa Mansouri", "email": "olfa.mansouri@demo.local", "role": "TECHNICIEN"},
]

PIECE_CATALOG = [
    {"reference": "BRG-6204", "name": "Roulement 6204", "category": "Mécanique",
     "unit_price": 12.5, "min_stock": 10, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "BLT-A45", "name": "Courroie A45", "category": "Mécanique",
     "unit_price": 22.0, "min_stock": 6, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "NOZ-SMT-05", "name": "Buse SMT 0.5mm", "category": "CMS",
     "unit_price": 48.0, "min_stock": 12, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "FEED-8MM", "name": "Feeder 8mm", "category": "CMS",
     "unit_price": 310.0, "min_stock": 4, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "THERMO-K", "name": "Thermocouple type K", "category": "Électrique",
     "unit_price": 35.0, "min_stock": 8, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "FUSE-10A", "name": "Fusible 10A", "category": "Électrique",
     "unit_price": 2.0, "min_stock": 40, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "RELAY-24V", "name": "Relais 24V", "category": "Électrique",
     "unit_price": 18.0, "min_stock": 10, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "FILT-AIR", "name": "Filtre à air", "category": "Utilité",
     "unit_price": 27.0, "min_stock": 8, "is_consumable": False, "default_unit": "pcs"},
    {"reference": "OIL-ISO46", "name": "Huile ISO VG46", "category": "Consommable",
     "unit_price": 6.5, "min_stock": 30, "is_consumable": True, "default_unit": "L"},
    {"reference": "GREASE-EP2", "name": "Graisse EP2", "category": "Consommable",
     "unit_price": 9.0, "min_stock": 20, "is_consumable": True, "default_unit": "kg"},
    {"reference": "SOLDER-PASTE", "name": "Pâte à souder SAC305", "category": "Consommable",
     "unit_price": 85.0, "min_stock": 15, "is_consumable": True, "default_unit": "kg"},
    {"reference": "IPA-CLEAN", "name": "Alcool isopropylique", "category": "Consommable",
     "unit_price": 4.5, "min_stock": 25, "is_consumable": True, "default_unit": "L"},
]

FAILURE_PROFILES = {
    "critical": {
        "failure_types": ["TWF", "HDF"], "priority": "URGENTE",
        "itv_type": "Corrective", "root_cause": "Mechanical",
        "problems": ["Arrêt machine - vibration excessive",
                     "Surchauffe détectée sur l'axe principal"],
        "status_after": "EN_PANNE", "resolved": False,
    },
    "at_risk": {
        "failure_types": ["PWF", "OSF"], "priority": "ÉLEVÉE",
        "itv_type": "Preventive", "root_cause": "Mechanical",
        "problems": ["Usure outil au-delà du seuil",
                     "Dérive des paramètres process"],
        "status_after": "OPERATIONNELLE", "resolved": True,
    },
    "healthy": {
        "failure_types": ["NONE", "RNF"], "priority": "MOYENNE",
        "itv_type": "Preventive", "root_cause": "Unknown",
        "problems": ["Maintenance préventive planifiée",
                     "Contrôle périodique et lubrification"],
        "status_after": "OPERATIONNELLE", "resolved": True,
    },
}

# Sensor bands grounded in ai4i2020.csv's full-dataset mean/std, so seeded
# readings sit inside the distribution the P1-P6 models were trained on.
SENSOR_BANDS = {
    "healthy":  {"air": (299.0, 301.0), "rpm": (1450, 1650), "torque": (32, 46), "wear": (5, 80)},
    "at_risk":  {"air": (300.5, 303.0), "rpm": (1330, 1500), "torque": (44, 58), "wear": (90, 165)},
    "critical": {"air": (302.0, 306.0), "rpm": (1180, 1380), "torque": (55, 72), "wear": (170, 240)},
}


# ── Foundation rows ──────────────────────────────────────────────────────────
# Plain reference data with no workflow state machine, so inserted directly via
# the ORM — unlike the intervention/work-order chain, which is all transitions.


async def seed_users(db, rng) -> dict:
    """Create the maintenance org. All APPROVED so they can act immediately."""
    from core.auth import get_password_hash
    from models.utilisateurs import UserRole, UserShiftType, Utilisateurs
    from sqlalchemy import select

    by_role: dict = {"ADMIN": [], "CHEFTECH": [], "CHETOP": [], "TECHNICIEN": []}
    hashed = get_password_hash(DEMO_PASSWORD)

    for spec in USER_CATALOG:
        existing = (await db.execute(
            select(Utilisateurs).where(Utilisateurs.email == spec["email"])
        )).scalar_one_or_none()
        if existing:
            by_role[spec["role"]].append(existing)
            continue
        user = Utilisateurs(
            nom=spec["nom"],
            email=spec["email"],
            mot_de_passe=hashed,
            role=UserRole(spec["role"]),
            status="APPROVED",
            shift_type=rng.choice([UserShiftType.MORNING, UserShiftType.NIGHT]),
        )
        db.add(user)
        by_role[spec["role"]].append(user)

    await db.flush()
    logger.info("Users: %s", {k: len(v) for k, v in by_role.items()})
    return by_role


async def seed_machines(db, rng, limit: int) -> list:
    """Create the machine fleet. statut reflects the health mix decided up front."""
    from models.machines import Machines

    now = datetime.now(timezone.utc)
    specs = MACHINE_CATALOG[:limit]
    n_critical = int(len(specs) * HEALTH_MIX["critical"])
    n_at_risk = int(len(specs) * HEALTH_MIX["at_risk"])

    indices = list(range(len(specs)))
    rng.shuffle(indices)
    critical_idx = set(indices[:n_critical])
    at_risk_idx = set(indices[n_critical:n_critical + n_at_risk])

    machines = []
    for i, spec in enumerate(specs):
        if i in critical_idx:
            statut, health = "EN_PANNE", "critical"
        elif i in at_risk_idx:
            statut, health = "MAINTENANCE", "at_risk"
        else:
            statut, health = "OPERATIONNELLE", "healthy"

        machine = Machines(
            nom=spec["nom"],
            type=spec["type"],
            zone=spec["zone"],
            sous_zone=spec["sous_zone"],
            emplacement=spec["emplacement"],
            statut=statut,
            date_derniere_maintenance=now - timedelta(days=rng.randint(3, 45)),
            date_prochaine_maintenance=now + timedelta(days=rng.randint(5, 60)),
            created_at=now - timedelta(days=rng.randint(200, 400)),
        )
        machine._demo_health = health  # transient marker, not a mapped column
        db.add(machine)
        machines.append(machine)

    await db.flush()
    logger.info(
        "Machines: %s total (%s critical, %s at-risk, %s healthy)",
        len(machines), n_critical, n_at_risk, len(machines) - n_critical - n_at_risk,
    )
    return machines


async def seed_pieces_and_stock(db, rng) -> list:
    """Create the spare-parts catalog with stock levels.

    Some rows are deliberately seeded BELOW min_stock so the P7 parts-shortage
    surfaces have something real to flag in the demo."""
    from decimal import Decimal
    from models.pieces import Piece
    from models.stock import Stock

    pieces = []
    for spec in PIECE_CATALOG:
        piece = Piece(**spec)
        db.add(piece)
        pieces.append(piece)
    await db.flush()

    short_idx = set(rng.sample(range(len(pieces)), k=max(2, len(pieces) // 4)))
    for i, piece in enumerate(pieces):
        if i in short_idx:
            qty = Decimal(rng.randint(0, max(1, (piece.min_stock or 5) - 1)))
        else:
            qty = Decimal(rng.randint((piece.min_stock or 5) + 5, (piece.min_stock or 5) * 4))
        db.add(Stock(piece_id=piece.id, quantity=qty))

    await db.flush()
    logger.info("Pieces: %s (%s below min_stock)", len(pieces), len(short_idx))
    return pieces


async def seed_plannings(db, rng, users, machines, history_days: int) -> list:
    """One APPROVED maintenance planning per week of history, per zone.

    APPROVED is required — create_intervention_from_planning rejects anything else.
    Bridge rows (PlanningMachines / PlanningUtilisateurs) are what the permission
    check and the UI's team view both read."""
    from models.plannings import Plannings, PlanningStatut, PlanningType
    from models.planning_machines import PlanningMachines
    from models.planning_utilisateurs import PlanningUtilisateurs

    now = datetime.now(timezone.utc)
    zones = sorted({m.zone for m in machines if m.zone})
    n_weeks = max(1, history_days // 7)
    plannings = []

    for week in range(n_weeks):
        week_start = now - timedelta(days=history_days - week * 7)
        week_end = week_start + timedelta(days=7)
        for zone in zones:
            cheftech = rng.choice(users["CHEFTECH"])
            chetop = rng.choice(users["CHETOP"])
            planning = Plannings(
                identifiant_planning=f"PLAN-S{week + 1:02d}-{zone.replace(' ', '')}",
                date_debut=week_start,
                date_fin=week_end,
                type=PlanningType.HEBDOMADAIRE,
                planning_statut=PlanningStatut.APPROVED,
                chef_operation_id=chetop.id,
                chef_technique_id=cheftech.id,
                zone_travail=zone,
                created_at=week_start - timedelta(days=2),
            )
            db.add(planning)
            await db.flush()

            zone_machines = [m for m in machines if m.zone == zone]
            for machine in zone_machines:
                db.add(PlanningMachines(
                    planning_id=planning.id, machine_id=machine.id, created_at=week_start
                ))

            crew = rng.sample(users["TECHNICIEN"], k=min(3, len(users["TECHNICIEN"])))
            for tech in crew + [cheftech]:
                db.add(PlanningUtilisateurs(
                    planning_id=planning.id, utilisateur_id=tech.id, created_at=week_start
                ))

            planning._demo_crew = crew          # transient, not mapped
            planning._demo_cheftech = cheftech  # transient, not mapped
            planning._demo_chetop = chetop      # transient, not mapped
            planning._demo_machines = zone_machines
            plannings.append(planning)

    await db.flush()
    logger.info("Plannings: %s (%s weeks x %s zones)", len(plannings), n_weeks, len(zones))
    return plannings


# ── The real workflow chain ──────────────────────────────────────────────────


async def _backdate_cycle(db, intervention_id: int, work_order_id: int, cycle_start, cycle_end):
    """Rewrite this cycle's timestamps.

    The route functions hardcode datetime.now(), so every row they wrote carries
    today's date. The state machine they produced is genuine; only the clock
    needs correcting so the demo shows real history."""
    from sqlalchemy import text

    mid = cycle_start + (cycle_end - cycle_start) / 2
    await db.execute(
        text("""
            UPDATE "OrdresIntervention"
               SET date_intervention = :end_ts, requested_at = :start_ts,
                   approved_at = :mid_ts, date_debut = :mid_ts, date_fin = :end_ts,
                   created_at = :start_ts, updated_at = :end_ts
             WHERE id = :id
        """),
        {"id": intervention_id, "start_ts": cycle_start, "mid_ts": mid, "end_ts": cycle_end},
    )
    await db.execute(
        text("""
            UPDATE "OrdresTravail"
               SET created_at = :start_ts, date_validation = :end_ts, date_debut = :mid_ts,
                   date_fin = :end_ts, updated_at = :end_ts, date_echeance = :due_ts
             WHERE id = :id
        """),
        {"id": work_order_id, "start_ts": cycle_start, "mid_ts": mid, "end_ts": cycle_end,
         "due_ts": cycle_end + timedelta(days=2)},
    )


async def run_lifecycle_cycle(db, rng, planning, machine, tech, cheftech, admin,
                              cycle_start, cycle_end) -> tuple:
    """Drive one full maintenance cycle through the REAL endpoints, then backdate."""
    from sqlalchemy import text

    from modules.shared.routes.intervention_workflow import (
        create_intervention_from_planning,
        create_work_order_from_intervention,
        validate_intervention,
    )
    from modules.shared.routes.ordres_intervention.schemas import (
        OrdresInterventionValidationData,
    )
    from modules.shared.routes.ordres_intervention.validation import (
        complete_validation_ordres_intervention,
    )
    from modules.shared.routes.ordres_travail.schemas import OrdresTravailValidationData
    from modules.shared.routes.ordres_travail.validation import (
        close_OrdresTravail,
        validate_OrdresTravail,
    )
    from modules.technicien.technicien_work_orders import (
        WorkOrderCompletePayload,
        complete_work_order,
        start_work_order,
    )

    profile = FAILURE_PROFILES[getattr(machine, "_demo_health", "healthy")]
    failure_type = rng.choice(profile["failure_types"])
    problem = rng.choice(profile["problems"])

    # 1. ITV created from planning (statut: PENDING). CHEFTECH owns the planning.
    itv = await create_intervention_from_planning(
        planning_id=planning.id, machine_id=machine.id, problem_description=problem,
        priority=profile["priority"], estimated_duration_minutes=rng.choice([30, 60, 90, 120]),
        required_materials=None, current_user=cheftech, db=db,
    )

    # 2. CHEFTECH validates the request (statut: APPROVED).
    await validate_intervention(
        intervention_id=itv.id,
        data=OrdresInterventionValidationData(action="APPROVE", technicien_id=tech.id),
        current_user=cheftech, db=db,
    )

    # 3. WO created from the approved ITV (WO: ASSIGNED, ITV: CONVERTED_TO_WORKORDER).
    wo = await create_work_order_from_intervention(
        intervention_id=itv.id, technician_id=tech.id, current_user=cheftech, db=db,
    )

    # 4. Technician starts (WO: IN_PROGRESS, ITV: EN_COURS).
    await start_work_order(order_id=wo.id, current_user=tech, db=db)

    # 5. Technician completes with the full PDCA form (WO: COMPLETED, ITV: TERMINÉ).
    #    This is the call that fills every PDCA field and fires P4/P7 ML feedback.
    payload = WorkOrderCompletePayload(
        rapport=f"Intervention réalisée sur {machine.nom}. {problem} — traité.",
        intervention_type=profile["itv_type"],
        root_cause_category=profile["root_cause"],
        root_cause_description=f"Analyse: {problem.lower()} confirmé au diagnostic.",
        actions_performed="Diagnostic, remplacement pièce défectueuse, essai de fonctionnement.",
        parts_replaced=rng.choice([p["name"] for p in PIECE_CATALOG]),
        tools_used="Clé dynamométrique, multimètre, caméra thermique",
        machine_status_after=profile["status_after"],
        plan_hypothesis=f"Hypothèse initiale: dérive liée à {profile['root_cause'].lower()}.",
        check_resolved=profile["resolved"],
        check_verification_method="Test run",
        act_preventive_actions="Renforcer la fréquence de contrôle sur ce sous-ensemble.",
        act_recommendations="Prévoir le remplacement préventif au prochain arrêt planifié.",
        ml_prediction_matched=rng.choice([True, False]),
    )
    await complete_work_order(order_id=wo.id, payload=payload, current_user=tech, db=db)

    # 6. Diagnosis is required before the ITV can be validated.
    await db.execute(
        text('UPDATE "OrdresIntervention" SET actual_failure_type = :ft WHERE id = :id'),
        {"id": itv.id, "ft": failure_type},
    )
    await db.commit()

    # 7. CHEFTECH validates the finished intervention (ITV: VALIDATED).
    await complete_validation_ordres_intervention(id=itv.id, db=db, current_user=cheftech)

    # 8. CHEFTECH validates the finished WO (WO: VALIDATED) — action added in Task 1.
    await validate_OrdresTravail(
        id=wo.id, data=OrdresTravailValidationData(action="VALIDATE"),
        db=db, current_user=cheftech,
    )

    # 9. ADMIN closes it (WO: CLOSED).
    await close_OrdresTravail(id=wo.id, db=db, current_user=admin)

    await _backdate_cycle(db, itv.id, wo.id, cycle_start, cycle_end)
    await db.commit()
    return itv.id, wo.id


async def seed_lifecycles(db, rng, users, plannings, history_days: int) -> list:
    """Run one completed maintenance cycle per machine per planning week.

    Not every machine gets a cycle every week — rng.random() gates it so the
    history looks uneven, like real maintenance activity."""
    admin = users["ADMIN"][0]
    results = []
    failures = 0

    for planning in plannings:
        cheftech = planning._demo_cheftech
        crew = planning._demo_crew
        for machine in planning._demo_machines:
            health = getattr(machine, "_demo_health", "healthy")
            chance = {"critical": 0.75, "at_risk": 0.45, "healthy": 0.20}[health]
            if rng.random() > chance:
                continue

            span_start = planning.date_debut + timedelta(hours=rng.randint(1, 60))
            span_end = span_start + timedelta(hours=rng.randint(2, 20))
            if span_end >= planning.date_fin:
                span_end = planning.date_fin - timedelta(hours=1)

            tech = rng.choice(crew)
            try:
                ids = await run_lifecycle_cycle(
                    db, rng, planning, machine, tech, cheftech, admin, span_start, span_end,
                )
                results.append(ids)
            except Exception as exc:
                await db.rollback()
                failures += 1
                logger.warning("Cycle failed for machine %s in %s: %s",
                               machine.nom, planning.identifiant_planning, exc)

    logger.info("Completed lifecycles: %s work orders driven end-to-end (%s failed)",
                len(results), failures)
    return results


# ── Telemetry ────────────────────────────────────────────────────────────────


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


async def seed_telemetry(db, rng, machines, history_days: int) -> int:
    """Sensor history + shadow ML-prediction logs, ~4 readings per machine per day.

    is_synthetic=True is deliberate: it keeps this demo data out of ML retrain
    ground truth. The ML READ path is gated separately by the
    ML_ALLOW_SYNTHETIC_TELEMETRY env var, flipped to true for eam-staging so the
    dashboards actually render these readings."""
    from models.machine_telemetry import MachineTelemetry
    from models.ml_prediction_log import MlPredictionLog

    now = datetime.now(timezone.utc)
    readings_per_machine = history_days * 4
    total = 0

    for machine in machines:
        band = SENSOR_BANDS[getattr(machine, "_demo_health", "healthy")]
        wear_lo, wear_hi = band["wear"]
        for step in range(readings_per_machine):
            frac = step / max(readings_per_machine - 1, 1)
            recorded_at = now - timedelta(days=history_days) + timedelta(
                hours=step * (history_days * 24 / readings_per_machine)
            )
            wear = wear_lo + (wear_hi - wear_lo) * frac + rng.gauss(0, 3)
            wear = max(0.0, min(250.0, wear))
            air = rng.uniform(*band["air"]) + rng.gauss(0, 0.3)
            proc = air + 10.0 + rng.gauss(0, 0.4)
            rpm = int(rng.uniform(*band["rpm"]) + rng.gauss(0, 25))
            torque = rng.uniform(*band["torque"]) + rng.gauss(0, 1.5)

            db.add(MachineTelemetry(
                machine_id=machine.id, air_temperature=round(air, 2),
                process_temperature=round(proc, 2), rotational_speed=rpm,
                torque=round(torque, 2), tool_wear=round(wear, 2),
                recorded_at=recorded_at, notes="Demo seed telemetry",
                is_synthetic=True,
            ))

            prob = _failure_prob(wear)
            db.add(MlPredictionLog(
                machine_id=machine.id, machine_name=machine.nom,
                risk_level=_risk_level(prob), failure_probability=round(prob, 2),
                rul_days=round(max(0.0, (240.0 - wear) / 2.2), 1),
                predicted_priority="P1" if prob > 75 else "P2",
                is_anomaly=wear > 180, anomaly_score=round(max(0.0, (wear - 100.0) / 140.0), 4),
                air_temperature=round(air, 2), process_temperature=round(proc, 2),
                rotational_speed=rpm, torque=round(torque, 2), tool_wear=int(wear),
                ml_model_used=False, created_at=recorded_at, is_synthetic=True,
            ))
            total += 2
        await db.flush()

    await db.commit()
    logger.info("Telemetry: %s rows across %s machines", total, len(machines))
    return total


# ── Driver ───────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="Seed realistic demo data into eam-staging.")
    parser.add_argument("--force", action="store_true",
                        help="Seed even if machines already exist (does NOT delete existing rows)")
    parser.add_argument("--machines", type=int, default=len(MACHINE_CATALOG),
                        help=f"How many machines to create (default: {len(MACHINE_CATALOG)})")
    parser.add_argument("--history-days", type=int, default=HISTORY_DAYS,
                        help=f"Days of history to backdate across (default: {HISTORY_DAYS})")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    rng = random.Random(RNG_SEED)
    from core.database import db_manager

    await db_manager.init_db()
    async with db_manager.async_session_maker() as db:
        from sqlalchemy import func, select
        from models.machines import Machines

        existing = (await db.execute(select(func.count(Machines.id)))).scalar() or 0
        if existing and not args.force:
            logger.error(
                "Refusing to seed: %s machines already exist. Re-run with --force "
                "if you really want to add more on top.", existing
            )
            return

        logger.info("Seeding %s machines, %s days of history...", args.machines, args.history_days)

        users = await seed_users(db, rng)
        machines = await seed_machines(db, rng, args.machines)
        pieces = await seed_pieces_and_stock(db, rng)
        plannings = await seed_plannings(db, rng, users, machines, args.history_days)
        await db.commit()
        logger.info("Foundation committed: %s users, %s machines, %s pieces, %s plannings",
                    sum(len(v) for v in users.values()), len(machines), len(pieces),
                    len(plannings))

        cycles = await seed_lifecycles(db, rng, users, plannings, args.history_days)
        logger.info("Lifecycle seeding complete: %s cycles", len(cycles))

        await seed_telemetry(db, rng, machines, args.history_days)
        logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
