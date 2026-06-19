import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { rankNextBestActions, NbaInput } from './rankNextBestActions';

const SEV: Record<string, string> = {
  critical: 'border-red-500 bg-red-900/40 text-red-200',
  high: 'border-amber-500 bg-amber-900/40 text-amber-200',
  medium: 'border-blue-500 bg-blue-900/40 text-blue-200',
};

export function NextBestActions(props: NbaInput) {
  const actions = rankNextBestActions(props);
  if (actions.length === 0) {
    return <p className="text-sm text-blue-300 py-2">Aucune action prioritaire. Tout est à jour.</p>;
  }
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-blue-300">Actions prioritaires</p>
      {actions.map((a) => {
        const border = a.severity === 'critical' ? 'border-l-red-500'
          : a.severity === 'high' ? 'border-l-amber-500' : 'border-l-blue-500';
        return (
          <Link key={a.key} to={a.href}
            className={`flex items-center gap-3 rounded-md border border-slate-700 border-l-[3px] ${border} bg-slate-800 px-3 py-2 hover:bg-slate-700/60`}>
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${SEV[a.severity]}`}>
              {a.severity === 'critical' ? 'Critique' : a.severity === 'high' ? 'Urgent' : 'À faire'}
            </span>
            <span className="text-sm text-slate-100 flex-1">{a.label}</span>
            <ChevronRight className="h-4 w-4 text-slate-500" />
          </Link>
        );
      })}
    </div>
  );
}
