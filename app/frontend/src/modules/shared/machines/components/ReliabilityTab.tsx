import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingDown, Clock, Zap, AlertTriangle, CheckCircle2, Timer, Activity } from 'lucide-react';
import type { ReliabilityMetrics, DowntimeEvent } from '../utils/reliabilityMetrics';
import { formatDuration, formatHours } from '../utils/reliabilityMetrics';

interface ReliabilityTabProps {
    metrics: ReliabilityMetrics;
    machineName: string;
}

function ClassificationBadge({ classification }: { classification: ReliabilityMetrics['classification'] }) {
    const config = {
        Excellent: { className: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2 },
        Bon: { className: 'bg-blue-100 text-blue-800 border-blue-200', icon: Activity },
        Moyen: { className: 'bg-amber-100 text-amber-800 border-amber-200', icon: AlertTriangle },
        Critique: { className: 'bg-red-100 text-red-800 border-red-200', icon: AlertTriangle },
    }[classification];
    const Icon = config.icon;
    return (
        <Badge className={`flex items-center gap-1.5 px-3 py-1.5 text-sm border ${config.className}`}>
            <Icon className="h-3.5 w-3.5" />
            {classification}
        </Badge>
    );
}

function MetricCard({
    label, value, sublabel, icon: Icon, colorClass = 'text-gray-800', tooltip,
}: {
    label: string;
    value: string;
    sublabel?: string;
    icon: React.ElementType;
    colorClass?: string;
    tooltip?: string;
}) {
    return (
        <Card className="flex-1" title={tooltip}>
            <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
                    <Icon className="h-4 w-4 text-gray-400" />
                </div>
                <p className={`mt-2 text-2xl font-black ${colorClass}`}>{value}</p>
                {sublabel && <p className="text-xs text-gray-400 mt-0.5">{sublabel}</p>}
            </CardContent>
        </Card>
    );
}

function UptimeGauge({ pct }: { pct: number }) {
    const color = pct >= 95 ? 'stroke-emerald-500' : pct >= 85 ? 'stroke-blue-500' : pct >= 70 ? 'stroke-amber-500' : 'stroke-red-500';
    const R = 40;
    const circumference = 2 * Math.PI * R;
    const arc = (pct / 100) * circumference;

    return (
        <div className="flex flex-col items-center justify-center py-4">
            <svg width="120" height="120" viewBox="0 0 100 100" className="-rotate-90">
                <circle cx="50" cy="50" r={R} fill="none" stroke="#e5e7eb" strokeWidth="10" />
                <circle
                    cx="50" cy="50" r={R} fill="none" strokeWidth="10"
                    strokeDasharray={`${arc} ${circumference - arc}`}
                    strokeLinecap="round"
                    className={`${color} transition-all duration-700`}
                />
            </svg>
            <div className="-mt-20 mb-16 text-center">
                <span className="text-2xl font-black text-gray-800">{pct.toFixed(1)}%</span>
                <p className="text-xs text-gray-400 mt-0.5">Disponibilité</p>
            </div>
        </div>
    );
}

