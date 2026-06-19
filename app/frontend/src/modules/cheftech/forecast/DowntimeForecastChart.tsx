import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface MachineDowntime {
  machine_name: string;
  p_failure: number;
  expected_downtime_hours: number;
}

interface Props {
  machines: MachineDowntime[];
}

function riskColor(p: number): string {
  if (p >= 0.7) return '#f87171';
  if (p >= 0.4) return '#fbbf24';
  return '#34d399';
}

export function DowntimeForecastChart({ machines }: Props) {
  const data = machines.slice(0, 10).map(m => ({
    name: m.machine_name.length > 14 ? m.machine_name.slice(0, 14) + '…' : m.machine_name,
    heures: m.expected_downtime_hours,
    p: m.p_failure,
  }));

  if (!data.length) return (
    <div className="h-40 flex items-center justify-center text-slate-400 text-sm">Aucune donnée</div>
  );

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Arrêts attendus par machine</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} unit=" h" />
          <YAxis dataKey="name" type="category" tick={{ fill: '#cbd5e1', fontSize: 11 }} width={110} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number) => [`${v.toFixed(1)} h`, 'Arrêt attendu']}
          />
          <Bar dataKey="heures" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={riskColor(d.p)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
