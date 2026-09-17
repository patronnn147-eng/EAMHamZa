from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from core.celery_app import celery_app
from core.database import db_manager
from models.alertes import Alert  # noqa: F401 — registers Alert mapper for string relationships
from models.machines import Machines
from models.ordres_travail import Ordres_travail
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


async def run_maintenance_check():
    """Logic for the maintenance check"""
    # Each asyncio.run() creates a new event loop. Close + reinit db_manager
    # (engine + asyncio.Locks) so everything is bound to the current loop,
    # avoiding "Future attached to a different loop" errors.
    await db_manager.close_db()
    db_manager._init_lock = asyncio.Lock()
    db_manager._table_creation_lock = asyncio.Lock()
    await db_manager.init_db()

    async with db_manager.async_session_maker() as session:
        # 1. Query machines with upcoming maintenance (next 7 days)
        now = datetime.now(timezone.utc)
        limit_date = now + timedelta(days=7)

        logger.info(f"Checking for maintenance due between {now} and {limit_date}")

        query = select(Machines).where(
            and_(
                Machines.date_prochaine_maintenance is not None,
                Machines.date_prochaine_maintenance >= now,
                Machines.date_prochaine_maintenance <= limit_date,
            )
        )
        result = await session.execute(query)
        machines = result.scalars().all()

        created_count = 0
        for machine in machines:
            # 2. Check if a preventive order already exists
            # We look for [PRÉVENTIF] in the title for this machine that isn't finished or cancelled
            order_query = select(Ordres_travail).where(
                and_(
                    Ordres_travail.machine_id == machine.id,
                    Ordres_travail.titre.like("[PRÉVENTIF]%"),
                    Ordres_travail.statut.in_(["EN_ATTENTE", "EN_COURS"]),
                )
            )
            order_result = await session.execute(order_query)
            existing_order = order_result.scalar_one_or_none()

            if not existing_order:
                # 3. Create the preventive work order
                new_order = Ordres_travail(
                    titre=f"[PRÉVENTIF] Maintenance - {machine.nom}",
                    description=f"Maintenance préventive planifiée automatiquement pour la machine {machine.nom}.",
                    priorite="MOYENNE",
                    machine_id=machine.id,
                    date_echeance=machine.date_prochaine_maintenance,
                    statut="EN_ATTENTE",
                )
                session.add(new_order)
                created_count += 1
                logger.info(
                    f"Created preventive work order for machine {machine.nom} (ID: {machine.id})"
                )
            else:
                logger.debug(
                    f"Preventive order already exists for machine {machine.nom} (ID: {machine.id})"
                )

        if created_count > 0:
            await session.commit()
            logger.info(f"Successfully created {created_count} preventive work orders")
        else:
            logger.info("No new preventive work orders needed")

        return created_count


@celery_app.task(name="tasks.check_preventive_maintenance")
def check_preventive_maintenance():
    """Trigger the maintenance check background task"""
    logger.info("🚀 Starting preventive maintenance check task...")
    try:
        # Use a new event loop for this sync call
        created = asyncio.run(run_maintenance_check())
        return {"status": "success", "created_orders": created}
    except Exception as e:
        logger.exception(
            f"❌ Error in check_preventive_maintenance task: {str(e)}", exc_info=True
        )
        return {"status": "error", "message": str(e)}
