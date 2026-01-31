export interface Intervention {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  machine_id: number;
  machine_nom?: string;
  technicien_id?: number;
  technicien_nom?: string;
  date_debut?: string;
  date_fin?: string;
  created_at: string;
}

export interface WorkOrder {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  machine_id: number;
  machine_nom?: string;
  utilisateur_id?: number;
  utilisateur_nom?: string;
  date_echeance?: string;
  created_at: string;
}

export interface Technician {
  id: number;
  nom: string;
  email: string;
  role: string;
  created_at: string;
}

export interface Machine {
  id: number;
  identifiant_machine: string;
  nom: string;
  emplacement: string;
  statut: string;
  type: string;
  date_derniere_maintenance?: string;
  date_prochaine_maintenance?: string;
  image_url?: string;
}

export interface DashboardStats {
  total_interventions: number;
  interventions_en_cours: number;
  interventions_termines: number;
  interventions_urgents: number;
  total_ordres_travail: number;
  ordres_en_attente: number;
  ordres_en_cours: number;
  total_techniciens: number;
  techniciens_disponibles: number;
  total_machines: number;
  machines_critiques: number;
}
