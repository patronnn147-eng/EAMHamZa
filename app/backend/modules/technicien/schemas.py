from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class InterventionResponse(BaseModel):
    id: int
    ordre_travail_id: Optional[int] = None
    statut: str
    date_intervention: datetime
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    work_order_due_date: Optional[datetime] = None
    is_overdue: Optional[bool] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None
    retrained: Optional[bool] = None
    machine_category: Optional[str] = None
    symptoms: Optional[str] = None
    problem_start_time: Optional[datetime] = None
    frequency: Optional[str] = None
    operating_state: Optional[str] = None
    temperature: Optional[str] = None
    impact: Optional[str] = None
    estimated_loss: Optional[str] = None
    similar_issue_before: Optional[bool] = None
    suggested_cause: Optional[str] = None
    suggested_priority: Optional[str] = None
    risk_score: Optional[str] = None
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    actions_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    tools_used: Optional[str] = None
    machine_status_after: Optional[str] = None
    plan_hypothesis: Optional[str] = None
    check_resolved: Optional[bool] = None
    check_verification_method: Optional[str] = None
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None

    class Config:
        from_attributes = True


class InterventionStatusUpdate(BaseModel):
    statut: str
    rapport: Optional[str] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class InterventionRequestPayload(BaseModel):
    ordre_travail_id: Optional[int] = None
    machine_id: int
    problem_description: str
    priority: str
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    
    # Enhanced Fields from ChefOp flow
    machine_category: Optional[str] = None
    symptoms: Optional[str] = None
    problem_start_time: Optional[datetime] = None
    frequency: Optional[str] = None
    operating_state: Optional[str] = None
    temperature: Optional[str] = None
    impact: Optional[str] = None
    estimated_loss: Optional[str] = None
    similar_issue_before: Optional[bool] = None


class WorkOrderExecutionUpdate(BaseModel):
    statut: str
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    failure_type: Optional[str] = None


class MachineResponse(BaseModel):
    id: int
    nom: str
    emplacement: Optional[str] = None
    type: Optional[str] = None
    statut: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
