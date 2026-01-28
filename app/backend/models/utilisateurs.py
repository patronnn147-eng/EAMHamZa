"""
Utilisateurs Model - User table for authentication and user management
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
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
    email = Column(String(255), unique=True, nullable=False, index=True)
    nom = Column(String(255), nullable=False)
    mot_de_passe_chiffre = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.TECHNICIEN)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Utilisateurs(id={self.id}, email={self.email}, nom={self.nom}, role={self.role})>"