from fastapi import Depends, HTTPException
from models.utilisateurs import Utilisateurs, UserRole
from core.auth import get_current_user


def verify_management_access(
    current_user: Utilisateurs = Depends(get_current_user),
):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN, UserRole.CHETOP]:
        raise HTTPException(
            status_code=403, detail="Accès non autorisé. Rôle de gestion requis."
        )
    return current_user


def verify_cheftech(
    current_user: Utilisateurs = Depends(verify_management_access),
):
    return current_user


def verify_cheftech_or_admin(
    current_user: Utilisateurs = Depends(verify_management_access),
):
    return current_user


def verify_cheftech_only(
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Strict CHEFTECH-only guard — unlike verify_cheftech above (which
    actually also allows ADMIN and CHETOP via verify_management_access),
    this rejects everyone except CHEFTECH. Used for the machine-status
    approval queue, where ADMIN deliberately has no action (read-only via
    the audit log)."""
    if current_user.role != UserRole.CHEFTECH:
        raise HTTPException(status_code=403, detail="Réservé au chef technicien.")
    return current_user
