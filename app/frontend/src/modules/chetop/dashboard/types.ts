export interface WorkOrder {
  id: number;
  titre: string;
  description: string;
  priorite: string;
  statut: string;
  date_echeance?: string;
  created_at: string;
  machine_id: number;
  machine_nom?: string;
  utilisateur_id?: number;
  utilisateur_nom?: string;
}

export interface Machine {
  id: number;
  nom: string;
  emplacement?: string;
  type?: string;
  statut?: string;
}

export interface DashboardStats {
  total_ordres: number;
  ordres_en_attente: number;
  ordres_en_cours: number;
  ordres_termines: number;
  ordres_urgents: number;
  total_machines: number;
  machines_en_maintenance: number;
  machines_hors_service: number;
}

export interface CreateWorkOrderFormData {
  titre: string;
  description: string;
  priorite: string;
  machine_id: number;
  utilisateur_id: number | null;
  date_echeance: string;
}
