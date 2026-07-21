"""
UtilisateurZones Model - many-to-many zone assignment for CHEFTECH/TECHNICIEN oversight scoping
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from core.database import Base
from datetime import datetime


class UtilisateurZone(Base):
    """One row per (user, zone) assignment. A user can be assigned to multiple zones."""

    __tablename__ = "utilisateur_zones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    utilisateur_id = Column(
        Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<UtilisateurZone utilisateur_id={self.utilisateur_id} zone={self.zone}>"
