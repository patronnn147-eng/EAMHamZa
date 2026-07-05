import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock,
    TrendingDown,
    TrendingUp,
    Zap,
    ChevronRight,
} from 'lucide-react';
import type { Machine, Intervention } from '@/lib/types';
import {
    computeFleetReliability,
    computeFleetKpiTrends,
    formatDuration,
    formatHours,
    type FleetReliabilitySummary,
    type FleetKpiTrends,
} from './machines/utils/reliabilityMetrics';
import { KpiTrendCard } from './machines/components/KpiTrendCard';

function SimpleBar({ pct, colorClass }: { pct: number; colorClass: string }) {
    return (
        <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
                className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-700`}
                style={{ width: `${Math.min(100, pct)}%` }}
            />
        </div>
    );
}

const classificationConfig = {
    Excellent: { badge: 'bg-emerald-100 text-emerald-800', dot: 'bg-emerald-500' },
    Bon: { badge: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
    Moyen: { badge: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
    Critique: { badge: 'bg-red-100 text-red-800', dot: 'bg-red-500 animate-pulse' },
};

export const ReliabilityDashboardTab: React.FC = () => {
    const navigate = useNavigate();
    const [machines, setMachines] = useState<Machine[]>([]);
    const [interventions, setInterventions] = useState<Intervention[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                setLoading(true);
                const [machinesRes, intRes] = await Promise.all([
                    client.entities.machines.queryAll({ query: {}, limit: 200 }),
                    client.entities.ordres_intervention.queryAll({ query: {}, sort: '-date_intervention', limit: 800 }),
                ]);
                setMachines(machinesRes.data.items || []);
                setInterventions(intRes.data.items || []);
            } catch (err) {
                console.error('Fleet reliability load error:', err);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    const byMachine: Record<number, Intervention[]> = useMemo(() => {
        const grouped: Record<number, Intervention[]> = {};
        for (const i of interventions) {
            if (i.machine_id) {
                if (!grouped[i.machine_id]) grouped[i.machine_id] = [];
                grouped[i.machine_id].push(i);
            }
        }
        return grouped;
    }, [interventions]);

    const summary: FleetReliabilitySummary = useMemo(
        () => computeFleetReliability(machines, byMachine, 90),
        [machines, byMachine]
    );

    const kpiTrends: FleetKpiTrends = useMemo(
        () => computeFleetKpiTrends(machines, byMachine, 180, 13),
        [machines, byMachine]
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
            </div>
        );
    }

    const { entries, avgUptimePct, avgMttr, avgMtbf, totalDowntimeMinutes, criticalCount, goodCount } = summary;

    // Sort by reliability score ascending (worst first)
    const sortedEntries = [...entries].sort(
        (a, b) => a.metrics.reliabilityScore - b.metrics.reliabilityScore
    );

    return (
        <div className="space-y-6">
            {/* Fleet KPI row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiTrendCard
                    index={0}
                    label="Disponibilité moyenne"
                    icon={Activity}
                    valueFormatted={`${avgUptimePct.toFixed(1)}%`}
                    valueColorClass={avgUptimePct >= 95 ? 'text-emerald-600' : avgUptimePct >= 85 ? 'text-blue-600' : 'text-red-600'}
                    trend={kpiTrends.availability}
                    targetLabel="Cible 95%"
                    captionSuffix="Flotte complète · 90j"
                />
                <KpiTrendCard
                    index={1}
                    label="MTTR moyen"
                    icon={Zap}
                    valueFormatted={avgMttr !== null ? formatDuration(avgMttr) : 'N/A'}
                    trend={kpiTrends.mttr}
                    targetLabel="Cible 24h"
                    captionSuffix="Temps moyen de réparation"
                />
                <KpiTrendCard
                    index={2}
                    label="MTBF moyen"
                    icon={Clock}
                    valueFormatted={avgMtbf !== null ? formatHours(avgMtbf) : 'N/A'}
                    trend={kpiTrends.mtbf}
                    targetLabel="Cible 30j"
                    captionSuffix="Temps entre pannes"
                />
                <KpiTrendCard
                    index={3}
                    label="Arrêt total cumulé"
                    icon={TrendingDown}
                    valueFormatted={formatDuration(totalDowntimeMinutes)}
                    valueColorClass={totalDowntimeMinutes > 0 ? 'text-red-600' : 'text-emerald-600'}
                    trend={kpiTrends.downtime}
                    captionSuffix="Toutes machines · 90j"
                />
            </div>

            {/* Fleet health overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardContent className="pt-5">
                        <div className="flex items-center justify-between mb-4">
                            <p className="font-semibold text-blue-50">Vue d'ensemble flotte</p>
                            <span className="text-xs text-blue-400">{machines.length} machines</span>
                        </div>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                                    <span className="text-sm text-blue-200">Fiables (Excellent + Bon)</span>
                                </div>
                                <span className="font-bold text-emerald-600">{goodCount}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse inline-block" />
                                    <span className="text-sm text-blue-200">Critiques</span>
                                </div>
                                <span className="font-bold text-red-600">{criticalCount}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" />
                                    <span className="text-sm text-blue-200">Moyennes</span>
                                </div>
                                <span className="font-bold text-amber-600">
                                    {entries.filter((e) => e.metrics.classification === 'Moyen').length}
                                </span>
                            </div>
                        </div>

                        {/* Mini distribution bar */}
                        <div className="mt-4 flex h-2.5 rounded-full overflow-hidden gap-0.5">
                            {goodCount > 0 && (
                                <div
                                    className="bg-emerald-400 rounded-full"
                                    style={{ flex: goodCount }}
                                    title={`${goodCount} fiables`}
                                />
                            )}
                            {entries.filter((e) => e.metrics.classification === 'Moyen').length > 0 && (
                                <div
                                    className="bg-amber-400 rounded-full"
                                    style={{ flex: entries.filter((e) => e.metrics.classification === 'Moyen').length }}
                                    title="Moyennes"
                                />
                            )}
                            {criticalCount > 0 && (
                                <div
                                    className="bg-red-500 rounded-full animate-pulse"
                                    style={{ flex: criticalCount }}
                                    title={`${criticalCount} critiques`}
                                />
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Alert: critical machines */}
                <Card className={criticalCount > 0 ? 'border-red-200 bg-red-50/50' : 'border-emerald-200 bg-emerald-50/50'}>
                    <CardContent className="pt-5">
                        {criticalCount > 0 ? (
                            <>
                                <div className="flex items-center gap-2 mb-3">
                                    <AlertTriangle className="h-5 w-5 text-red-500" />
                                    <p className="font-semibold text-red-800">{criticalCount} machine{criticalCount > 1 ? 's' : ''} critique{criticalCount > 1 ? 's' : ''}</p>
                                </div>
                                <div className="space-y-2">
                                    {sortedEntries
                                        .filter((e) => e.metrics.classification === 'Critique')
                                        .slice(0, 4)
                                        .map((e) => (
                                            <button
                                                type="button"
                                                key={e.machineId}
                                                className="flex w-full items-center justify-between p-2 rounded-lg bg-slate-800 border border-red-100 cursor-pointer text-left hover:border-red-300 transition-colors"
                                                onClick={() => navigate(`/machines/${e.machineId}`)}
                                            >
                                                <div>
                                                    <p className="text-sm font-semibold text-blue-50">{e.machineName}</p>
                                                    <p className="text-xs text-red-600">{e.metrics.failureCount} arrêts · {e.metrics.uptimePct.toFixed(1)}% dispo.</p>
                                                </div>
                                                <ChevronRight className="h-4 w-4 text-blue-400" />
                                            </button>
                                        ))}
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full py-4 text-center">
                                <CheckCircle2 className="h-10 w-10 text-emerald-400 mb-2" />
                                <p className="font-semibold text-emerald-800">Toutes les machines sont fiables</p>
                                <p className="text-xs text-emerald-600 mt-1">Aucun état critique détecté sur la flotte</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Per-machine reliability table */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-blue-300" />
                        Fiabilité par Machine
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {entries.length === 0 ? (
                        <p className="text-center text-blue-400 py-8">Aucune machine trouvée</p>
                    ) : (
                        <div className="space-y-2">
                            {sortedEntries.map((entry) => {
                                const cfg = classificationConfig[entry.metrics.classification];
                                return (
                                    <div
                                        key={entry.machineId}
                                        className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-800/50 cursor-pointer border border-transparent hover:border-blue-700/50 transition-colors"
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => navigate(`/machines/${entry.machineId}`)}
                                        onKeyDown={(ev) => {
                                            if (ev.key === 'Enter' || ev.key === ' ') {
                                                ev.preventDefault();
                                                navigate(`/machines/${entry.machineId}`);
                                            }
                                        }}
                                    >
                                        {/* Status dot */}
                                        <span className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />

                                        {/* Machine name */}
                                        <div className="min-w-[160px] max-w-[200px]">
                                            <p className="font-semibold text-sm text-blue-50 truncate">{entry.machineName}</p>
                                        </div>

                                        {/* Score bar */}
                                        <div className="flex-1 space-y-1 hidden sm:block">
                                            <SimpleBar pct={entry.metrics.reliabilityScore} colorClass={entry.metrics.colorClass} />
                                        </div>

                                        {/* Score number */}
                                        <span className="text-sm font-bold text-blue-100 w-12 text-right shrink-0">
                                            {entry.metrics.reliabilityScore}/100
                                        </span>

                                        {/* Uptime */}
                                        <span className="text-xs text-blue-300 w-16 text-right shrink-0 hidden md:inline">
                                            {entry.metrics.uptimePct.toFixed(1)}% dispo.
                                        </span>

                                        {/* Classification badge */}
                                        <Badge className={`text-xs px-2 py-0.5 shrink-0 ${cfg.badge}`}>
                                            {entry.metrics.classification}
                                        </Badge>

                                        {/* View button */}
                                        <Button variant="ghost" size="sm" className="shrink-0 p-1.5 h-auto">
                                            <ChevronRight className="h-4 w-4" />
                                        </Button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default ReliabilityDashboardTab;
