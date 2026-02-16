export interface User {
  id: string;
  email: string;
  role: string;
  nom?: string;
  created_at: string;
}

export interface Machine {
  id: number;
  nom: string;
  type?: string;
  emplacement?: string;
  zone?: string;
  sous_zone?: string;
  ordre?: string;
  statut?: string;
  date_derniere_maintenance?: string;
  date_prochaine_maintenance?: string;
  image_url?: string;
  user_id?: string;
  created_at?: string;
}

export interface OrdreTravail {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  date_echeance: string;
  machine_id: number;
  utilisateur_id?: number;
  utilisateur_nom?: string;
  user_id: string;
  created_at: string;
}

export interface Intervention {
  id: number;
  date_intervention: string;
  statut?: string;
  technicien_id?: number;
  date_debut?: string;
  date_fin?: string;
  rapport: string;
  ordre_travail_id: number;
  problem_description?: string;
  priority?: string;
  estimated_duration_minutes?: number;
  required_materials?: string;
  machine_id?: number;
  requested_at?: string;
  approved_by?: number;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: string;
  chef_technique_id?: number | null;
  machine_ids?: number[];
  assigned_users?: Array<{
    id: number;
    nom: string;
    email: string;
    role: string;
    shift_type?: string | null;
  }>;
  created_at: string;
}

export interface Rapport {
  id: number;
  identifiant_rapport: string;
  titre: string;
  contenu: string;
  utilisateur_id: string;
  created_at: string;
}

export interface Archive {
  id: number;
  nom_fichier: string;
  type_fichier: string;
  taille_fichier: number;
  chemin_stockage: string;
  user_id: string;
  created_at: string;
}