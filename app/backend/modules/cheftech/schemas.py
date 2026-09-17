from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class InterventionResponse(BaseModel):
    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
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
    work_order_due_date: Optional[datetime] = None
    is_overdue: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # PDCA / Enhanced Fields
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


class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    utilisateur_id: Optional[int] = None
    date_echeance: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None

    class Config:
        from_attributes = True


class MachineResponse(BaseModel):
    id: int
    nom: str
    emplacement: Optional[str] = None
    statut: Optional[str] = None
    type: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TechnicianResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_ordres_travail: int
    ordres_en_attente: int
    ordres_en_cours: int
    total_interventions: int
    interventions_en_cours: int
    total_techniciens: int
    techniciens_disponibles: int
    total_machines: int
    machines_critiques: int


class DistributionSlice(BaseModel):
    name: str
    value: int


class InterventionDistributions(BaseModel):
    by_status: List[DistributionSlice]
    by_type: List[DistributionSlice]
    by_root_cause: List[DistributionSlice]
    by_machine_category: List[DistributionSlice]


class WorkOrderAssignRequest(BaseModel):
    technicien_ids: List[int]
    estimated_completion_date: Optional[datetime] = None
    machine_ids: Optional[List[int]] = None


class InterventionDecisionRequest(BaseModel):
    rejection_reason: Optional[str] = None
    technician_id: Optional[int] = None


class ChefTechFeedbackRequest(BaseModel):
    feedback: str


class CompletedWorkOrderItem(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    machine_nom: Optional[str] = None
    utilisateur_id: Optional[int] = None
    technician_nom: Optional[str] = None
    technician_email: Optional[str] = None
    date_echeance: Optional[datetime] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    failure_type: Optional[str] = None
    cheftech_feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
