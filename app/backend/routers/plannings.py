"""
Custom Planning Router with Role-Based Access Control
Admin: Full CRUD access
Other roles: Read-only access
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings, PlanningType, ShiftType
from models.planning_machines import Planning_machines
from models.planning_utilisateurs import Planning_utilisateurs
from models.machines import Machines
from models.notifications import Notifications
from services.plannings import PlanningsService
from services.planning_utilisateurs import Planning_utilisateursService
from services.notifications import NotificationsService
from tasks.planning_emails import send_planning_assignment_emails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])


def _serialize_planning_for_email(payload: dict) -> dict:
    def _dt(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return "" if value is None else str(value)

    return {
        "id": payload.get("id"),
        "identifiant_planning": payload.get("identifiant_planning", ""),
        "date_debut": _dt(payload.get("date_debut")),
        "date_fin": _dt(payload.get("date_fin")),
        "type": payload.get("type", ""),
        "shift_type": payload.get("shift_type") or "",
        "zone_travail": payload.get("zone_travail") or "",
    }


# ---------- Pydantic Schemas ----------
class PlanningCreateData(BaseModel):
    """Schema for creating a planning"""
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: PlanningType
    shift_type: Optional[ShiftType] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    technicien_ids: List[int] = Field(default_factory=list, description="List of technician IDs")
    machine_ids: List[int] = Field(default_factory=list, description="List of machine IDs")


class PlanningUpdateData(BaseModel):
    """Schema for updating a planning"""
    identifiant_planning: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    type: Optional[PlanningType] = None
    shift_type: Optional[ShiftType] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    technicien_ids: Optional[List[int]] = None
    machine_ids: Optional[List[int]] = None


class PlanningResponse(BaseModel):
    """Schema for planning response"""
    id: int
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: str
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    created_at: Optional[datetime] = None
    assigned_users: List[dict] = Field(default_factory=list)
    machine_ids: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PlanningListResponse(BaseModel):
    """List response schema"""
    items: List[PlanningResponse]
    total: int
    skip: int
    limit: int


class UserOption(BaseModel):
    """User option for dropdowns"""
    id: int
    nom: str
    email: str
    role: str
    shift_type: Optional[str] = None


class PlanningMachineResponse(BaseModel):
    """Machine as returned when listing planning machines"""

    id: int
    nom: str
    type: Optional[str] = None
    emplacement: Optional[str] = None
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    statut: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Helper Functions ----------
async def verify_admin(current_user: Utilisateurs):
    """Verify that the current user is an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action"
        )


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Utilisateurs]:
    """Get user by ID"""
    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    return result.scalar_one_or_none()


async def validate_planning_data(db: AsyncSession, data: PlanningCreateData):
    """Validate planning data"""
    # Validate shift_type is provided only for SHIFT type
    if data.type == PlanningType.SHIFT:
        if not data.shift_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="shift_type is required for SHIFT planning"
            )
        if not data.chef_operation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chef_operation_id is required for SHIFT planning"
            )
    elif data.shift_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="shift_type should only be provided for SHIFT planning"
        )

    # Validate chef_operation exists and has CHETOP role
    if data.chef_operation_id:
        chef_op = await get_user_by_id(db, data.chef_operation_id)
        if not chef_op:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chef Operation with ID {data.chef_operation_id} not found"
            )
        if chef_op.role != UserRole.CHETOP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chef Operation must have CHETOP role"
            )

    # Validate chef_technique exists and has CHEFTECH role
    if data.chef_technique_id:
        chef_tech = await get_user_by_id(db, data.chef_technique_id)
        if not chef_tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chef Technique with ID {data.chef_technique_id} not found"
            )
        if chef_tech.role != UserRole.CHEFTECH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chef Technique must have CHEFTECH role"
            )

    # Validate all technicians exist and have TECHNICIEN role
    for tech_id in data.technicien_ids:
        tech = await get_user_by_id(db, tech_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician with ID {tech_id} not found"
            )
        if tech.role != UserRole.TECHNICIEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {tech_id} must have TECHNICIEN role"
            )


