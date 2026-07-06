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
    get_current_user,
)
from models.utilisateurs import Utilisateurs
from schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from typing import Annotated

# Remove prefix from router - it will be added by main.py's auto-discovery
router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Register a new user - Account will be pending until admin approval

    - **email**: Email de l'utilisateur (format valide requis)
    - **nom**: Nom complet (2-100 caractères)
    - **mot_de_passe**: Mot de passe (min 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre)
    - **role**: TECHNICIEN, CHEFTECH, CHETOP, ou ADMIN
    """
    from core.email import email_service
    from models.utilisateurs import UserStatus

    # Check if email already exists
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    # Allow re-registration if previous account was rejected
    if existing_user:
        if existing_user.status != UserStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cet email existe déjà",
            )
        # Delete the rejected account to allow re-registration
        await db.delete(existing_user)
        await db.commit()

    # Create new user with PENDING status
    hashed_password = get_password_hash(user_data.mot_de_passe)
    new_user = Utilisateurs(
        email=user_data.email,
        nom=user_data.nom,
        mot_de_passe=hashed_password,
        role=user_data.role,
        status=UserStatus.PENDING,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send pending approval email
    email_service.send_registration_pending_email(new_user.email, new_user.nom)

    return {
        "message": "Inscription réussie! Votre compte est en attente d'approbation par un administrateur.",
        "status": "pending",
        "user": {
            "id": str(new_user.id),
            "email": new_user.email,
            "nom": new_user.nom,
            "role": new_user.role,
        },
    }


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Login with email and password

    - **email**: Email de l'utilisateur
    - **mot_de_passe**: Mot de passe
    """
    from models.utilisateurs import UserStatus

    # Find user by email
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    # Verify password
    if not verify_password(credentials.mot_de_passe, user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    # Check account status
    if user.status == UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte est en attente d'approbation par un administrateur",
        )

    if user.status == UserStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte a été rejeté. Veuillez contacter un administrateur",
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
            role=user.role,
            status=user.status,
            shift_type=user.shift_type.value
            if hasattr(user.shift_type, "value")
            else (str(user.shift_type) if getattr(user, "shift_type", None) else None),
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[Utilisateurs, Depends(get_current_user)]):
    """
    Get current authenticated user information
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        nom=current_user.nom,
        role=current_user.role,
        status=current_user.status,
        shift_type=current_user.shift_type.value
        if hasattr(current_user.shift_type, "value")
        else (
            str(current_user.shift_type)
            if getattr(current_user, "shift_type", None)
            else None
        ),
        created_at=current_user.created_at,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Refresh access token using refresh token from cookie
    """

    # This endpoint expects the refresh token to be passed via cookie
    # For simplicity, we'll create a new access token if user is authenticated
    # In production, you'd validate a refresh token from a signed cookie

    # For now, return a message that refresh requires authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token required. Please login again.",
    )


@router.post("/logout")
async def logout():
    """
    Logout current user (client should clear tokens)
    """
    return {"message": "Déconnexion réussie"}
