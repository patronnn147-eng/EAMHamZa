"""
Authentication Routes - Simple JWT-based authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user
)
from models.utilisateurs import Utilisateurs
from schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse

# Remove prefix from router - it will be added by main.py's auto-discovery
router = APIRouter(tags=["authentication"])

@router.post("/api/v1/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: Email de l'utilisateur (format valide requis)
    - **nom**: Nom complet (2-100 caractères)
    - **mot_de_passe**: Mot de passe (min 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre)
    - **role**: TECHNICIEN, CHEFTECH, CHETOP, ou ADMIN
    """
    # Check if email already exists
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.mot_de_passe)
    new_user = Utilisateurs(
        email=user_data.email,
        nom=user_data.nom,
        mot_de_passe_chiffre=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            nom=new_user.nom,
            role=new_user.role
        )
    )

@router.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password
    
    - **email**: Email de l'utilisateur
    - **mot_de_passe**: Mot de passe
    """
    # Find user by email
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    # Verify password
    if not verify_password(credentials.mot_de_passe, user.mot_de_passe_chiffre):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            nom=user.nom,
            role=user.role
        )
    )

@router.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user: Utilisateurs = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        nom=current_user.nom,
        role=current_user.role
    )