"""
Utilisateurs Model - User table for authentication and user management
"""
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from core.database import Base
import enum

class UserRole(str, enum.Enum):
    """User roles"""
    TECHNICIEN = "TECHNICIEN"
    CHEFTECH = "CHEFTECH"
    CHETOP = "CHETOP"
    ADMIN = "ADMIN"

class Utilisateurs(Base):
    """Users table for authentication"""
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nom = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.TECHNICIEN)
    
    def __repr__(self):
        return f"<Utilisateurs(id={self.id}, email={self.email}, nom={self.nom}, role={self.role})>"