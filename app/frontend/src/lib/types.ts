// User and Role types
export type UserRole = 'CHETOP' | 'TECHNICIEN' | 'CHEFTECH' | 'ADMIN';

export interface Utilisateur {
  id: number;
  identifiant: string;
  nom_utilisateur: string;
  mot_de_passe_chiffre: string;
  courriel: string;
  role: UserRole;
  user_id: string;
  created_at: string;
}

// Machine types
export type MachineStatut = 'EN_ATTENTE' | 'EN_COURS' | 'TERMINE' | 'ANNULE';

export interface Machine {
  id: number;
  identifiant_machine: string;
  nom: string;
  emplacement: string;
  statut: MachineStatut;
  type: string;
  date_derniere_maintenance?: string;
  date_prochaine_maintenance?: string;
  image_url?: string;
  created_at: string;
}

// Order types
export type OrderStatut = 'EN_ATTENTE' | 'EN_COURS' | 'TERMINE' | 'ANNULE';

export interface Ordre {
  id: number;
  identifiant: string;
  titre: string;
  description?: string;
  date_creation: string;
  statut: OrderStatut;
  created_at: string;
}

// Work Order types
export type WorkOrderPriorite = 'BASSE' | 'MOYENNE' | 'ELEVEE' | 'URGENTE';

export interface OrdreTravail {
  id: number;
  date_echeance: string;
  priorite: WorkOrderPriorite;
  machine_id: number;
  utilisateur_id?: number;
  ordre_id?: number;
  statut: OrderStatut;
  created_at: string;
}

// Intervention types
export interface OrdreIntervention {
  id: number;
  date_intervention: string;
  rapport?: string;
  ordre_travail_id: number;
  created_at: string;
}

// Planning types
export type PlanningType = 'JOURNALIER' | 'HEBDOMADAIRE' | 'MENSUEL' | 'MAINTENANCE';

export interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: PlanningType;
  created_at: string;
}

export interface PlanningUtilisateur {
  id: number;
  planning_id: number;
  utilisateur_id: number;
  created_at: string;
}

export interface PlanningOrdreTravail {
  id: number;
  planning_id: number;
  ordre_travail_id: number;
  created_at: string;
}

// Archive types
export type ArchiveType = 'DOCUMENT' | 'IMAGE' | 'VIDEO' | 'AUTRE';

export interface Archive {
  id: number;
  identifiant_archive: string;
  nom: string;
  date_archivage: string;
  type: ArchiveType;
  object_key?: string;
  ordre_travail_id?: number;
  created_at: string;
}

// Report types
export interface Rapport {
  id: number;
  identifiant_rapport: string;
  titre: string;
  date_generation: string;
  contenu: string;
  utilisateur_id?: number;
  created_at: string;
}

// Maintenance types
export interface MaintenancePlanifiee {
  id: number;
  utilisateur_id?: number;
  rapport_id?: number;
  date_planifiee: string;
  description?: string;
  created_at: string;
}

// Dashboard metrics
export interface DashboardMetrics {
  totalMachines: number;
  activeMachines: number;
  pendingWorkOrders: number;
  urgentWorkOrders: number;
  completedThisWeek: number;
  upcomingMaintenance: number;
}