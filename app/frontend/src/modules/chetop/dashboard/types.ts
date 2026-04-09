export interface InterventionRequest {
  id: number;
  machine_id: number;
  machine_nom?: string;
  priorite: string;
  description: string;
  statut: string;
  requested_at: string;
  rejection_reason?: string;
  ordre_travail_id?: number;
}

export interface Machine {
  id: number;
  identifiant_machine?: string;
  nom: string;
  emplacement?: string;
  type?: string;
  statut?: string;
}

export interface DashboardStats {
  total_requests: number;
  requests_pending: number;
  requests_approved: number;
  requests_rejected: number;
  total_machines: number;
  machines_en_maintenance: number;
  machines_hors_service: number;
}

export interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
}
