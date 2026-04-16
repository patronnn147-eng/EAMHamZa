import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from .model_loader import get_model, _ml_model_p4, _ml_model_p2, _ml_model_p5
from .services.ml_xai import XAIService
from .predictions import MachineLearningService


class RULCalculator:

    @staticmethod
    def calculate_rul(
        machine: Machines,
        interventions: List[Ordres_intervention],
        telemetry_entries=None,          # List[MachineTelemetry] — optional
        open_work_orders: int = 0,
        recent_interventions: int = 0,
        fusion_result: Optional[Dict] = None,
    ) -> Dict:
        """
        Calculate Remaining Useful Life (RUL) and ML-informed KPIs.

        Strategy:
          - RUL (P3): predictive remaining life.
          - Health Score: ML-derived condition index.
          - Reliability: predictive stability index.
        """
        now = datetime.now(timezone.utc)

        # --- Step 1: Telemetry Data Extraction ---
        # Use latest entry from history; fall back to hardcoded defaults for new machines
        entries = list(telemetry_entries) if telemetry_entries else []

        if entries:
            latest = entries[-1]
            air_temp     = float(latest.air_temperature)
            process_temp = float(latest.process_temperature)
            rpm          = int(latest.rotational_speed)
            torque       = float(latest.torque)
            tool_wear    = float(latest.tool_wear)
        else:
            air_temp, process_temp, rpm, torque, tool_wear = 300.0, 310.0, 1500, 40.0, 0.0

        temp_delta = float(process_temp) - float(air_temp)
        rpm_torque = (float(rpm) * float(torque)) / 1000.0  # Normalized feature

        # --- Step 1b: Degradation Rate ---
        # (latest - first) / (n - 1) per sensor; 0.0 if single or no entry
        def _deg_rate(attr: str) -> float:
            if len(entries) < 2:
                return 0.0
            first = float(getattr(entries[0], attr))
            last  = float(getattr(entries[-1], attr))
            return (last - first) / (len(entries) - 1)

        deg_air    = _deg_rate("air_temperature")
        deg_proc   = _deg_rate("process_temperature")
        deg_wear   = _deg_rate("tool_wear")

        # Composite degradation magnitude (0 = stable, higher = faster degradation)
        deg_magnitude = (
            abs(deg_air)  / 10.0 +
            abs(deg_proc) / 10.0 +
            abs(deg_wear) / 5.0
        )

        # Feature vectors for different models:
        # P1 (failure): 7 features [air, process, rpm, torque, wear, temp_delta, rpm_torque]
        # P2 (failure type): 6 features [air, process, rpm, torque, wear, temp_delta]
        # P3 (RUL): 5 features [air, process, rpm, torque, wear]
        # P4 (anomaly): 5 features [air, process, rpm, torque, wear]
        # P5 (priority): 6 features [air, process, rpm, torque, wear, temp_delta]
        # P6 (schedule): 6 features [air, process, rpm, torque, wear, temp_delta]
        features_5 = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear)]
        features_6 = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear), temp_delta]
        features_7 = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear), temp_delta, rpm_torque]

        # --- Step 2: RUL Prediction (P3 - 5 features) ---
        hist_mtbf_days = MachineLearningService._get_historical_mtbf(interventions)
        model_rul = MachineLearningService._predict_model_rul(features_5)

        if model_rul is not None:
            rul_days = (model_rul * 0.7) + (hist_mtbf_days * 0.3)
        else:
            rul_days = hist_mtbf_days

        # Apply degradation rate: proportionally shorten RUL (cap at 50% reduction)
        if deg_magnitude > 0:
            degradation_factor = max(0.5, 1.0 - min(0.5, deg_magnitude * 0.1))
            rul_days = rul_days * degradation_factor

        # --- Step 3: Failure Probability (P1 - 7 features) ---
        ml_probability: float = 0.0
        model_p1 = get_model()
        if model_p1 is not None:
            ml_probability = MachineLearningService.predict_failure_probability(features_7)

        # --- Step 4: Anomaly Detection (P4 - 5 features) ---
        is_anomaly = False
        anomaly_score = 0.0
        if _ml_model_p4 is not None:
            is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(features_5)

        # --- Step 5: Operational Deductions (Maintenance, Status, Tickets) ---
        now_dt = datetime.now(timezone.utc)
        
        # 5a. Maintenance Age
        maint_date = machine.date_derniere_maintenance
        if maint_date:
            if maint_date.tzinfo is None:
                maint_date = maint_date.replace(tzinfo=timezone.utc)
            days_since_maint = (now_dt - maint_date).days
        else:
            days_since_maint = -1
            
        maint_deduction = max(0, min(days_since_maint * 0.5, 30)) if days_since_maint > 0 else 0
        
        # 5b. Overdue Maintenance
        overdue_deduction = 0
        next_maint = machine.date_prochaine_maintenance
        if next_maint:
            if next_maint.tzinfo is None:
                next_maint = next_maint.replace(tzinfo=timezone.utc)
            if now_dt > next_maint:
                days_overdue = (now_dt - next_maint).days
                overdue_deduction = min(days_overdue * 2, 40)
        
        # 5c. Machine Status (Down/Stopped)
        status_deduction = 60 if machine.statut in ["EN_PANNE", "HORS_SERVICE"] else 0
        
        # 5d. Work Orders & Recent Interventions
        wo_deduction = min(open_work_orders * 12, 36)
        ri_deduction = min(recent_interventions * 10, 30)

        # --- Step 6: ML-Informed Health Score (0-100) ---
        # NOTE: anomaly_penalty removed — P1 already captures the sensor anomaly state,
        # so adding a separate P4 penalty was double-counting the same signal.
        # The unified_health_score from the DST fusion layer (Wave 2) is the authoritative
        # score when the ML microservice is available; the formula below is the fallback.
        if fusion_result and "unified_health_score" in fusion_result:
            ml_health_score = float(fusion_result["unified_health_score"])
            score_source = "dst_fusion"
            dst_verdict = fusion_result.get("dst_verdict", "Unknown")
            conflict_k = float(fusion_result.get("conflict_factor_K", 0.0))
        else:
            predictive_health = 100.0 - ml_probability
            ml_health_score = predictive_health - (maint_deduction + overdue_deduction + status_deduction + wo_deduction + ri_deduction)
            ml_health_score = max(0.0, min(100.0, ml_health_score))
            score_source = "fallback_additive"
            dst_verdict = None
            conflict_k = None

        # --- Step 7: ML-Informed Reliability Score (0-100) ---
        reliability_base = min(100, (rul_days / 60) * 100) if rul_days < 60 else 100
        ml_reliability_score = max(0, min(100, reliability_base * (1 - (ml_probability / 200))))

        # --- Step 7: Predicted KPIs (MTBF, MTTR, Availability) ---
        if len(interventions) == 0:
            ml_mtbf_hours = 0.0
            ml_mttr_hours = 0.0
            ml_availability_pct = 0.0
            ml_health_score = 100.0
            ml_reliability_score = 100.0
            risk_level = "LOW"
            predicted_priority = "Normal"
        else:
            ml_mtbf_hours = rul_days * 24
            ml_mttr_hours = 2.5
            if _ml_model_p2 is not None:
                types = MachineLearningService.predict_failure_type(features_6)
                for t_name, t_data in types.items():
                    if t_data["detected"]:
                        if t_name in ["HDF", "OSF"]: ml_mttr_hours += 1.5
                        if t_name == "TWF": ml_mttr_hours += 0.5
            ml_availability_pct = max(0, min(100.0, 100.0 - (ml_probability * 0.1)))

        # --- Step 8: Risk Level & Priority (P5 - 5 features) ---
        if ml_probability >= 70 or rul_days < 7: risk_level = "CRITICAL"
        elif ml_probability >= 50 or rul_days < 15: risk_level = "HIGH"
        elif ml_probability >= 30 or rul_days < 30: risk_level = "MEDIUM"
        else: risk_level = "LOW"

        predicted_priority = MachineLearningService.predict_priority(features_6) if _ml_model_p5 else risk_level.title()

        # SHAP Explanations (P1 - 5 features)
        explanations = []
        if model_p1 is not None:
            feature_names = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
            raw_explanations = XAIService.explain_prediction(model_p1, features_5, feature_names)
            explanations = [{"factor": XAIService.get_friendly_factor_name(e["factor"]), "impact": e["impact"], "intensity": e["intensity"]} for e in raw_explanations]

        response = {
            "machine_id": machine.id,
            "machine_name": machine.nom,
            "rul_days": round(float(max(0, rul_days)), 1),
            "risk_level": risk_level,
            "failure_probability": float(ml_probability) if ml_probability is not None else 0.0,
            "predicted_failure_date": (now + timedelta(days=max(0, rul_days))).isoformat(),
            "data_points": len(interventions),
            "ml_model_used": model_p1 is not None,
            "predicted_priority": predicted_priority,
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(float(anomaly_score), 4),
            "explanations": explanations,
            
            "health_score": round(float(ml_health_score), 1) if ml_health_score is not None else None,
            "health_breakdown": {
                "predictive_risk": round(float(ml_probability), 1),
                "score_source": score_source,
                "dst_verdict": dst_verdict,
                "conflict_factor_K": round(float(conflict_k), 4) if conflict_k is not None else None,
                "maintenance_deduction": round(float(maint_deduction), 1),
                "overdue_deduction": round(float(overdue_deduction), 1),
                "status_deduction": round(float(status_deduction), 1),
                "work_order_deduction": round(float(wo_deduction), 1),
                "intervention_deduction": round(float(ri_deduction), 1),
                "days_since_maintenance": days_since_maint,
                "open_work_orders": open_work_orders,
                "recent_interventions": recent_interventions,
                "degradation_rate_air":  round(float(deg_air),       4),
                "degradation_rate_wear": round(float(deg_wear),      4),
                "degradation_magnitude": round(float(deg_magnitude), 4),
            },
            "reliability_score": round(float(ml_reliability_score), 1) if ml_reliability_score is not None else 0.0,
            "mtbf_pred": round(float(ml_mtbf_hours), 1) if ml_mtbf_hours is not None else 0.0,
            "mttr_pred": round(float(ml_mttr_hours), 1) if ml_mttr_hours is not None else 0.0,
            "availability_pred": round(float(ml_availability_pct), 1) if ml_availability_pct is not None else 0.0,

            "air_temperature":     round(float(air_temp), 2),
            "process_temperature": round(float(process_temp), 2),
            "rotational_speed":    int(rpm),
            "torque":              round(float(torque), 2),
            "tool_wear":           round(float(tool_wear), 2),
            "telemetry_data_points": len(entries),
        }

        if model_p1 is None:
            response["model_unavailable"] = True

        return response
