from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship


class Machines(Base):
    __tablename__ = "machines"
    __table_args__ = {"extend_existing": True}

    # Relationships
    alerts = relationship("Alert", back_populates="machine")

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    nom = Column(String, nullable=False)

    type = Column(String, nullable=True)
    emplacement = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    sous_zone = Column(String, nullable=True)
    ordre = Column(String, nullable=True)
    statut = Column(String, nullable=True, default="OPERATIONNELLE")
    date_derniere_maintenance = Column(DateTime(timezone=True), nullable=True)
    date_prochaine_maintenance = Column(DateTime(timezone=True), nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
