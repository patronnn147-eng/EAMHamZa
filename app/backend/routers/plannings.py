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
from sqlalchemy import select

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings, PlanningType, ShiftType
from models.planning_utilisateurs import Planning_utilisateurs
from models.notifications import Notifications
from services.plannings import PlanningsService
from services.planning_utilisateurs import Planning_utilisateursService
from services.notifications import NotificationsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])


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
    technicien_ids: List[int] = Field(default_factory=list, description="List of technician IDs")


class PlanningUpdateData(BaseModel):
    """Schema for updating a planning"""
    identifiant_planning: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    type: Optional[PlanningType] = None
    shift_type: Optional[ShiftType] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    technicien_ids: Optional[List[int]] = None


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
    created_at: Optional[datetime] = None
    assigned_users: List[dict] = Field(default_factory=list)

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
    planning: Plannings,
    user_ids: List[int]
):
    """Send notifications to all assigned users"""
    notification_service = NotificationsService(db)
    
    for user_id in user_ids:
        try:
            notification_data = {
                "utilisateur_id": user_id,
                "type": "PLANNING_ASSIGNMENT",
                "message": f"You have been assigned to planning: {planning.identifiant_planning}",
                "date_envoi": datetime.now(),
                "lu": False
            }
            await notification_service.create(notification_data)
            logger.info(f"Notification sent to user {user_id} for planning {planning.id}")
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
    for pu, user in result:
        assigned_users.append({
            "id": user.id,
            "nom": user.nom,
            "email": user.email,
            "role": user.role.value
        })
    
    return {
        "id": planning.id,
        "identifiant_planning": planning.identifiant_planning,
        "date_debut": planning.date_debut,
        "date_fin": planning.date_fin,
        "type": planning.type.value,
        "shift_type": planning.shift_type.value if planning.shift_type else None,
        "chef_operation_id": planning.chef_operation_id,
        "chef_technique_id": planning.chef_technique_id,
        "created_at": planning.created_at,
        "assigned_users": assigned_users
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
                role=user.role.value
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
    """List all plannings (all users can view)"""
    try:
        service = PlanningsService(db)
        result = await service.get_list(skip=skip, limit=limit, sort="-date_debut")
        
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
    """Get planning details (all users can view)"""
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
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


@router.post("", response_model=PlanningResponse, status_code=status.HTTP_201_CREATED)
async def create_planning(
    data: PlanningCreateData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        # Validate planning data
        await validate_planning_data(db, data)
        
        # Create planning
        planning_service = PlanningsService(db)
        planning_data = {
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type.value,
            "shift_type": data.shift_type.value if data.shift_type else None,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "created_at": datetime.now()
        }
        
        planning = await planning_service.create(planning_data)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create planning"
            )
        
        # Assign users to planning
        pu_service = Planning_utilisateursService(db)
        all_assigned_users = []
        
        # Add chef operation
        if data.chef_operation_id:
            all_assigned_users.append(data.chef_operation_id)
            await pu_service.create({
                "planning_id": planning.id,
                "utilisateur_id": data.chef_operation_id,
                "created_at": datetime.now()
            })
        
        # Add chef technique
        if data.chef_technique_id:
            all_assigned_users.append(data.chef_technique_id)
            await pu_service.create({
                "planning_id": planning.id,
                "utilisateur_id": data.chef_technique_id,
                "created_at": datetime.now()
            })
        
        # Add technicians
        for tech_id in data.technicien_ids:
            all_assigned_users.append(tech_id)
            await pu_service.create({
                "planning_id": planning.id,
                "utilisateur_id": tech_id,
                "created_at": datetime.now()
            })
        
        # Send notifications to all assigned users
        await send_planning_notifications(db, planning, all_assigned_users)
        
        # Return planning with assigned users
        planning_dict = await get_planning_with_users(db, planning)
        return PlanningResponse(**planning_dict)
        
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
        
        # Update planning
        updated_planning = await service.update(planning_id, update_dict)
        
        # Update assigned users if provided
        if data.technicien_ids is not None:
            # Remove existing technician assignments
            pu_service = Planning_utilisateursService(db)
            result = await db.execute(
                select(Planning_utilisateurs)
                .where(Planning_utilisateurs.planning_id == planning_id)
            )
            existing_assignments = result.scalars().all()
            
            for assignment in existing_assignments:
                await pu_service.delete(assignment.id)
            
            # Add new assignments
            all_assigned_users = []
            
            if data.chef_operation_id:
                all_assigned_users.append(data.chef_operation_id)
                await pu_service.create({
                    "planning_id": planning_id,
                    "utilisateur_id": data.chef_operation_id,
                    "created_at": datetime.now()
                })
            
            if data.chef_technique_id:
                all_assigned_users.append(data.chef_technique_id)
                await pu_service.create({
                    "planning_id": planning_id,
                    "utilisateur_id": data.chef_technique_id,
                    "created_at": datetime.now()
                })
            
            for tech_id in data.technicien_ids:
                all_assigned_users.append(tech_id)
                await pu_service.create({
                    "planning_id": planning_id,
                    "utilisateur_id": tech_id,
                    "created_at": datetime.now()
                })
            
            # Send notifications
            await send_planning_notifications(db, updated_planning, all_assigned_users)
        
        planning_dict = await get_planning_with_users(db, updated_planning)
        return PlanningResponse(**planning_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating planning {planning_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update planning: {str(e)}"
        )


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