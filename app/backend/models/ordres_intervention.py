from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.sql import func


class Ordres_intervention(Base):
    __tablename__ = "ordres_intervention"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    date_intervention = Column(DateTime(timezone=True), nullable=False)
    rapport = Column(String, nullable=True)
    ordre_travail_id = Column(Integer, nullable=True)
    technicien_id = Column(Integer, nullable=True)
    statut = Column(String(20), nullable=False, default="EN_ATTENTE")
    problem_description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    required_materials = Column(Text, nullable=True)
    machine_id = Column(Integer, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # PDCA Feedback Fields (Technician fills these out when closing an intervention)
    actual_failure_type = Column(String(20), nullable=True)    # TWF, HDF, PWF, OSF, RNF, or None
    ml_prediction_matched = Column(Boolean, nullable=True)     # Did the ML prediction match reality?
    retrained = Column(Boolean, nullable=True, default=False)  # Has this feedback been used to retrain the model?

    # --- New Enhanced DI Fields ---
    machine_category = Column(String(50), nullable=True)  # critical / non-critical
    symptoms = Column(Text, nullable=True)  # multi-select comma separated or JSON
    problem_start_time = Column(DateTime(timezone=True), nullable=True)
    frequency = Column(String(50), nullable=True)  # First time, Occasional, Recurrent
    operating_state = Column(String(50), nullable=True)  # Running, Idle, Startup, Shutdown
    load_level = Column(Integer, nullable=True)  # %
    temperature = Column(String(50), nullable=True)
    impact = Column(String(100), nullable=True)  # Production stopped, Reduced performance, No impact yet
    estimated_loss = Column(String(100), nullable=True)
    similar_issue_before = Column(Boolean, nullable=True)
    
    # AI / Prediction fields
    suggested_cause = Column(String(255), nullable=True)
    suggested_priority = Column(String(50), nullable=True)
    risk_score = Column(String(50), nullable=True)

    # --- New Enhanced Report Fields ---
    intervention_type = Column(String(50), nullable=True)  # Corrective, Preventive, Predictive
    root_cause_category = Column(String(50), nullable=True)  # Mechanical, Electrical, Software, Human error, Unknown
    root_cause_description = Column(Text, nullable=True)
    actions_performed = Column(Text, nullable=True)  # multi-select
    parts_replaced = Column(Text, nullable=True) # JSON or descriptive text
    tools_used = Column(Text, nullable=True)
    machine_status_after = Column(String(50), nullable=True)  # Operational, Limited, Stopped

    # PDCA Specific
    plan_hypothesis = Column(Text, nullable=True)
    check_resolved = Column(Boolean, nullable=True)
    check_verification_method = Column(String(100), nullable=True) # Test run, Monitoring, Visual inspection
    act_preventive_actions = Column(Text, nullable=True)
    act_recommendations = Column(Text, nullable=True)
