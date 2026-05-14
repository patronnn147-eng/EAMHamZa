from pathlib import Path
from pydantic_settings import BaseSettings


class MLConfig(BaseSettings):
    # Model file paths base directory
    models_dir: Path = Path(__file__).parent.parent.parent / "models"

    # P1 — failure probability risk level thresholds (%)
    p1_risk_medium: float = 25.0
    p1_risk_high: float = 50.0
    p1_risk_critical: float = 75.0

    # P4 — anomaly detection score threshold (0.0–1.0)
    p4_anomaly_threshold: float = 0.5

    # Wave 2 DST fusion — Dempster-Shafer conflict threshold
    dst_conflict_threshold: float = 0.8

    # Sensor defaults — used when a reading is missing from the request
    default_air_temp: float = 298.0
    default_process_temp: float = 308.0
    default_rpm: int = 1500
    default_torque: float = 40.0
    default_tool_wear: int = 0

    model_config = {"env_prefix": "ML_"}


config = MLConfig()