function DowntimeTimeline({ events }: { events: DowntimeEvent[] }) {
    if (events.length === 0) {
        return (
            <div className="text-center py-10 text-gray-400">
                <CheckCircle2 className="h-10 w-10 mx-auto mb-2 text-emerald-400" />
                <p className="text-sm">Aucun arrêt enregistré sur la période</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {events.map((event) => (
                <div
                    key={event.id}
                    className="flex items-start gap-4 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:bg-red-50/30 transition-colors"
                >
                    {/* Duration pill */}
                    <div className="shrink-0 flex flex-col items-center justify-center bg-red-50 border border-red-200 rounded-lg px-3 py-2 min-w-[64px] text-center">
                        <Timer className="h-3.5 w-3.5 text-red-500 mb-0.5" />
                        <span className="text-sm font-bold text-red-700">{formatDuration(event.durationMinutes)}</span>
                    </div>

                    <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                            <p className="font-semibold text-sm text-gray-800">Intervention #{event.id}</p>
                            <p className="text-xs text-gray-400 shrink-0">
                                {event.start.toLocaleDateString('fr-FR')}
                            </p>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">
                            {event.start.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                            {' → '}
                            {event.end.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                        {event.rapport && (
                            <p className="text-xs text-gray-600 mt-1.5 line-clamp-2 leading-relaxed">
                                {event.rapport}
                            </p>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

export const ReliabilityTab: React.FC<ReliabilityTabProps> = ({ metrics, machineName }) => {
    const {
        mttr, mtbf, uptimePct, totalDowntimeMinutes,
        failureCount, downtimeEvents, reliabilityScore, classification, colorClass, windowDays
    } = metrics;

    return (
        <div className="space-y-6">
            {/* Header summary */}
            <Card className="overflow-hidden">
                {/* Colored top bar */}
                <div className={`h-1.5 w-full bg-gradient-to-r ${colorClass}`} />
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div>
                            <CardTitle className="text-base flex items-center gap-2">
                                <Activity className="h-4 w-4 text-gray-500" />
                                Fiabilité — {machineName}
                            </CardTitle>
                            <p className="text-xs text-gray-400 mt-0.5">Analyse sur les {windowDays} derniers jours</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="text-right">
                                <span className="text-3xl font-black text-gray-900">{reliabilityScore}</span>
                                <span className="text-gray-400 text-sm">/100</span>
                            </div>
                            <ClassificationBadge classification={classification} />
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Reliability score bar */}
                    <div className="space-y-1.5">
                        <div className="flex justify-between text-xs text-gray-500">
                            <span>Score de fiabilité</span>
                            <span>{reliabilityScore}/100</span>
                        </div>
                        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                                className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-700`}
                                style={{ width: `${reliabilityScore}%` }}
                            />
                        </div>
                        <div className="flex justify-between text-xs text-gray-400">
                            <span>Critique</span>
                            <span>Moyen</span>
                            <span>Bon</span>
                            <span>Excellent</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* KPI row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                    label="MTTR"
                    value={mttr !== null ? formatDuration(mttr) : 'N/A'}
                    sublabel="Temps moyen de réparation"
                    icon={Zap}
                    colorClass={mttr !== null && mttr > 240 ? 'text-red-600' : 'text-gray-800'}
                    tooltip="Mean Time To Repair — durée moyenne d'une intervention"
                />
                <MetricCard
                    label="MTBF"
                    value={mtbf !== null ? formatHours(mtbf) : 'N/A'}
                    sublabel="Temps entre pannes"
                    icon={Clock}
                    colorClass={mtbf !== null && mtbf < 48 ? 'text-red-600' : 'text-emerald-600'}
                    tooltip="Mean Time Between Failures — intervalle moyen entre deux pannes"
                />
                <MetricCard
                    label="Arrêts"
                    value={String(failureCount)}
                    sublabel={`sur ${windowDays} jours`}
                    icon={AlertTriangle}
                    colorClass={failureCount === 0 ? 'text-emerald-600' : failureCount > 5 ? 'text-red-600' : 'text-amber-600'}
                />
                <MetricCard
                    label="Temps d'arrêt"
                    value={formatDuration(totalDowntimeMinutes)}
                    sublabel="total sur la période"
                    icon={TrendingDown}
                    colorClass={totalDowntimeMinutes === 0 ? 'text-emerald-600' : 'text-red-600'}
                />
            </div>

            {/* Uptime gauge + downtime timeline */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Uptime gauge */}
                <Card className="md:col-span-1 flex flex-col items-center justify-center">
                    <CardHeader className="pb-0 text-center w-full">
                        <CardTitle className="text-sm text-gray-600">Taux de disponibilité</CardTitle>
                    </CardHeader>
                    <CardContent className="w-full">
                        <UptimeGauge pct={uptimePct} />
                        <p className="text-center text-xs text-gray-400 -mt-4">
                            {formatDuration(totalDowntimeMinutes)} d'arrêt cumulé
                        </p>
                    </CardContent>
                </Card>

                {/* Downtime timeline */}
                <Card className="md:col-span-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center justify-between">
                            <span className="flex items-center gap-2">
                                <Timer className="h-4 w-4 text-gray-400" />
                                Historique des Arrêts
                            </span>
                            {downtimeEvents.length > 0 && (
                                <Badge variant="secondary">{downtimeEvents.length}</Badge>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <DowntimeTimeline events={downtimeEvents} />
                    </CardContent>
                </Card>
            </div>

            {/* Interpretation guide */}
            <Card className="bg-blue-50 border-blue-100">
                <CardContent className="pt-4 pb-4">
                    <p className="text-xs font-semibold text-blue-700 mb-2">💡 Comprendre les métriques</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1.5 text-xs text-blue-600">
                        <p><strong>MTTR</strong> — Plus il est court, plus les réparations sont rapides.</p>
                        <p><strong>MTBF</strong> — Plus il est long, plus la machine est fiable.</p>
                        <p><strong>Disponibilité</strong> — % du temps où la machine est opérationnelle.</p>
                        <p><strong>Score de fiabilité</strong> — Combinaison pondérée uptime + fréquence pannes.</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default ReliabilityTab;
