import React from 'react';
import { motion } from 'framer-motion';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { GroupedDatum } from './groupByField';

const DEFAULT_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#94a3b8', '#8b5cf6'];

interface DashboardPieChartCardProps {
  title: string;
  data: (GroupedDatum & { color?: string })[];
  emptyLabel?: string;
  index?: number;
}

export const DashboardPieChartCard: React.FC<DashboardPieChartCardProps> = ({
  title,
  data,
  emptyLabel = 'No data',
  index = 0,
}) => {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.08 }}
    >
      <Card>
        <CardHeader className="pb-0">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </CardHeader>
        <CardContent className="h-[260px]">
          {total === 0 ? (
            <div className="h-full flex items-center justify-center text-blue-400 text-sm">
              {emptyLabel}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }: { name: string; percent: number }) =>
                    `${name} (${(percent * 100).toFixed(0)}%)`
                  }
                >
                  {data.map((entry, i) => (
                    <Cell key={entry.name} fill={entry.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ borderRadius: 8, border: 'none', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default DashboardPieChartCard;
