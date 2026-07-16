from fastapi import Depends, HTTPException
from models.utilisateurs import Utilisateurs
from core.auth import get_current_user


def verify_technicien(
    current_user: Utilisateurs = Depends(get_current_user),
) -> Utilisateurs:
    """Dependency to verify that the current user has the TECHNICIEN role."""
    if current_user.role != "TECHNICIEN":
        raise HTTPException(
            status_code=403, detail="Accès non autorisé. Rôle TECHNICIEN requis."
        )
    return current_user