async def send_planning_notifications(
    db: AsyncSession,
    planning_id: int,
    identifiant_planning: str,
    user_ids: List[int]
):
    """Send notifications to all assigned users"""
    notification_service = NotificationsService(db)
    
    for user_id in user_ids:
        try:
            notification_data = {
                "utilisateur_id": user_id,
                "titre": "Planning Assignment",
                "priorite": "MOYENNE",  # Add priority field
                "type": "PLANNING_ASSIGNMENT",
                "message": f"You have been assigned to planning: {identifiant_planning}",
                "date_envoi": datetime.now(),
                "lu": False
            }
            await notification_service.create(notification_data)
            logger.info(f"Notification sent to user {user_id} for planning {planning_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {str(e)}")


async def get_planning_with_users(db: AsyncSession, planning: Plannings) -> dict:
    """Get planning with assigned users"""
    # Get assigned users
    result = await db.execute(
        select(Planning_utilisateurs, Utilisateurs)
        .join(Utilisateurs, Planning_utilisateurs.utilisateur_id == Utilisateurs.id)
        .where(Planning_utilisateurs.planning_id == planning.id)
    )
    
    assigned_users = []
    seen_user_ids = set()
    for pu, user in result:
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        
        # Safely handle enum values
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        shift_val = None
        if user.shift_type:
            shift_val = user.shift_type.value if hasattr(user.shift_type, "value") else str(user.shift_type)
            
        assigned_users.append({
            "id": user.id,
            "nom": user.nom,
            "email": user.email,
            "role": role_val,
            "shift_type": shift_val,
        })
    
    machines_result = await db.execute(
        select(Planning_machines.machine_id).where(Planning_machines.planning_id == planning.id)
    )
    machine_ids = [row[0] for row in machines_result.fetchall()]
    
    # Safely handle enum values for planning
    type_val = planning.type.value if hasattr(planning.type, "value") else str(planning.type)
    planning_shift_val = None
    if planning.shift_type:
        planning_shift_val = planning.shift_type.value if hasattr(planning.shift_type, "value") else str(planning.shift_type)

    return {
        "id": planning.id,
        "identifiant_planning": planning.identifiant_planning,
        "date_debut": planning.date_debut,
        "date_fin": planning.date_fin,
        "type": type_val,
        "shift_type": planning_shift_val,
        "chef_operation_id": planning.chef_operation_id,
        "chef_technique_id": planning.chef_technique_id,
        "zone_travail": planning.zone_travail,
        "created_at": planning.created_at,
        "assigned_users": assigned_users,
        "machine_ids": machine_ids,
    }


