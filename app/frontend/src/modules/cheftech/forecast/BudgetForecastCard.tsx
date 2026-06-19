import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency } from './forecastTransforms';

interface BudgetData {
  labor_cost: number;
  parts_cost: number;
  total: number;
  currency: string;
  breakdown: { label: string; value: number }[];
}

interface Props { data: BudgetData }

const COLORS = ['#60a5fa', '#f59e0b'];

export function BudgetForecastCard({ data }: Props) {
  const pieData = data.breakdown.filter(b => b.value > 0);

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Budget estimé</p>
      <div className="flex items-center gap-4">
        {pieData.length > 0 ? (
          <ResponsiveContainer width={120} height={120}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={50} innerRadius={30}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                formatter={(v: number) => [formatCurrency(v)]}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-[120px] h-[120px] flex items-center justify-center text-xs text-slate-500">—</div>
        )}
        <div className="flex-1 space-y-2">
          {data.breakdown.map((b, i) => (
            <div key={b.label} className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs text-slate-300">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: COLORS[i % COLORS.length] }} />
                {b.label}
              </span>
              <span className="text-sm font-semibold text-slate-100">{formatCurrency(b.value)}</span>
            </div>
          ))}
          <div className="border-t border-slate-700 pt-2 flex justify-between">
            <span className="text-xs text-slate-300 font-semibold">Total</span>
            <span className="text-base font-bold text-blue-300">{formatCurrency(data.total)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
