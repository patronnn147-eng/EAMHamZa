"""
Utilisateurs Model - User table for authentication and user management
"""
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime
from core.database import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    """User roles"""
    TECHNICIEN = "TECHNICIEN"
    CHEFTECH = "CHEFTECH"
    CHETOP = "CHETOP"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    """User account status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class UserShiftType(str, enum.Enum):
    """Default shift availability for a user"""
    MORNING = "MORNING"
    NIGHT = "NIGHT"

class Utilisateurs(Base):
    """Users table for authentication"""
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nom = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.TECHNICIEN)
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.PENDING)
    shift_type = Column(SQLEnum(UserShiftType, native_enum=False), nullable=False, default=UserShiftType.MORNING)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Utilisateurs(id={self.id}, email={self.email}, nom={self.nom}, role={self.role}, status={self.status})>"