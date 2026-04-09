from fastapi import Depends, HTTPException
from models.utilisateurs import Utilisateurs, UserRole
from core.auth import get_current_user


async def verify_management_access(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN, UserRole.CHETOP]:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle de gestion requis.")
    return current_user


async def verify_cheftech(current_user: Utilisateurs = Depends(verify_management_access)):
    return current_user


async def verify_cheftech_or_admin(current_user: Utilisateurs = Depends(verify_management_access)):
    return current_user
