from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: str
    email: str
    nom: str
    role: str

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    nom: str
    mot_de_passe: str
    role: Literal["ADMIN", "TECHNICIEN", "CHETOP", "CHEFTECH"]

    @field_validator('mot_de_passe')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password requirements"""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
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
    user: UserResponse


# Alias for compatibility
TokenResponse = Token