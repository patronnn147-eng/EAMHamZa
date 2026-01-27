"""
Authentication Schemas
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    nom: str = Field(..., min_length=2, max_length=100, description="Nom complet de l'utilisateur")
    mot_de_passe: str = Field(..., min_length=8, description="Mot de passe (minimum 8 caractères)")
    role: str = Field(..., description="Rôle de l'utilisateur: TECHNICIEN, CHEFTECH, CHETOP, ADMIN")
    
    @field_validator('mot_de_passe')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une lettre majuscule')
        if not re.search(r'[a-z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une lettre minuscule')
        if not re.search(r'[0-9]', v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role"""
        allowed_roles = ['TECHNICIEN', 'CHEFTECH', 'CHETOP', 'ADMIN']
        if v not in allowed_roles:
            raise ValueError(f'Rôle invalide. Rôles autorisés: {", ".join(allowed_roles)}')
        return v

class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    mot_de_passe: str = Field(..., description="Mot de passe")

class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    nom: str
    role: str
    
    class Config:
        from_attributes = True