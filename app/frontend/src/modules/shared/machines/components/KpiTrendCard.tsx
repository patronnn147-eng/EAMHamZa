import React, { useId } from 'react';
import { motion } from 'framer-motion';
import {
    AreaChart,
    Area,
    XAxis,
    ReferenceLine,
    Tooltip as RechartsTooltip,
    ResponsiveContainer,
} from 'recharts';
import { Card, CardContent } from '@/components/ui/card';
import type { KpiTrend } from '../utils/reliabilityMetrics';

interface KpiTrendCardProps {
    label: string;
    icon: React.ElementType;
    valueFormatted: string;
    valueColorClass?: string;
    trend: KpiTrend;
    targetLabel?: string;
    captionSuffix: string;
    index?: number;
}

function formatDateTick(value: string): string {
    const d = new Date(value);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
}

export const KpiTrendCard: React.FC<KpiTrendCardProps> = ({
    label,
    icon: Icon,
    valueFormatted,
    valueColorClass = 'text-blue-50',
    trend,
    targetLabel,
    captionSuffix,
    index = 0,
}) => {
    const gradientId = useId();

    const isFavorable =
        trend.pctChange === null
            ? null
            : trend.goodDirection === 'up'
                ? trend.pctChange > 0
                : trend.pctChange < 0;

    const chartColor = isFavorable === null ? '#60a5fa' : isFavorable ? '#34d399' : '#f87171';
    const badgeColorClass =
        isFavorable === null
            ? 'bg-blue-500/15 text-blue-300'
            : isFavorable
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-red-500/15 text-red-400';
    const arrow = trend.pctChange === null ? '—' : trend.pctChange > 0 ? '▲' : trend.pctChange < 0 ? '▼' : '—';

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: index * 0.08 }}
        >
            <Card>
                <CardContent className="pt-5 pb-3">
                    <div className="flex items-start justify-between mb-1">
                        <div className="flex items-center gap-1.5">
                            <Icon className="h-3.5 w-3.5 text-blue-400" />
                            <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">{label}</p>
                        </div>
                        {trend.pctChange !== null && (
                            <span
                                className={`inline-flex items-center gap-0.5 text-[11px] font-bold rounded-full px-2 py-0.5 shrink-0 ${badgeColorClass}`}
                            >
                                {arrow} {Math.abs(trend.pctChange).toFixed(1)}%
                            </span>
                        )}
                    </div>

                    <p className={`text-2xl font-black ${valueColorClass}`}>{valueFormatted}</p>

                    <div className="h-[65px] -ml-2 mt-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={trend.series} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                                <defs>
                                    <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={chartColor} stopOpacity={0.4} />
                                        <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="date"
                                    tick={{ fontSize: 10, fill: '#93c5fd' }}
                                    axisLine={false}
                                    tickLine={false}
                                    interval="preserveStartEnd"
                                    tickFormatter={formatDateTick}
                                />
                                {trend.target !== null && (
                                    <ReferenceLine
                                        y={trend.target}
                                        stroke="#93c5fd"
                                        strokeDasharray="3 3"
                                        strokeOpacity={0.6}
                                    />
                                )}
                                <RechartsTooltip
                                    contentStyle={{ borderRadius: 8, border: 'none', fontSize: 12 }}
                                    labelFormatter={(value: string) => new Date(value).toLocaleDateString('fr-FR')}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={chartColor}
                                    strokeWidth={2}
                                    fill={`url(#${gradientId})`}
                                    connectNulls={false}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    <p className="text-xs text-blue-400 mt-0.5">
                        {targetLabel ? `${targetLabel} · ` : ''}
                        {captionSuffix}
                    </p>
                </CardContent>
            </Card>
        </motion.div>
    );
};

export default KpiTrendCard;
