import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle } from 'lucide-react';
import { formatHours } from './forecastTransforms';

interface LaborData {
  demand_hours: number;
  capacity_hours: number;
  coverage_pct: number;
  overload: boolean;
  technician_count: number;
  workdays: number;
  breakdown: { predicted_failure_hours: number; open_wo_backlog_hours: number };
}

interface Props { data: LaborData; horizon: number }

export function LaborForecastChart({ data, horizon }: Readonly<Props>) {
  const chartData = [
    { name: `${horizon}j`, demande: data.demand_hours, capacité: data.capacity_hours },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Main-d'œuvre</p>
        {data.overload && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-900/40 rounded px-2 py-0.5">
            <AlertTriangle className="h-3 w-3" /> Surcharge prévue
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit=" h" />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number) => [`${v.toFixed(0)} h`]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="demande" fill="#f87171" radius={[4, 4, 0, 0]} />
          <Bar dataKey="capacité" fill="#34d399" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-3 gap-2 text-center mt-1">
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Demande</p>
          <p className="text-sm font-bold text-red-300">{formatHours(data.demand_hours)}</p>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Capacité</p>
          <p className="text-sm font-bold text-emerald-300">{formatHours(data.capacity_hours)}</p>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Couverture</p>
          <p className={`text-sm font-bold ${data.overload ? 'text-amber-300' : 'text-emerald-300'}`}>
            {data.coverage_pct}%
          </p>
        </div>
      </div>
    </div>
  );
}