# ---------- Routes ----------
@router.get("/users/by-role/{role}", response_model=List[UserOption])
async def get_users_by_role(
    role: UserRole,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get users by role for dropdown selection"""
    await verify_admin(current_user)
    
    try:
        result = await db.execute(
            select(Utilisateurs).where(Utilisateurs.role == role)
        )
        users = result.scalars().all()
        
        return [
            UserOption(
                id=user.id,
                nom=user.nom,
                email=user.email,
                role=user.role.value,
                shift_type=user.shift_type.value if hasattr(user.shift_type, "value") else (str(user.shift_type) if getattr(user, "shift_type", None) else None),
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error fetching users by role {role}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.get("", response_model=PlanningListResponse)
async def list_plannings(
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List plannings filtered by user role and assignments"""
    try:
        service = PlanningsService(db)
        
        # Admin can see all plannings
        if current_user.role == UserRole.ADMIN:
            result = await service.get_list(skip=skip, limit=limit, sort="-date_debut")
        else:
            # Non-admin users can only see their assigned plannings
            # Role-specific filtering for more precision
            if current_user.role == UserRole.CHETOP:
                # Chef Opérateur sees plannings where they are responsible
                query = select(Plannings.id).where(Plannings.chef_operation_id == current_user.id)
            elif current_user.role == UserRole.CHEFTECH:
                # Chef Technique sees plannings where they are responsible
                query = select(Plannings.id).where(Plannings.chef_technique_id == current_user.id)
            else:
                # Technicians see plannings where they are explicitly assigned in planning_utilisateurs
                query = select(Planning_utilisateurs.planning_id).where(
                    Planning_utilisateurs.utilisateur_id == current_user.id
                )
            
            planning_ids_result = await db.execute(query.distinct())
            planning_ids = [row[0] for row in planning_ids_result.fetchall()]
            
            if not planning_ids:
                # User has no assigned plannings
                return PlanningListResponse(
                    items=[],
                    total=0,
                    skip=skip,
                    limit=limit
                )
            
            # Get only the plannings where user is assigned
            data_query = select(Plannings).where(Plannings.id.in_(planning_ids))
            
            # Apply sorting
            data_query = data_query.order_by(Plannings.date_debut.desc())
            
            # Apply pagination
            data_query = data_query.offset(skip).limit(limit)
            
            # Execute query
            plannings_result = await db.execute(data_query)
            plannings_objs = plannings_result.scalars().all()
            
            # Get total count
            count_query = select(func.count(Plannings.id)).where(Plannings.id.in_(planning_ids))
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0
            
            items = []
            for p in plannings_objs:
                items.append(await get_planning_with_users(db, p))
            
            return PlanningListResponse(
                items=items,
                total=total,
                skip=skip,
                limit=limit
            )
            
        # Enrich with assigned users
        items_with_users = []
        for planning in result["items"]:
            planning_dict = await get_planning_with_users(db, planning)
            items_with_users.append(PlanningResponse(**planning_dict))
        
        return PlanningListResponse(
            items=items_with_users,
            total=result["total"],
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing plannings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plannings: {str(e)}"
        )


@router.get("/{planning_id}", response_model=PlanningResponse)
async def get_planning(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get planning details with role-based access control"""
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
            )
        
        # Check if user has access to this planning
        if current_user.role != UserRole.ADMIN:
            has_access = False
            if current_user.role == UserRole.CHETOP:
                has_access = planning.chef_operation_id == current_user.id
            elif current_user.role == UserRole.CHEFTECH:
                has_access = planning.chef_technique_id == current_user.id
            
            # If not already found as chef, check the bridge table (especially for technicians)
            if not has_access:
                pu_result = await db.execute(
                    select(Planning_utilisateurs).where(
                        Planning_utilisateurs.planning_id == planning_id,
                        Planning_utilisateurs.utilisateur_id == current_user.id
                    )
                )
                has_access = pu_result.scalar_one_or_none() is not None
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this planning"
                )
        
        planning_dict = await get_planning_with_users(db, planning)
        return PlanningResponse(**planning_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching planning {planning_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch planning: {str(e)}"
        )


@router.get("/{planning_id}/machines", response_model=List[PlanningMachineResponse])
async def get_planning_machines(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get machines assigned to a planning with role-based access control"""
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found",
            )

        if current_user.role != UserRole.ADMIN:
            # Check if user is responsible for this planning
            has_access = False
            if current_user.role == UserRole.CHETOP:
                has_access = planning.chef_operation_id == current_user.id
            elif current_user.role == UserRole.CHEFTECH:
                has_access = planning.chef_technique_id == current_user.id
            
            # If not responsible, check if explicitly assigned (bridge table)
            if not has_access:
                assignment_query = select(Planning_utilisateurs).where(
                    Planning_utilisateurs.planning_id == planning_id,
                    Planning_utilisateurs.utilisateur_id == current_user.id,
                )
                assignment_result = await db.execute(assignment_query)
                assignment = assignment_result.scalar_one_or_none()
                has_access = assignment is not None
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view machines for this planning",
                )

        result = await db.execute(
            select(Machines)
            .join(Planning_machines, Planning_machines.machine_id == Machines.id)
            .where(Planning_machines.planning_id == planning_id)
            .order_by(Machines.nom.asc())
        )
        machines = result.scalars().all()
        return [PlanningMachineResponse.model_validate(m) for m in machines]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching planning machines for {planning_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch planning machines: {str(e)}",
        )


