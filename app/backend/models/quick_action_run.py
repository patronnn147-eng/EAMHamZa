"""QuickActionRun — idempotency ledger for the Quick Action parts provisioning.

One row per successful (non-dry-run) execution. `hash` is UNIQUE: a repeat
request with the same recommendation short-circuits and replays `result_json`.
"""
from core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func


class QuickActionRun(Base):
    __tablename__ = "quick_action_runs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id = Column(Integer, nullable=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, index=True)
    result_json = Column(Text, nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
