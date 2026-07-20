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

from models.ordres_intervention import OrdresIntervention
from models.machines import Machines


_SHAP_FRIENDLY = {
    "Air temperature [K]": "Température Ambiante",
    "Process temperature [K]": "Température du Processus",
    "Rotational speed [rpm]": "Vitesse de Rotation",
    "Torque [Nm]": "Couple (Torque)",
    "Tool wear [min]": "Usure de l'Outil",
}


class RULCalculator:
    @staticmethod
    def _extract_telemetry(entries: list) -> tuple:
        """
        Return (air_temp, process_temp, rpm, torque, tool_wear) from the last
        entry, or all-None when there is no telemetry.

        No placeholder defaults on purpose: substituting nominal readings makes
        a machine with zero sensor history indistinguishable from a healthy one.
        """
        if not entries:
            return None, None, None, None, None
        latest = entries[-1]
        return (
            float(latest.air_temperature),
            float(latest.process_temperature),
            int(latest.rotational_speed),
            float(latest.torque),
            float(latest.tool_wear),
        )

    @staticmethod
    def _deg_rate(entries: list, attr: str) -> float:
        if len(entries) < 2:
            return 0.0
        return (float(getattr(entries[-1], attr)) - float(getattr(entries[0], attr))) / (len(entries) - 1)

    @staticmethod
    def _extract_fusion_fields(fusion_result: Optional[Dict]) -> tuple:
        """Return (ml_probability, model_rul, is_anomaly, anomaly_score, priority_ml, failure_types, shap_exps, rul_interval)."""
        if not fusion_result:
            return 0.0, None, False, 0.0, None, {}, [], None
        return (
            float(fusion_result.get("p1_failure_probability", 0.0)),
            fusion_result.get("p3_rul_days"),
            bool(fusion_result.get("p4_is_anomaly", False)),
            float(fusion_result.get("p4_anomaly_score", 0.0)),
            fusion_result.get("p5_predicted_priority"),
            fusion_result.get("p2_failure_types", {}),
            fusion_result.get("shap_explanations", []),
            fusion_result.get("p3_rul_interval"),
        )

    @staticmethod
    def _scale_rul_interval(rul_interval: Optional[Dict], rul_days: float) -> Optional[Dict]:
        """Rescale the raw model's [p10,p50,p90] spread onto the final,
        blended rul_days actually shown to the user (rul_days is model_rul
        blended with historical MTBF + degradation adjustment — not the raw
        model output the interval was fit against). Applies the model's
        relative spread (as a fraction of its own p50) around the final
        number instead of the raw model's absolute bounds, so a stale/absent
        interval never contradicts the headline RUL figure. None when no
        interval is available (older pkl, not yet retrained with Phase 4.2
        quantile heads) — omitted entirely rather than faked."""
        if not rul_interval:
            return None
        p10, p50, p90 = rul_interval.get("p10"), rul_interval.get("p50"), rul_interval.get("p90")
        if not p50 or p50 <= 0 or p10 is None or p90 is None:
            return None
        low_ratio = max(0.0, min(1.0, (p50 - p10) / p50))
        high_ratio = max(0.0, (p90 - p50) / p50)
        return {
            "low": round(max(0.0, rul_days * (1 - low_ratio)), 1),
            "high": round(rul_days * (1 + high_ratio), 1),
            "confidence": 0.8,
        }

    @staticmethod
    def _compute_deductions(machine: Machines, now_dt: datetime,
                            open_work_orders: int, recent_interventions: int) -> tuple:
        """Return (maint_deduction, overdue_deduction, status_deduction, wo_deduction, ri_deduction, days_since_maint)."""
        maint_date = machine.date_derniere_maintenance
        if maint_date:
            if maint_date.tzinfo is None:
                maint_date = maint_date.replace(tzinfo=timezone.utc)
            days_since_maint = (now_dt - maint_date).days
        else:
            days_since_maint = -1
        maint_deduction = max(0, min(days_since_maint * 0.5, 30)) if days_since_maint > 0 else 0

        overdue_deduction = 0
        next_maint = machine.date_prochaine_maintenance
        if next_maint:
            if next_maint.tzinfo is None:
                next_maint = next_maint.replace(tzinfo=timezone.utc)
            if now_dt > next_maint:
                overdue_deduction = min((now_dt - next_maint).days * 2, 40)

        return (
            maint_deduction,
            overdue_deduction,
            60 if machine.statut in ["EN_PANNE", "HORS_SERVICE"] else 0,
            min(open_work_orders * 12, 36),
            min(recent_interventions * 10, 30),
            days_since_maint,
        )

    @staticmethod
    def _compute_health_score(fusion_result, ml_probability, maint_ded, overdue_ded,
                               status_ded, wo_ded, ri_ded) -> tuple:
        """Return (health_score, score_source, dst_verdict, conflict_k)."""
        if fusion_result and "unified_health_score" in fusion_result:
            return (
                float(fusion_result["unified_health_score"]),
                "dst_fusion",
                fusion_result.get("dst_verdict", "Unknown"),
                float(fusion_result.get("conflict_factor_K", 0.0)),
            )
        score = max(0.0, min(100.0, (100.0 - ml_probability) - (maint_ded + overdue_ded + status_ded + wo_ded + ri_ded)))
        return score, "fallback_additive", None, None

    @staticmethod
    def _compute_kpis(interventions, rul_days, ml_probability, failure_types,
                       ml_health_score, ml_reliability_score) -> tuple:
        """Return (mtbf_hours, mttr_hours, avail_pct, health_score, reliability_score)."""
        if not interventions:
            return 0.0, 0.0, 0.0, 100.0, 100.0
        mttr = 2.5
        for t_name, t_data in failure_types.items():
            if isinstance(t_data, dict) and t_data.get("detected"):
                if t_name in ["HDF", "OSF"]:
                    mttr += 1.5
                if t_name == "TWF":
                    mttr += 0.5
        return (
            rul_days * 24,
            mttr,
            max(0, min(100.0, 100.0 - ml_probability * 0.1)),
            ml_health_score,
            ml_reliability_score,
        )

    @staticmethod
    def _compute_risk_level(ml_probability: float, rul_days: float) -> str:
        if ml_probability >= 70 or rul_days < 7:
            return "CRITICAL"
        if ml_probability >= 50 or rul_days < 15:
            return "HIGH"
        if ml_probability >= 30 or rul_days < 30:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _map_shap(shap_exps: list) -> list:
        return [
            {
                "factor": _SHAP_FRIENDLY.get(e.get("factor", ""), e.get("factor", "")),
                "impact": e.get("impact", 0.0),
                "intensity": e.get("intensity", "low"),
            }
            for e in shap_exps
        ]

    @staticmethod
    def calculate_rul(
        machine: Machines,
        interventions: List[OrdresIntervention],
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
        entries = list(telemetry_entries) if telemetry_entries else []

        air_temp, process_temp, rpm, torque, tool_wear = RULCalculator._extract_telemetry(entries)
        deg_air = RULCalculator._deg_rate(entries, "air_temperature")
        deg_proc = RULCalculator._deg_rate(entries, "process_temperature")
        deg_wear = RULCalculator._deg_rate(entries, "tool_wear")
        deg_magnitude = abs(deg_air) / 10.0 + abs(deg_proc) / 10.0 + abs(deg_wear) / 5.0

        ml_probability, model_rul, is_anomaly, anomaly_score, predicted_priority_ml, failure_types, shap_exps, rul_interval_raw = \
            RULCalculator._extract_fusion_fields(fusion_result)

        hist_mtbf_days = RULCalculator._get_historical_mtbf(interventions)
        rul_days = (float(model_rul) * 0.7 + hist_mtbf_days * 0.3) if model_rul is not None else hist_mtbf_days
        if deg_magnitude > 0:
            rul_days *= max(0.5, 1.0 - min(0.5, deg_magnitude * 0.1))

        maint_ded, overdue_ded, status_ded, wo_ded, ri_ded, days_since_maint = \
            RULCalculator._compute_deductions(machine, now, open_work_orders, recent_interventions)

        ml_health_score, score_source, dst_verdict, conflict_k = \
            RULCalculator._compute_health_score(fusion_result, ml_probability,
                                                 maint_ded, overdue_ded, status_ded, wo_ded, ri_ded)

        reliability_base = min(100, (rul_days / 60) * 100) if rul_days < 60 else 100
        ml_reliability_score = max(0, min(100, reliability_base * (1 - ml_probability / 200)))

        ml_mtbf_hours, ml_mttr_hours, ml_availability_pct, ml_health_score, ml_reliability_score = \
            RULCalculator._compute_kpis(interventions, rul_days, ml_probability,
                                         failure_types, ml_health_score, ml_reliability_score)

        risk_level = RULCalculator._compute_risk_level(ml_probability, rul_days)
        rul_confidence_interval = RULCalculator._scale_rul_interval(rul_interval_raw, rul_days)

        if predicted_priority_ml:
            predicted_priority = str(predicted_priority_ml)
        elif not interventions:
            predicted_priority = "Normal"
        else:
            predicted_priority = risk_level.title()

        response = {
            "machine_id": machine.id,
            "machine_name": machine.nom,
            "rul_days": round(float(max(0, rul_days)), 1),
            "rul_confidence_interval": rul_confidence_interval,
            "risk_level": risk_level,
            "failure_probability": float(ml_probability),
            "predicted_failure_date": (now + timedelta(days=max(0, rul_days))).isoformat(),
            "data_points": len(interventions),
            "ml_model_used": fusion_result is not None,
            "predicted_priority": predicted_priority,
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(float(anomaly_score), 4),
            "explanations": RULCalculator._map_shap(shap_exps),
            "health_score": round(float(ml_health_score), 1) if ml_health_score is not None else None,
            "health_breakdown": {
                "predictive_risk": round(float(ml_probability), 1),
                "score_source": score_source,
                "dst_verdict": dst_verdict,
                "conflict_factor_K": round(float(conflict_k), 4) if conflict_k is not None else None,
                "maintenance_deduction": round(float(maint_ded), 1),
                "overdue_deduction": round(float(overdue_ded), 1),
                "status_deduction": round(float(status_ded), 1),
                "work_order_deduction": round(float(wo_ded), 1),
                "intervention_deduction": round(float(ri_ded), 1),
                "days_since_maintenance": days_since_maint,
                "open_work_orders": open_work_orders,
                "recent_interventions": recent_interventions,
                "degradation_rate_air": round(float(deg_air), 4),
                "degradation_rate_wear": round(float(deg_wear), 4),
                "degradation_magnitude": round(float(deg_magnitude), 4),
            },
            "reliability_score": round(float(ml_reliability_score), 1) if ml_reliability_score is not None else 0.0,
            "mtbf_pred": round(float(ml_mtbf_hours), 1),
            "mttr_pred": round(float(ml_mttr_hours), 1),
            "availability_pred": round(float(ml_availability_pct), 1) if ml_availability_pct is not None else 0.0,
            "air_temperature": round(float(air_temp), 2) if air_temp is not None else None,
            "process_temperature": round(float(process_temp), 2) if process_temp is not None else None,
            "rotational_speed": int(rpm) if rpm is not None else None,
            "torque": round(float(torque), 2) if torque is not None else None,
            "tool_wear": round(float(tool_wear), 2) if tool_wear is not None else None,
            "telemetry_data_points": len(entries),
            "telemetry_available": len(entries) > 0,
        }

        if not fusion_result:
            response["model_unavailable"] = True

        return response

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_historical_mtbf(
        interventions: List[OrdresIntervention],
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