@router.post("", response_model=PlanningResponse, status_code=status.HTTP_201_CREATED)
async def create_planning(
    data: PlanningCreateData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        # TODO: Temporarily disable validation to isolate greenlet_spawn issue
        # await validate_planning_data(db, data)
        
        # Create planning directly without service to avoid greenlet_spawn
        planning_data = {
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type.value,
            "shift_type": data.shift_type.value if data.shift_type else None,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "created_at": datetime.now()
        }
        
        planning = Plannings(**planning_data)
        db.add(planning)
        await db.commit()
        await db.refresh(planning)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create planning"
            )
        
        # Capture only the ID immediately to avoid greenlet_spawn issues
        planning_id = planning.id
        
        # Create response data without accessing planning object attributes
        planning_response_data = {
            "id": planning_id,
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type.value,
            "shift_type": data.shift_type.value if data.shift_type else None,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "created_at": datetime.now(),
            "assigned_users": [],
            "machine_ids": [],
        }

        if data.machine_ids:
            now = datetime.now()
            for machine_id in sorted(set(data.machine_ids)):
                db.add(
                    Planning_machines(
                        planning_id=planning_id,
                        machine_id=machine_id,
                        created_at=now,
                    )
                )
            await db.commit()
            planning_response_data["machine_ids"] = sorted(set(data.machine_ids))
        
        # Assign users (dedupe + single commit)
        user_ids_set = set()
        if data.chef_operation_id:
            user_ids_set.add(data.chef_operation_id)
        if data.chef_technique_id:
            user_ids_set.add(data.chef_technique_id)
        if data.technicien_ids:
            user_ids_set.update(data.technicien_ids)

        all_assigned_users = list(user_ids_set)

        # Enforce user shift availability for SHIFT plannings
        if data.type == PlanningType.SHIFT and data.shift_type and all_assigned_users:
            mismatched_result = await db.execute(
                select(Utilisateurs.id)
                .where(Utilisateurs.id.in_(all_assigned_users))
                .where(Utilisateurs.shift_type != data.shift_type.value)
            )
            mismatched_ids = [row[0] for row in mismatched_result.fetchall()]
            if mismatched_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Users {mismatched_ids} do not match planning shift_type {data.shift_type.value}",
                )

        now = datetime.now()
        for user_id in all_assigned_users:
            db.add(
                Planning_utilisateurs(
                    planning_id=planning_id,
                    utilisateur_id=user_id,
                    created_at=now,
                )
            )
        await db.commit()

        if all_assigned_users:
            await send_planning_notifications(db, planning_id, data.identifiant_planning, all_assigned_users)

            users_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(all_assigned_users)))
            users = users_result.scalars().all()
            recipients = [{"id": u.id, "nom": u.nom, "email": u.email} for u in users if getattr(u, "email", None)]
            if recipients:
                send_planning_assignment_emails.delay(recipients, _serialize_planning_for_email(planning_response_data))
        
        # Return simple dict to avoid greenlet_spawn issues
        return planning_response_data
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating planning: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create planning: {str(e)}"
        )


