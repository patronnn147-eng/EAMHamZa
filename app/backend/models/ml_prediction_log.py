from core.database import Base
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.sql import func


class MlPredictionLog(Base):
    """
    Shadow logging table for ML predictions (PDCA Plan - Phase 1).
    Every time the backend computes a prediction, a row is logged here.
    Used for auditing model accuracy against real-world outcomes.
    """
    __tablename__ = "ml_prediction_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id = Column(Integer, nullable=False, index=True)
    machine_name = Column(String, nullable=True)

    # P1: Failure Risk
    risk_level = Column(String(20), nullable=True)          # CRITICAL / HIGH / MEDIUM / LOW
    failure_probability = Column(Float, nullable=True)      # 0-100

    # P3: Remaining Useful Life
    rul_days = Column(Float, nullable=True)
    predicted_failure_date = Column(String, nullable=True)   # ISO timestamp

    # P5: Work Order Priority
    predicted_priority = Column(String(20), nullable=True)   # Critical / High / Medium / Low

    # P4: Anomaly Detection
    is_anomaly = Column(Boolean, nullable=True, default=False)
    anomaly_score = Column(Float, nullable=True)

    # P2: Failure Type (stored as JSON string, e.g. '{"TWF": true, "HDF": false, ...}')
    p2_failure_types = Column(Text, nullable=True)

    # P7: Parts Demand (stored as JSON string — parts_demand contract)
    p7_parts_demand = Column(Text, nullable=True)

    # Telemetry Snapshot (Used for automated retraining ground truth)
    air_temperature = Column(Float, nullable=True)
    process_temperature = Column(Float, nullable=True)
    rotational_speed = Column(Integer, nullable=True)
    torque = Column(Float, nullable=True)
    tool_wear = Column(Integer, nullable=True)

    # Metadata
    data_points = Column(Integer, nullable=True)
    ml_model_used = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
