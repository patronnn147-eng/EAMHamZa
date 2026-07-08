"""
RUL Calculator — Backend business logic for Remaining Useful Life estimation.

All ML inference is delegated to the ml-microservice (via ml_client.predict_all).
When the microservice is unavailable, a pure-formula fallback is used (no local models).

fusion_result keys consumed (from microservice predict_all):
    p1_failure_probability  float  0-100
    p3_rul_days             float  days
    p4_is_anomaly           bool
    p4_anomaly_score        float
    p5_predicted_priority   str
    p2_failure_types        dict
    unified_health_score    float  0-100
    dst_verdict             str
    conflict_factor_K       float
    shap_explanations       list[dict]
"""

import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from models.ordres_intervention import Ordres_intervention
from models.machines import Machines


class RULCalculator:
    @staticmethod
    def calculate_rul(
        machine: Machines,
        interventions: List[Ordres_intervention],
        telemetry_entries=None,  # List[MachineTelemetry] — optional
        open_work_orders: int = 0,
        recent_interventions: int = 0,
        fusion_result: Optional[Dict] = None,
    ) -> Dict:
        """
        Calculate Remaining Useful Life (RUL) and ML-informed KPIs.

        ML inference comes exclusively from fusion_result (ml-microservice).
        When fusion_result is None (microservice down), a formula-only fallback
        is used — degraded accuracy but no silent failures.
        """
        now = datetime.now(timezone.utc)

        # --- Step 1: Telemetry Data Extraction ---
        entries = list(telemetry_entries) if telemetry_entries else []

        if entries:
            latest = entries[-1]
            air_temp = float(latest.air_temperature)
            process_temp = float(latest.process_temperature)
            rpm = int(latest.rotational_speed)
            torque = float(latest.torque)
            tool_wear = float(latest.tool_wear)
        else:
            air_temp, process_temp, rpm, torque, tool_wear = (
                300.0,
                310.0,
                1500,
                40.0,
                0.0,
            )

        # --- Step 1b: Degradation Rate ---
        def _deg_rate(attr: str) -> float:
            if len(entries) < 2:
                return 0.0
            first = float(getattr(entries[0], attr))
            last = float(getattr(entries[-1], attr))
            return (last - first) / (len(entries) - 1)

        deg_air = _deg_rate("air_temperature")
        deg_proc = _deg_rate("process_temperature")
        deg_wear = _deg_rate("tool_wear")

        deg_magnitude = abs(deg_air) / 10.0 + abs(deg_proc) / 10.0 + abs(deg_wear) / 5.0

        # --- Step 2: RUL & Failure Probability from microservice ---
        # Extract ML data from fusion_result when available; formula fallback otherwise.
        if fusion_result:
            ml_probability = float(fusion_result.get("p1_failure_probability", 0.0))
            model_rul = fusion_result.get("p3_rul_days")  # may be None
            is_anomaly = bool(fusion_result.get("p4_is_anomaly", False))
            anomaly_score = float(fusion_result.get("p4_anomaly_score", 0.0))
            predicted_priority_ml = fusion_result.get("p5_predicted_priority")
            failure_types = fusion_result.get("p2_failure_types", {})
            shap_exps = fusion_result.get("shap_explanations", [])
        else:
            # Microservice unavailable — degraded formula-only mode
            ml_probability = 0.0
            model_rul = None
            is_anomaly = False
            anomaly_score = 0.0
            predicted_priority_ml = None
            failure_types = {}
            shap_exps = []

        # Historical MTBF from intervention records
        hist_mtbf_days = RULCalculator._get_historical_mtbf(interventions)

        if model_rul is not None:
            rul_days = (float(model_rul) * 0.7) + (hist_mtbf_days * 0.3)
        else:
            rul_days = hist_mtbf_days

        # Apply degradation rate (cap at 50% reduction)
        if deg_magnitude > 0:
            degradation_factor = max(0.5, 1.0 - min(0.5, deg_magnitude * 0.1))
            rul_days = rul_days * degradation_factor

        # --- Step 3: Operational Deductions ---
        now_dt = datetime.now(timezone.utc)

        maint_date = machine.date_derniere_maintenance
        if maint_date:
            if maint_date.tzinfo is None:
                maint_date = maint_date.replace(tzinfo=timezone.utc)
            days_since_maint = (now_dt - maint_date).days
        else:
            days_since_maint = -1
        maint_deduction = (
            max(0, min(days_since_maint * 0.5, 30)) if days_since_maint > 0 else 0
        )

        overdue_deduction = 0
        next_maint = machine.date_prochaine_maintenance
        if next_maint:
            if next_maint.tzinfo is None:
                next_maint = next_maint.replace(tzinfo=timezone.utc)
            if now_dt > next_maint:
                days_overdue = (now_dt - next_maint).days
                overdue_deduction = min(days_overdue * 2, 40)

        status_deduction = 60 if machine.statut in ["EN_PANNE", "HORS_SERVICE"] else 0
        wo_deduction = min(open_work_orders * 12, 36)
        ri_deduction = min(recent_interventions * 10, 30)

        # --- Step 4: Health Score ---
        if fusion_result and "unified_health_score" in fusion_result:
            ml_health_score = float(fusion_result["unified_health_score"])
            score_source = "dst_fusion"
            dst_verdict = fusion_result.get("dst_verdict", "Unknown")
            conflict_k = float(fusion_result.get("conflict_factor_K", 0.0))
        else:
            predictive_health = 100.0 - ml_probability
            ml_health_score = predictive_health - (
                maint_deduction
                + overdue_deduction
                + status_deduction
                + wo_deduction
                + ri_deduction
            )
            ml_health_score = max(0.0, min(100.0, ml_health_score))
            score_source = "fallback_additive"
            dst_verdict = None
            conflict_k = None

        # --- Step 5: Reliability Score ---
        reliability_base = min(100, (rul_days / 60) * 100) if rul_days < 60 else 100
        ml_reliability_score = max(
            0, min(100, reliability_base * (1 - (ml_probability / 200)))
        )

        # --- Step 6: KPIs & Risk ---
        if len(interventions) == 0:
            ml_mtbf_hours = 0.0
            ml_mttr_hours = 0.0
            ml_availability_pct = 0.0
            ml_health_score = 100.0
            ml_reliability_score = 100.0
        else:
            ml_mtbf_hours = rul_days * 24
            ml_mttr_hours = 2.5
            for t_name, t_data in failure_types.items():
                if isinstance(t_data, dict) and t_data.get("detected"):
                    if t_name in ["HDF", "OSF"]:
                        ml_mttr_hours += 1.5
                    if t_name == "TWF":
                        ml_mttr_hours += 0.5
            ml_availability_pct = max(0, min(100.0, 100.0 - (ml_probability * 0.1)))

        # --- Step 7: Risk Level ---
        if ml_probability >= 70 or rul_days < 7:
            risk_level = "CRITICAL"
        elif ml_probability >= 50 or rul_days < 15:
            risk_level = "HIGH"
        elif ml_probability >= 30 or rul_days < 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Priority from microservice; fallback to risk-derived label
        if predicted_priority_ml:
            predicted_priority = str(predicted_priority_ml)
        elif len(interventions) == 0:
            predicted_priority = "Normal"
        else:
            predicted_priority = risk_level.title()

        # --- Step 8: SHAP Explanations ---
        # Already retrieved from fusion_result; map to friendly French names
        explanations = []
        _FRIENDLY = {
            "Air temperature [K]": "Température Ambiante",
            "Process temperature [K]": "Température du Processus",
            "Rotational speed [rpm]": "Vitesse de Rotation",
            "Torque [Nm]": "Couple (Torque)",
            "Tool wear [min]": "Usure de l'Outil",
        }
        for e in shap_exps:
            explanations.append(
                {
                    "factor": _FRIENDLY.get(e.get("factor", ""), e.get("factor", "")),
                    "impact": e.get("impact", 0.0),
                    "intensity": e.get("intensity", "low"),
                }
            )

        response = {
            "machine_id": machine.id,
            "machine_name": machine.nom,
            "rul_days": round(float(max(0, rul_days)), 1),
            "risk_level": risk_level,
            "failure_probability": float(ml_probability),
            "predicted_failure_date": (
                now + timedelta(days=max(0, rul_days))
            ).isoformat(),
            "data_points": len(interventions),
            "ml_model_used": fusion_result is not None,
            "predicted_priority": predicted_priority,
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(float(anomaly_score), 4),
            "explanations": explanations,
            "health_score": round(float(ml_health_score), 1)
            if ml_health_score is not None
            else None,
            "health_breakdown": {
                "predictive_risk": round(float(ml_probability), 1),
                "score_source": score_source,
                "dst_verdict": dst_verdict,
                "conflict_factor_K": round(float(conflict_k), 4)
                if conflict_k is not None
                else None,
                "maintenance_deduction": round(float(maint_deduction), 1),
                "overdue_deduction": round(float(overdue_deduction), 1),
                "status_deduction": round(float(status_deduction), 1),
                "work_order_deduction": round(float(wo_deduction), 1),
                "intervention_deduction": round(float(ri_deduction), 1),
                "days_since_maintenance": days_since_maint,
                "open_work_orders": open_work_orders,
                "recent_interventions": recent_interventions,
                "degradation_rate_air": round(float(deg_air), 4),
                "degradation_rate_wear": round(float(deg_wear), 4),
                "degradation_magnitude": round(float(deg_magnitude), 4),
            },
            "reliability_score": round(float(ml_reliability_score), 1)
            if ml_reliability_score is not None
            else 0.0,
            "mtbf_pred": round(float(ml_mtbf_hours), 1),
            "mttr_pred": round(float(ml_mttr_hours), 1),
            "availability_pred": round(float(ml_availability_pct), 1)
            if ml_availability_pct is not None
            else 0.0,
            "air_temperature": round(float(air_temp), 2),
            "process_temperature": round(float(process_temp), 2),
            "rotational_speed": int(rpm),
            "torque": round(float(torque), 2),
            "tool_wear": round(float(tool_wear), 2),
            "telemetry_data_points": len(entries),
        }

        if not fusion_result:
            response["model_unavailable"] = True

        return response

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_historical_mtbf(
        interventions: List[Ordres_intervention],
        default_days: Optional[float] = None,
    ) -> float:
        """Calculate Mean Time Between Failures from intervention history."""
        fallback_default = default_days if default_days is not None else 60.0
        if len(interventions) < 2:
            return fallback_default
        raw_dates = [i.date_intervention for i in interventions if i.date_intervention]
        if len(raw_dates) < 2:
            return fallback_default
        dates = sorted(raw_dates)
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        return float(np.mean(gaps)) if gaps else fallback_default
