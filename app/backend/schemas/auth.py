from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    nom: str
    mot_de_passe: str
    role: Literal["ADMIN", "TECHNICIEN"]

    @field_validator('mot_de_passe')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password requirements"""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Le mot de passe ne peut pas dépasser 72 octets')
        return v

    @field_validator('nom')
    @classmethod
    def validate_nom(cls, v: str) -> str:
        """Validate name is not empty"""
        if not v or not v.strip():
            raise ValueError('Le nom ne peut pas être vide')
        return v.strip()


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    mot_de_passe: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: int
    email: str
    nom: str
    role: str

    class Config:
        from_attributes = True