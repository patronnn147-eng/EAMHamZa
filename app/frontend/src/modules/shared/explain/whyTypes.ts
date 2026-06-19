export type WhyTone = 'critical' | 'warning' | 'normal' | 'info';
export interface WhyReason { label: string; detail?: string; tone?: WhyTone }
export interface WhyConfidence { level: 'Faible' | 'Moyenne' | 'Élevée'; note: string }
export interface WhyPayload {
  title: string;
  summary: string;
  reasons: WhyReason[];
  confidence?: WhyConfidence;
  counterfactual?: WhyReason[];
  source: string;
  llmContext?: Record<string, unknown>;
}