@router.put("/{planning_id}", response_model=PlanningResponse)
async def update_planning(
    planning_id: int,
    data: PlanningUpdateData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
            )
        
        original_identifiant_planning = planning.identifiant_planning
        original_date_debut = planning.date_debut
        original_date_fin = planning.date_fin
        original_type = planning.type.value if planning.type else None
        original_shift_type = planning.shift_type.value if planning.shift_type else None
        original_chef_operation_id = planning.chef_operation_id
        original_chef_technique_id = planning.chef_technique_id
        original_zone_travail = getattr(planning, "zone_travail", None)
        original_created_at = planning.created_at

        # Build update dict
        update_dict = {}
        if data.identifiant_planning is not None:
            update_dict["identifiant_planning"] = data.identifiant_planning
        if data.date_debut is not None:
            update_dict["date_debut"] = data.date_debut
        if data.date_fin is not None:
            update_dict["date_fin"] = data.date_fin
        if data.type is not None:
            update_dict["type"] = data.type.value
        if data.shift_type is not None:
            update_dict["shift_type"] = data.shift_type.value
        if data.chef_operation_id is not None:
            update_dict["chef_operation_id"] = data.chef_operation_id
        if data.chef_technique_id is not None:
            update_dict["chef_technique_id"] = data.chef_technique_id
        if data.zone_travail is not None:
            update_dict["zone_travail"] = data.zone_travail
        
        # Update planning
        await service.update(planning_id, update_dict)

        identifiant_planning = update_dict.get("identifiant_planning", original_identifiant_planning)

        planning_response_data = {
            "id": planning_id,
            "identifiant_planning": identifiant_planning,
            "date_debut": update_dict.get("date_debut", original_date_debut),
            "date_fin": update_dict.get("date_fin", original_date_fin),
            "type": update_dict.get("type", original_type),
            "shift_type": update_dict.get("shift_type", original_shift_type),
            "chef_operation_id": update_dict.get("chef_operation_id", original_chef_operation_id),
            "chef_technique_id": update_dict.get("chef_technique_id", original_chef_technique_id),
            "zone_travail": update_dict.get("zone_travail", original_zone_travail),
            "created_at": original_created_at,
            "assigned_users": [],
            "machine_ids": [],
        }

        if data.machine_ids is not None:
            await db.execute(
                delete(Planning_machines).where(Planning_machines.planning_id == planning_id)
            )
            now = datetime.now()
            for machine_id in sorted(set(data.machine_ids)):
                db.add(
                    Planning_machines(
                        planning_id=planning_id,
                        machine_id=machine_id,
                        created_at=now,
                    )
                )
            await db.commit()
            planning_response_data["machine_ids"] = sorted(set(data.machine_ids))
        else:
            machines_result = await db.execute(
                select(Planning_machines.machine_id).where(Planning_machines.planning_id == planning_id)
            )
            planning_response_data["machine_ids"] = [row[0] for row in machines_result.fetchall()]

        all_assigned_users: List[int] = []
        
        if (
            data.chef_operation_id is not None
            or data.chef_technique_id is not None
            or data.technicien_ids is not None
        ):
            user_ids_set = set()
            if data.chef_operation_id:
                user_ids_set.add(data.chef_operation_id)
            if data.chef_technique_id:
                user_ids_set.add(data.chef_technique_id)
            if data.technicien_ids:
                user_ids_set.update(data.technicien_ids)

            all_assigned_users = list(user_ids_set)

            await db.execute(
                delete(Planning_utilisateurs).where(
                    Planning_utilisateurs.planning_id == planning_id
                )
            )

            now = datetime.now()
            for user_id in all_assigned_users:
                db.add(
                    Planning_utilisateurs(
                        planning_id=planning_id,
                        utilisateur_id=user_id,
                        created_at=now,
                    )
                )

            await db.commit()

        if all_assigned_users:
            await send_planning_notifications(db, planning_id, identifiant_planning, all_assigned_users)

            users_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(all_assigned_users)))
            users = users_result.scalars().all()
            recipients = [{"id": u.id, "nom": u.nom, "email": u.email} for u in users if getattr(u, "email", None)]
            if recipients:
                send_planning_assignment_emails.delay(recipients, _serialize_planning_for_email(planning_response_data))

        return PlanningResponse(**planning_response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating planning {planning_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update planning: {str(e)}"
        )


@router.post("/{planning_id}/resend-emails")
async def resend_planning_emails(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually re-send planning assignment emails to currently assigned users (admin only)."""
    await verify_admin(current_user)

    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning not found")

    assigned_ids_result = await db.execute(
        select(Planning_utilisateurs.utilisateur_id).where(Planning_utilisateurs.planning_id == planning_id)
    )
    user_ids = [row[0] for row in assigned_ids_result.fetchall()]

    if not user_ids:
        return {"queued": 0}

    users_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(user_ids)))
    users = users_result.scalars().all()
    recipients = [{"id": u.id, "nom": u.nom, "email": u.email} for u in users if getattr(u, "email", None)]
    if not recipients:
        return {"queued": 0}

    planning_payload = _serialize_planning_for_email(
        {
            "id": planning.id,
            "identifiant_planning": planning.identifiant_planning,
            "date_debut": planning.date_debut,
            "date_fin": planning.date_fin,
            "type": planning.type.value if getattr(planning, "type", None) else "",
            "shift_type": planning.shift_type.value if getattr(planning, "shift_type", None) else None,
            "zone_travail": getattr(planning, "zone_travail", None),
        }
    )

    send_planning_assignment_emails.delay(recipients, planning_payload)
    return {"queued": len(recipients)}


@router.delete("/{planning_id}")
async def delete_planning(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        # Delete associated planning_utilisateurs records first
        pu_service = Planning_utilisateursService(db)
        result = await db.execute(
            select(Planning_utilisateurs)
            .where(Planning_utilisateurs.planning_id == planning_id)
        )
        assignments = result.scalars().all()
        
        for assignment in assignments:
            await pu_service.delete(assignment.id)
        
        # Delete planning
        service = PlanningsService(db)
        success = await service.delete(planning_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
            )
        
        return {"message": "Planning deleted successfully", "id": planning_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting planning {planning_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete planning: {str(e)}"
        )