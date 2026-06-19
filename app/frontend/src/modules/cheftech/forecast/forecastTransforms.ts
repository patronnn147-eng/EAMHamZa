export function formatHours(h: number): string {
  return `${Math.round(h * 10) / 10} h`;
}

export function formatCurrency(eur: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(eur);
}

export function labelOverload(overload: boolean): string {
  return overload ? '⚠ Capacité dépassée !' : 'Capacité suffisante';
}
