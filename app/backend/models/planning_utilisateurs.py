from core.database import Base
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import relationship


class Planning_utilisateurs(Base):
    __tablename__ = "planning_utilisateurs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    planning_id = Column(Integer, nullable=False)
    utilisateur_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship for eager loading the user
    utilisateur = relationship(
        "Utilisateurs",
        primaryjoin="foreign(Planning_utilisateurs.utilisateur_id) == Utilisateurs.id",
        lazy="noload",
        viewonly=True,
    )