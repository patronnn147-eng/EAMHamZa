from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Ordres_intervention(Base):
    __tablename__ = "ordres_intervention"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    date_intervention = Column(DateTime(timezone=True), nullable=False)
    rapport = Column(String, nullable=True)
    ordre_travail_id = Column(Integer, nullable=True)
    technician_id = Column(Integer, nullable=True)
    planning_id = Column(Integer, nullable=True)  # Links intervention to a planning
    planning_tache_id = Column(Integer, nullable=True)  # Links intervention to a specific task
    statut = Column(String(20), nullable=False, default="EN_ATTENTE")
    problem_description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    required_materials = Column(Text, nullable=True)
    machine_id = Column(Integer, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=True)
    requested_by = Column(Integer, nullable=True)  # User who requested the intervention (ChefOp)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    archived_at = Column(DateTime(timezone=True), nullable=True)

    archive_reason = Column(String(50), nullable=True)
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
    # parts_replaced renamed to legacy_parts_text — kept for legacy records only.
    # The current source of truth for consumed parts is the consumed_pieces table.
    # The `parts_replaced` accessor below returns a JSON string aggregated from that table.
    legacy_parts_text = Column(Text, nullable=True)
    tools_used = Column(Text, nullable=True)
    machine_status_after = Column(String(50), nullable=True)  # Operational, Limited, Stopped
    # NEW: indicates CHEFTECH approved the required pieces (reservation already applied)
    parts_approved = Column(Boolean, nullable=True)

    # PDCA Specific
    plan_hypothesis = Column(Text, nullable=True)
    check_resolved = Column(Boolean, nullable=True)
    check_verification_method = Column(String(100), nullable=True) # Test run, Monitoring, Visual inspection
    act_preventive_actions = Column(Text, nullable=True)
    act_recommendations = Column(Text, nullable=True)

    # Relationships for eager loading (no FK constraints in DB, use primaryjoin)
    machine = relationship(
        "Machines",
        primaryjoin="foreign(Ordres_intervention.machine_id) == Machines.id",
        lazy="noload",
        viewonly=True,
    )
    technician = relationship(
        "Utilisateurs",
        primaryjoin="foreign(Ordres_intervention.technician_id) == Utilisateurs.id",
        lazy="noload",
        viewonly=True,
    )
    ordre_travail = relationship(
        "Ordres_travail",
        primaryjoin="foreign(Ordres_intervention.ordre_travail_id) == Ordres_travail.id",
        lazy="noload",
        viewonly=True,
    )

    # ── parts_replaced: computed, not persisted ──────────────────────────────
    # Reads from consumed_pieces (single source of truth). Always returns a
    # JSON string (or empty list) for backwards compatibility with reports
    # that previously read the raw text column. The actual rows live in
    # `consumed_pieces` and are reachable via `consumed_items` relationship.
    consumed_items = relationship(
        "ConsumedPiece",
        primaryjoin="foreign(ConsumedPiece.intervention_id) == Ordres_intervention.id",
        lazy="noload",
        viewonly=True,
    )

    @property
    def parts_replaced(self) -> str:
        """Computed JSON summary of consumed pieces (single source of truth).

        Falls back to legacy_parts_text for historical records that were
        completed before the consumed_pieces table existed.
        """
        import json

        # Use loaded consumed_items if available (selectinload pattern)
        loaded = getattr(self, "__dict__", {}).get("consumed_items")
        if loaded is not None and len(loaded) > 0:
            return json.dumps([
                {
                    "piece_id":  ci.piece_id,
                    "used":      float(ci.quantity_used or 0),
                    "returned":  float(ci.quantity_returned or 0),
                    "wasted":    float(ci.quantity_wasted or 0),
                    "unit":      ci.unit,
                    "disposition": ci.disposition,
                }
                for ci in loaded
            ])

        # Fallback for legacy records
        return self.legacy_parts_text or ""
