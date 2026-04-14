import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  ComposedChart,
  Area
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Download, TrendingUp, Activity, Thermometer, Gauge, Zap } from 'lucide-react';

interface TelemetryPoint {
  timestamp: string;
  value: number;
}

interface TrendChartProps {
  data: TelemetryPoint[];
  metric: string;
  unit: string;
  thresholds?: {
    warning: number;
    critical: number;
  };
  title?: string;
  height?: number;
}

const metricIcons: Record<string, React.ReactNode> = {
  temperature: <Thermometer className="h-4 w-4" />,
  vibration: <Activity className="h-4 w-4" />,
  rpm: <Gauge className="h-4 w-4" />,
  torque: <TrendingUp className="h-4 w-4" />,
  power: <Zap className="h-4 w-4" />
};

const metricColors: Record<string, string> = {
  temperature: '#ef4444',
  vibration: '#f59e0b',
  rpm: '#10b981',
  torque: '#3b82f6',
  power: '#8b5cf6'
};

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  metric,
  unit,
  thresholds,
  title,
  height = 300
}) => {
  const [timeRange, setTimeRange] = useState<string>('7d');

  const getFilteredData = () => {
    if (!data || data.length === 0) return [];
    
    const now = new Date();
    let cutoff: Date;
    
    switch (timeRange) {
      case '1h':
        cutoff = new Date(now.getTime() - 60 * 60 * 1000);
        break;
      case '6h':
        cutoff = new Date(now.getTime() - 6 * 60 * 60 * 1000);
        break;
      case '24h':
        cutoff = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case '90d':
        cutoff = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        break;
      default:
        cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    }
    
    return data.filter(d => new Date(d.timestamp) >= cutoff);
  };

  const filteredData = getFilteredData();

  const getStats = () => {
    if (filteredData.length === 0) return { min: 0, max: 0, avg: 0 };
    const values = filteredData.map(d => d.value);
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length
    };
  };

  const stats = getStats();
  const color = metricColors[metric] || '#3b82f6';

  const exportCSV = () => {
    const headers = 'timestamp,value\n';
    const rows = filteredData
      .map(d => `${d.timestamp},${d.value}`)
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${metric}_${timeRange}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatXAxis = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeRange === '1h' || timeRange === '6h') {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {metricIcons[metric] || <Activity className="h-4 w-4" />}
            <CardTitle className="text-base">
              {title || `${metric.charAt(0).toUpperCase() + metric.slice(1)} Trend`}
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-[100px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1h">1 Hour</SelectItem>
                <SelectItem value="6h">6 Hours</SelectItem>
                <SelectItem value="24h">24 Hours</SelectItem>
                <SelectItem value="7d">7 Days</SelectItem>
                <SelectItem value="30d">30 Days</SelectItem>
                <SelectItem value="90d">90 Days</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={exportCSV}>
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Min</p>
            <p className="text-lg font-semibold">
              {stats.min.toFixed(1)} {unit}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Average</p>
            <p className="text-lg font-semibold">
              {stats.avg.toFixed(1)} {unit}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Max</p>
            <p className="text-lg font-semibold">
              {stats.max.toFixed(1)} {unit}
            </p>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              tick={{ fontSize: 12 }}
              className="text-xs"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(v) => `${v}${unit}`}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px'
              }}
              labelFormatter={(label) => new Date(label).toLocaleString()}
              formatter={(value: number) => [`${value.toFixed(2)} ${unit}`, metric]}
            />
            <Legend />
            {thresholds && (
              <>
                <ReferenceLine
                  y={thresholds.warning}
                  stroke="#f59e0b"
                  strokeDasharray="5 5"
                  label={{ value: 'Warning', fill: '#f59e0b', fontSize: 10 }}
                />
                <ReferenceLine
                  y={thresholds.critical}
                  stroke="#ef4444"
                  strokeDasharray="5 5"
                  label={{ value: 'Critical', fill: '#ef4444', fontSize: 10 }}
                />
              </>
            )}
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              fill={color}
              fillOpacity={0.1}
              strokeWidth={2}
              name={metric}
              dot={filteredData.length < 50}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

export default TrendChart;
