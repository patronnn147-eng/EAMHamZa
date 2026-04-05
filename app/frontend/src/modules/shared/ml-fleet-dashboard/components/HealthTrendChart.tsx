import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';

interface HealthTrendData {
  date: string;
  health_score: number;
  rul: number;
}

interface HealthTrendChartProps {
  data: HealthTrendData[];
}

export const HealthTrendChart: React.FC<HealthTrendChartProps> = ({ data }) => {
  return (
    <Card className="border-gray-100 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-blue-500" />
          Tendance Santé & RUL
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.4} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickMargin={8}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => {
                  const d = new Date(value);
                  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
                }}
              />
              <YAxis
                yAxisId="left"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip
                contentStyle={{
                  borderRadius: '8px',
                  border: 'none',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
                labelFormatter={(label) => new Date(label).toLocaleDateString('fr-FR')}
              />
              <Legend iconType="circle" />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="health_score"
                name="Score Santé"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="rul"
                name="RUL (jours)"
                fill="#3b82f6"
                fillOpacity={0.15}
                stroke="#3b82f6"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
