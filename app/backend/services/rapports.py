import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.rapports import Rapports
from models.machines import Machines
from models.alertes import Alert

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class RapportsService:
    """Service layer for Rapports operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Rapports]:
        """Create a new rapports"""
        try:
            obj = Rapports(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created rapports with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating rapports: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Rapports]:
        """Get rapports by ID"""
        try:
            query = select(Rapports).where(Rapports.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching rapports {obj_id}: {str(e)}")
            raise

    @staticmethod
    def _apply_filters(query, count_query, model, query_dict):
        """Apply equality filters from query_dict to both queries."""
        if not query_dict:
            return query, count_query
        for field, value in query_dict.items():
            if hasattr(model, field):
                condition = getattr(model, field) == value
                query = query.where(condition)
                count_query = count_query.where(condition)
        return query, count_query

    @staticmethod
    def _apply_sort(query, sort, model):
        """Apply ordering to query; defaults to id.desc()."""
        if not sort:
            return query.order_by(model.id.desc())
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(model, field_name):
                return query.order_by(getattr(model, field_name).desc())
        elif hasattr(model, sort):
            return query.order_by(getattr(model, sort))
        return query.order_by(model.id.desc())

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of rapportss"""
        try:
            query, count_query = self._apply_filters(
                select(Rapports),
                select(func.count(Rapports.id)),
                Rapports,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort, Rapports)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching rapports list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Rapports]:
        """Update rapports"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Rapports {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated rapports {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating rapports {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete rapports"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Rapports {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted rapports {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting rapports {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Rapports]:
        """Get rapports by any field"""
        try:
            if not hasattr(Rapports, field_name):
                raise ValueError(f"Field {field_name} does not exist on Rapports")
            result = await self.db.execute(
                select(Rapports).where(getattr(Rapports, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching rapports by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Rapports]:
        """Get list of rapportss filtered by field"""
        try:
            if not hasattr(Rapports, field_name):
                raise ValueError(f"Field {field_name} does not exist on Rapports")
            result = await self.db.execute(
                select(Rapports)
                .where(getattr(Rapports, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Rapports.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(f"Error fetching rapportss by {field_name}: {str(e)}")
            raise

    async def get_scheduled_reports(self, active_only: bool = True) -> List[Rapports]:
        """Get all scheduled reports"""
        try:
            query = select(Rapports).where(Rapports.report_type.isnot(None))
            if active_only:
                query = query.where(Rapports.is_active)
            result = await self.db.execute(query.order_by(Rapports.id.desc()))
            return list(result.scalars().all())
        except Exception as e:
            logger.exception(f"Error fetching scheduled reports: {str(e)}")
            raise

    async def create_scheduled_report(
        self,
        report_type: str,
        title: str,
        schedule_config: Dict[str, Any],
        recipients: List[int],
    ) -> Rapports:
        """Create a new scheduled report"""
        try:
            obj = Rapports(
                identifiant_rapport=f"SCHED_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                titre=title,
                date_generation=datetime.now(),
                contenu=json.dumps({"type": report_type, "recipients": recipients}),
                report_type=report_type,
                schedule_config=schedule_config,
                is_active=True,
            )
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created scheduled report with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating scheduled report: {str(e)}")
            raise

    async def generate_asset_health_report(self) -> Dict[str, Any]:
        """Generate asset health report data"""
        try:
            # Get machine counts
            machines_result = await self.db.execute(select(func.count(Machines.id)))
            total_machines = machines_result.scalar() or 0

            # Get active alerts
            alerts_result = await self.db.execute(
                select(func.count(Alert.id)).where(Alert.is_active)
            )
            active_alerts = alerts_result.scalar() or 0

            # Get critical alerts
            critical_result = await self.db.execute(
                select(func.count(Alert.id)).where(
                    and_(Alert.is_active, Alert.severity == "CRITICAL")
                )
            )
            critical_alerts = critical_result.scalar() or 0

            return {
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_machines": total_machines,
                    "active_alerts": active_alerts,
                    "critical_alerts": critical_alerts,
                },
                "report_type": "ASSET_HEALTH",
            }
        except Exception as e:
            logger.exception(f"Error generating asset health report: {str(e)}")
            raise

    async def generate_weekly_digest(self) -> Dict[str, Any]:
        """Generate weekly digest report data"""
        try:
            week_ago = datetime.now() - timedelta(days=7)

            # Get machines
            machines_result = await self.db.execute(select(func.count(Machines.id)))
            total_machines = machines_result.scalar() or 0

            # Get alerts this week
            alerts_result = await self.db.execute(
                select(func.count(Alert.id)).where(Alert.created_at >= week_ago)
            )
            alerts_this_week = alerts_result.scalar() or 0

            return {
                "generated_at": datetime.now().isoformat(),
                "period": f"Last 7 days (from {week_ago.strftime('%Y-%m-%d')})",
                "summary": {
                    "total_machines": total_machines,
                    "alerts_generated": alerts_this_week,
                },
                "report_type": "WEEKLY_DIGEST",
            }
        except Exception as e:
            logger.exception(f"Error generating weekly digest: {str(e)}")
            raise
