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
  air_temperature?: number;
  process_temperature?: number;
  rotational_speed?: number;
  torque?: number;
  tool_wear?: number;
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
  date_debut?: string;
  date_fin?: string;
  rapport?: string;
  failure_type?: string;
}

export interface Intervention {
  id: number;
  date_intervention: string;
  statut?: string;
  technicien_id?: number;
  date_debut?: string;
  date_fin?: string;
  rapport: string;
  ordre_travail_id?: number;
  work_order_due_date?: string;
  is_overdue?: boolean;
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
  actual_failure_type?: string;
  ml_prediction_matched?: boolean;
  
  // New Diagnostic Fields
  machine_category?: string;
  symptoms?: string[];
  problem_start_time?: string;
  frequency?: string;
  operating_state?: string;
  temperature?: string;
  impact?: string;
  estimated_loss?: string;
  similar_issue_before?: boolean;

  // New Report & PDCA Fields
  intervention_type?: string;
  root_cause_category?: string;
  root_cause_description?: string;
  actions_performed?: string;
  parts_replaced?: string;
  tools_used?: string;
  machine_status_after?: string;
  plan_hypothesis?: string;
  check_resolved?: boolean;
  check_verification_method?: string;
  act_preventive_actions?: string;
  act_recommendations?: string;

  // AI Fields
  ai_failure_risk?: number;
  ai_recommended_action?: string;
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

// ── ML Fleet Dashboard Types ──

export interface SHAPExplanation {
  factor: string;
  impact: number;
  intensity: 'high' | 'medium' | 'low';
}

export interface MLPrediction {
  machine_id: number;
  machine_name: string;
  rul_days: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  failure_probability: number;
  predicted_failure_date: string;
  data_points: number;
  predicted_priority?: string;
  is_anomaly?: boolean;
  anomaly_score?: number;
  explanations?: SHAPExplanation[];
  health_score: number;
  reliability_score: number;
  mtbf_pred: number;
  mttr_pred: number;
  availability_pred: number;
  failure_type_predictions?: {
    TWF?: number;
    HDF?: number;
    PWF?: number;
    OSF?: number;
    RNF?: number;
  };
}

export interface FleetMachineCard {
  machine_id: number;
  machine_name: string;
  zone?: string;
  sous_zone?: string;
  statut?: string;
  rul_days: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  failure_probability: number;
  predicted_failure_date: string;
  data_points: number;
  ml_model_used?: boolean;
  predicted_priority?: string;
  is_anomaly?: boolean;
  anomaly_score?: number;
  explanations?: SHAPExplanation[];
  health_score: number;
  reliability_score: number;
  mtbf_pred: number;
  mttr_pred: number;
  availability_pred: number;
  air_temperature?: number;
  process_temperature?: number;
  rotational_speed?: number;
  torque?: number;
  tool_wear?: number;
  health_breakdown?: {
    predictive_risk: number;
    anomaly_penalty: number;
    maintenance_deduction: number;
    overdue_deduction: number;
    status_deduction: number;
    work_order_deduction: number;
    intervention_deduction: number;
    days_since_maintenance: number;
    open_work_orders: number;
    recent_interventions: number;
  };
}

export interface FleetDashboardResponse {
  machines: FleetMachineCard[];
  total_machines?: number;
  critical_count?: number;
  high_risk_count?: number;
  avg_health_score?: number;
  avg_reliability_score?: number;
}

export interface FleetCriticalResponse {
  machines: FleetMachineCard[];
  count?: number;
}