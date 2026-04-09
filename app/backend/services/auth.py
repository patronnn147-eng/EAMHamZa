import logging
import time
from datetime import datetime, timezone
from typing import Optional

from core.config import settings
from core.database import db_manager
from core.auth import get_password_hash
from models.utilisateurs import Utilisateurs, UserRole
from sqlalchemy import select

logger = logging.getLogger(__name__)



async def initialize_admin_user():
    """Initialize admin user if not exists"""

    from services.database import initialize_database

    # Ensure database is initialized first
    await initialize_database()

    admin_id = getattr(settings, "admin_id", "")
    admin_user_email = getattr(settings, "admin_user_email", "")
    admin_user_password = getattr(settings, "admin_user_password", "")
    admin_user_nom = getattr(settings, "admin_user_nom", "Admin")

    if not admin_id or not admin_user_email or not admin_user_password:
        logger.warning("Admin user configuration missing, skipping admin initialization")
        return

    async with db_manager.async_session_maker() as db:
        # Check if admin user already exists (by email)
        result = await db.execute(select(Utilisateurs).where(Utilisateurs.email == admin_user_email))
        user: Optional[Utilisateurs] = result.scalar_one_or_none()

        if user:
            # Update existing user to admin if not already
            if str(user.role) != str(UserRole.ADMIN):
                user.role = UserRole.ADMIN
                user.email = admin_user_email  # Update email too
                await db.commit()
                logger.debug(f"Updated user {admin_id} to admin role")
            else:
                logger.debug(f"Admin user {admin_id} already exists")
        else:
            # Create new admin user
            hashed_password = get_password_hash(admin_user_password)
            admin_user = Utilisateurs(
                email=admin_user_email,
                nom=admin_user_nom,
                mot_de_passe=hashed_password,
                role=UserRole.ADMIN,
            )
            db.add(admin_user)
            await db.commit()
            logger.debug(f"Created admin user: {admin_id} with email: {admin_user_email}")
