import { Badge } from '@/components/ui/badge';

const PRIORITY_CONFIG: Record<string, { label: string; className: string }> = {
  CRITIQUE: { label: 'Critique', className: 'bg-red-100 text-red-800 border-red-300' },
  HAUTE: { label: 'Haute', className: 'bg-orange-100 text-orange-800 border-orange-300' },
  MOYENNE: { label: 'Moyenne', className: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  BASSE: { label: 'Basse', className: 'bg-green-100 text-green-800 border-green-300' },
};

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  EN_ATTENTE: { label: 'En attente', className: 'bg-gray-100 text-gray-800 border-gray-300' },
  ASSIGNÉ: { label: 'Assigné', className: 'bg-blue-100 text-blue-800 border-blue-300' },
  EN_COURS: { label: 'En cours', className: 'bg-amber-100 text-amber-800 border-amber-300' },
  TERMINÉ: { label: 'Terminé', className: 'bg-green-100 text-green-800 border-green-300' },
  BLOQUÉ: { label: 'Bloqué', className: 'bg-red-100 text-red-800 border-red-300' },
  ANNULÉ: { label: 'Annulé', className: 'bg-slate-100 text-slate-600 border-slate-300' },
};

export function PriorityBadge({ priorite }: Readonly<{ priorite: string }>) {
  const config = PRIORITY_CONFIG[priorite] ?? { label: priorite, className: 'bg-gray-100 text-gray-700' };
  return <Badge className={config.className}>{config.label}</Badge>;
}

export function StatusBadge({ statut }: Readonly<{ statut: string }>) {
  const config = STATUS_CONFIG[statut] ?? { label: statut, className: 'bg-gray-100 text-gray-700' };
  return <Badge className={config.className}>{config.label}</Badge>;
}
