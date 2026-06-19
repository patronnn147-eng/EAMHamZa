import { DashboardFilterState } from './dashboardFilters';

const RANGES: DashboardFilterState['range'][] = ['7d', '30d', '90d'];
const LABEL: Record<string, string> = { '7d': '7 jours', '30d': '30 jours', '90d': '90 jours' };

export function DashboardFilters({
  value, onChange,
}: { value: DashboardFilterState; onChange: (v: DashboardFilterState) => void }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {RANGES.map((r) => (
        <button key={r} onClick={() => onChange({ ...value, range: r })}
          className={`text-xs px-3 py-1.5 rounded-md ${
            value.range === r ? 'bg-blue-600 text-white' : 'bg-slate-800 text-blue-300'}`}>
          {LABEL[r]}
        </button>
      ))}
    </div>
  );
}
