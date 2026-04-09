from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class InterventionRequestCreate(BaseModel):
    """ChefOp requests an intervention (PDS) - Enhanced"""
    machine_id: int
    priorite: str = "MOYENNE"
    description: str
    
    # Enhanced DI fields
    machine_category: Optional[str] = None
    symptoms: Optional[str] = None
    problem_start_time: Optional[datetime] = None
    frequency: Optional[str] = None
    operating_state: Optional[str] = None
    temperature: Optional[str] = None
    impact: Optional[str] = None
    estimated_loss: Optional[str] = None
    similar_issue_before: Optional[bool] = None
    
    # AI placeholders (usually filled by backend/ML service)
    suggested_cause: Optional[str] = None
    suggested_priority: Optional[str] = None
    risk_score: Optional[str] = None


class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    priorite: str
    statut: str
    machine_id: int
    machine_nom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterventionRequestResponse(BaseModel):
    id: int
    machine_id: int
    machine_nom: Optional[str] = None
    priorite: str
    description: str
    statut: str
    requested_at: Optional[datetime] = None
    ordre_travail_id: Optional[int] = None
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True


class MachineStatusUpdate(BaseModel):
    """US-CHETOP-007: Update machine status"""
    statut: str  # disponible, en_maintenance, hors_service
    commentaire: Optional[str] = None


class MachineResponse(BaseModel):
    """US-CHETOP-006: Machine with status"""
    id: int
    nom: str
    emplacement: Optional[str] = None
    type: Optional[str] = None
    statut: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """CHETOP Dashboard Statistics"""
    total_requests: int
    requests_pending: int
    requests_approved: int
    requests_rejected: int
    total_machines: int
    machines_en_maintenance: int
    machines_hors_service: int


class WorkOrderCompletePayload(BaseModel):
    rapport: str
    
    # Enhanced Report fields
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    actions_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    tools_used: Optional[str] = None
    machine_status_after: Optional[str] = None
    
    # PDCA Specific
    plan_hypothesis: Optional[str] = None
    check_resolved: Optional[bool] = None
    check_verification_method: Optional[str] = None
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None
