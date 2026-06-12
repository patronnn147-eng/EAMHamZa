"""Tests for build_ml_context (ai_prompts) — ML snapshot → French prompt section."""
import pytest

from services.ai_prompts import build_ml_context, _sensor_status, _resolve_threshold_category


def _full_snapshot(**overrides):
    snap = {
        "machine_name": "Four Refusion BBS",
        "machine_type": "Reflow Oven",
        "health_score": 42.0,
        "dst_verdict": "Degrading",
        "failure_probability": 61.3,
        "risk_level": "HIGH",
        "rul_days": 12.0,
        "is_anomaly": True,
        "p4_anomaly_score": 0.72,
        "predicted_priority": "HAUTE",
        "p6_schedule_days": 8.0,
        "parts_items": [{"reference": "REF-001", "shortfall": 2.0}],
        "parts_readiness": "PARTIAL",
        "air_temperature": 302.4,
        "process_temperature": 528.1,
        "rotational_speed": 1150,
        "torque": 31.2,
        "tool_wear": 195,
    }
    snap.update(overrides)
    return snap


class TestBuildMlContext:
    def test_none_snapshot_returns_empty(self):
        assert build_ml_context(None) == ""

    def test_empty_snapshot_returns_empty(self):
        assert build_ml_context({}) == ""

    def test_full_snapshot_has_header_and_footer(self):
        out = build_ml_context(_full_snapshot())
        assert out.startswith("[ETAT ML EN TEMPS REEL]")
        assert out.endswith("[FIN ETAT ML]")
        assert "Four Refusion BBS" in out

    def test_core_fields_present(self):
        out = build_ml_context(_full_snapshot())
        assert "42/100" in out
        assert "61.3%" in out
        assert "HIGH" in out
        assert "12 jours" in out
        assert "Degrading" in out

    def test_anomaly_flagged(self):
        out = build_ml_context(_full_snapshot())
        assert "ANOMALIE COMPORTEMENTALE DETECTEE" in out
        assert "0.72" in out

    def test_no_anomaly_when_clean(self):
        out = build_ml_context(_full_snapshot(is_anomaly=False, p4_anomaly_score=0.1))
        assert "ANOMALIE" not in out

    def test_parts_shortfall_listed(self):
        out = build_ml_context(_full_snapshot())
        assert "REF-001" in out

    def test_sensor_status_reflow_process_temp_attention(self):
        # 528.1 K > warn_hi 525 but < crit_hi 530 for reflow → ATTENTION
        out = build_ml_context(_full_snapshot())
        assert "Temperature process" in out
        proc_line = next(l for l in out.split("\n") if "Temperature process" in l)
        assert "ATTENTION" in proc_line

    def test_kelvin_to_celsius_conversion(self):
        out = build_ml_context(_full_snapshot())
        # 302.4 K = 29.25 → 29.2/29.3 C
        assert "29.2C" in out or "29.3C" in out

    def test_missing_sensors_skipped(self):
        out = build_ml_context(_full_snapshot(torque=None, tool_wear=None))
        assert "Couple" not in out
        assert "Usure outil" not in out

    def test_missing_numeric_fields_show_nd(self):
        out = build_ml_context(_full_snapshot(health_score=None, rul_days=None))
        assert "N/D" in out


class TestSensorStatus:
    def test_normal(self):
        assert _sensor_status(300.0, (None, 306, None, 310)) == "NORMAL"

    def test_attention_high(self):
        assert _sensor_status(308.0, (None, 306, None, 310)) == "ATTENTION"

    def test_critique_high(self):
        assert _sensor_status(311.0, (None, 306, None, 310)) == "CRITIQUE"

    def test_attention_low_bound(self):
        assert _sensor_status(488.0, (490, 525, 485, 530)) == "ATTENTION"

    def test_critique_low_bound(self):
        assert _sensor_status(480.0, (490, 525, 485, 530)) == "CRITIQUE"


class TestThresholdCategory:
    def test_reflow_french(self):
        assert _resolve_threshold_category("", "Four de Refusion BBS") == "reflow"

    def test_wave_french(self):
        assert _resolve_threshold_category("Brassage a la vague", "") == "wave"

    def test_pickplace(self):
        assert _resolve_threshold_category("Pick and Place", "") == "pickplace"

    def test_unknown_falls_back_to_default(self):
        assert _resolve_threshold_category("Banc de Test", "BFE") == "_default"
