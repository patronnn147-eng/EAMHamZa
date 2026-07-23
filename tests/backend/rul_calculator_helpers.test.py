"""Unit tests for the RULCalculator static helper methods in rul_calculator.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from modules.ml.rul_calculator import RULCalculator


def _telemetry(air, proc, rpm, torque, wear):
    return SimpleNamespace(
        air_temperature=air, process_temperature=proc,
        rotational_speed=rpm, torque=torque, tool_wear=wear,
    )


# ── _extract_telemetry ───────────────────────────────────────────────────────

def test_extract_telemetry_empty_returns_all_none():
    assert RULCalculator._extract_telemetry([]) == (None, None, None, None, None)


def test_extract_telemetry_returns_last_entry():
    entries = [_telemetry(300, 310, 1500, 40, 10), _telemetry(301, 311, 1520, 41, 12)]
    air, proc, rpm, torque, wear = RULCalculator._extract_telemetry(entries)
    assert (air, proc, rpm, torque, wear) == (301.0, 311.0, 1520, 41.0, 12.0)


# ── _deg_rate ─────────────────────────────────────────────────────────────────

def test_deg_rate_needs_at_least_two_entries():
    assert RULCalculator._deg_rate([_telemetry(300, 310, 1500, 40, 10)], "air_temperature") == 0.0


def test_deg_rate_computes_slope_over_entry_count():
    entries = [_telemetry(300, 310, 1500, 40, 10), _telemetry(310, 310, 1500, 40, 10),
               _telemetry(320, 310, 1500, 40, 10)]
    assert RULCalculator._deg_rate(entries, "air_temperature") == 10.0


# ── _extract_fusion_fields ───────────────────────────────────────────────────

def test_extract_fusion_fields_none_result_returns_defaults():
    result = RULCalculator._extract_fusion_fields(None)
    assert result == (0.0, None, False, 0.0, None, {}, [], None)


def test_extract_fusion_fields_reads_known_keys():
    fusion = {
        "p1_failure_probability": 42.0, "p3_rul_days": 15.0, "p4_is_anomaly": True,
        "p4_anomaly_score": 0.9, "p5_predicted_priority": "P1",
        "p2_failure_types": {"TWF": {}}, "shap_explanations": [{"factor": "x"}],
        "p3_rul_interval": {"p10": 10, "p50": 15, "p90": 20},
    }
    ml_prob, model_rul, is_anom, anom_score, prio, ftypes, shap, interval = \
        RULCalculator._extract_fusion_fields(fusion)
    assert ml_prob == 42.0 and model_rul == 15.0 and is_anom is True
    assert anom_score == 0.9 and prio == "P1"
    assert ftypes == {"TWF": {}}
    assert interval == {"p10": 10, "p50": 15, "p90": 20}


# ── _scale_rul_interval ───────────────────────────────────────────────────────

def test_scale_rul_interval_none_when_no_interval():
    assert RULCalculator._scale_rul_interval(None, 20.0) is None


def test_scale_rul_interval_none_when_p50_invalid():
    assert RULCalculator._scale_rul_interval({"p10": 5, "p50": 0, "p90": 10}, 20.0) is None


def test_scale_rul_interval_rescales_around_final_rul():
    interval = RULCalculator._scale_rul_interval({"p10": 10, "p50": 20, "p90": 30}, rul_days=40.0)
    assert interval["confidence"] == 0.8
    assert interval["low"] == 20.0  # 40 * (1 - 0.5)
    assert interval["high"] == 60.0  # 40 * (1 + 0.5)


# ── _compute_deductions ───────────────────────────────────────────────────────

def _machine(statut="OPERATIONNELLE", derniere=None, prochaine=None):
    return SimpleNamespace(
        statut=statut, date_derniere_maintenance=derniere, date_prochaine_maintenance=prochaine,
    )


def test_compute_deductions_no_maintenance_dates():
    now = datetime.now(timezone.utc)
    deds = RULCalculator._compute_deductions(_machine(), now, open_work_orders=0, recent_interventions=0)
    maint_ded, overdue_ded, status_ded, wo_ded, ri_ded, days_since = deds
    assert maint_ded == 0 and overdue_ded == 0 and status_ded == 0
    assert days_since == -1


def test_compute_deductions_panne_status_adds_60():
    now = datetime.now(timezone.utc)
    deds = RULCalculator._compute_deductions(_machine(statut="EN_PANNE"), now, 0, 0)
    assert deds[2] == 60


def test_compute_deductions_overdue_maintenance():
    now = datetime.now(timezone.utc)
    overdue_machine = _machine(prochaine=now - timedelta(days=5))
    deds = RULCalculator._compute_deductions(overdue_machine, now, 0, 0)
    assert deds[1] == 10  # 5 days * 2


def test_compute_deductions_caps_wo_and_intervention_deductions():
    now = datetime.now(timezone.utc)
    deds = RULCalculator._compute_deductions(_machine(), now, open_work_orders=10, recent_interventions=10)
    assert deds[3] == 36  # capped
    assert deds[4] == 30  # capped


# ── _compute_health_score ─────────────────────────────────────────────────────

def test_compute_health_score_uses_dst_fusion_when_available():
    fusion = {"unified_health_score": 77.0, "dst_verdict": "Healthy", "conflict_factor_K": 0.2}
    score, source, verdict, k = RULCalculator._compute_health_score(fusion, 10.0, 0, 0, 0, 0, 0)
    assert (score, source, verdict, k) == (77.0, "dst_fusion", "Healthy", 0.2)


def test_compute_health_score_falls_back_to_additive_formula():
    score, source, verdict, k = RULCalculator._compute_health_score(None, 20.0, 5, 5, 0, 0, 0)
    assert source == "fallback_additive" and verdict is None and k is None
    assert score == 70.0  # (100-20) - (5+5)


# ── _compute_kpis ─────────────────────────────────────────────────────────────

def test_compute_kpis_no_interventions_returns_perfect_scores():
    kpis = RULCalculator._compute_kpis([], 10.0, 5.0, {}, 90.0, 90.0)
    assert kpis == (0.0, 0.0, 0.0, 100.0, 100.0)


def test_compute_kpis_mttr_increases_for_detected_failure_types():
    interventions = [object()]
    mtbf, mttr, avail, health, reliability = RULCalculator._compute_kpis(
        interventions, 10.0, 5.0, {"HDF": {"detected": True}, "TWF": {"detected": True}}, 80.0, 80.0
    )
    assert mtbf == 240.0  # 10*24
    assert mttr == 2.5 + 1.5 + 0.5


# ── _compute_risk_level ───────────────────────────────────────────────────────

def test_compute_risk_level_thresholds():
    assert RULCalculator._compute_risk_level(80, 100) == "CRITICAL"
    assert RULCalculator._compute_risk_level(10, 5) == "CRITICAL"
    assert RULCalculator._compute_risk_level(55, 100) == "HIGH"
    assert RULCalculator._compute_risk_level(10, 10) == "HIGH"
    assert RULCalculator._compute_risk_level(35, 100) == "MEDIUM"
    assert RULCalculator._compute_risk_level(10, 20) == "MEDIUM"
    assert RULCalculator._compute_risk_level(0, 100) == "LOW"


# ── _map_shap ─────────────────────────────────────────────────────────────────

def test_map_shap_translates_known_factor():
    result = RULCalculator._map_shap([{"factor": "Air temperature [K]", "impact": 0.5, "intensity": "high"}])
    assert result == [{"factor": "Température Ambiante", "impact": 0.5, "intensity": "high"}]


def test_map_shap_passes_through_unknown_factor():
    result = RULCalculator._map_shap([{"factor": "Unknown Sensor", "impact": 0.1}])
    assert result[0]["factor"] == "Unknown Sensor"
    assert result[0]["intensity"] == "low"


def test_map_shap_empty_list():
    assert RULCalculator._map_shap([]) == []


# ── _derive_predicted_priority ────────────────────────────────────────────────

def test_derive_predicted_priority_prefers_ml_prediction():
    assert RULCalculator._derive_predicted_priority("P1", [object()], "medium") == "P1"


def test_derive_predicted_priority_normal_when_no_interventions():
    assert RULCalculator._derive_predicted_priority(None, [], "high") == "Normal"


def test_derive_predicted_priority_falls_back_to_risk_level_title():
    assert RULCalculator._derive_predicted_priority(None, [object()], "critical") == "Critical"


# ── _get_historical_mtbf ──────────────────────────────────────────────────────

def _intervention(date):
    return SimpleNamespace(date_intervention=date)


def test_get_historical_mtbf_default_with_fewer_than_two_interventions():
    assert RULCalculator._get_historical_mtbf([]) == 60.0
    assert RULCalculator._get_historical_mtbf([], default_days=30.0) == 30.0
    assert RULCalculator._get_historical_mtbf([_intervention(datetime.now(timezone.utc))]) == 60.0


def test_get_historical_mtbf_averages_gaps_between_dates():
    now = datetime.now(timezone.utc)
    interventions = [
        _intervention(now - timedelta(days=30)),
        _intervention(now - timedelta(days=20)),
        _intervention(now - timedelta(days=10)),
    ]
    # gaps: 10 days, 10 days -> mean 10.0
    assert RULCalculator._get_historical_mtbf(interventions) == 10.0
