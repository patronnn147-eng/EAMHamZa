import type { WhyConfidence } from './whyTypes';

const SENSOR: Record<string, string> = {
  air_temperature: "température de l'air",
  process_temperature: 'température du procédé',
  rotational_speed: 'vitesse de rotation',
  torque: 'couple',
  tool_wear: "usure de l'outil",
};
const FAILURE: Record<string, string> = {
  TWF: "usure de l'outil",
  HDF: 'surchauffe',
  PWF: 'fluctuation de courant',
  OSF: 'surcharge',
  RNF: 'défaillance aléatoire',
};

export function sensorLabel(key: string): string {
  return SENSOR[key] ?? key.replace(/_/g, ' ');
}
export function failureLabel(code: string): string {
  return FAILURE[code] ?? code;
}
export function kToC(k: number): number {
  return Math.round((k - 273.15) * 10) / 10;
}
export function confidenceWords(conflictK: number): WhyConfidence {
  if (conflictK < 0.3) return { level: 'Élevée', note: 'toutes les vérifications sont d’accord' };
  if (conflictK < 0.7) return { level: 'Moyenne', note: 'la plupart des vérifications concordent' };
  return { level: 'Faible', note: 'les vérifications ne sont pas d’accord' };
}
// Banned ML jargon — producers' output must never match this.
export const NO_JARGON = /\b(SHAP|ensemble|DST|RUL|Kelvin|conflict|TWF|HDF|PWF|OSF|RNF)\b/i;
