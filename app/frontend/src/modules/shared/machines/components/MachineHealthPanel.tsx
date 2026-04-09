import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Calendar, Wrench, Zap, AlertTriangle, Info, Heart, Activity } from 'lucide-react';
import MachineHealthBar from './MachineHealthBar';
import type { HealthScoreResult } from '../utils/healthScore';
import { formatDuration } from '../utils/healthScore';

interface MachineHealthPanelProps {
    health: HealthScoreResult;
}

/**
 * Full health breakdown panel for the Machine Detail page.
 */
const MachineHealthPanel: React.FC<MachineHealthPanelProps> = ({ health }) => {
    const { score, factors, textColor, iconColor } = health;
    const { daysSinceLastMaintenance, openWorkOrders, recentInterventions, isDown } = factors;

    const factorRows = [
        {
            icon: Calendar,
            label: 'Dernière maintenance',
            value: formatDuration(daysSinceLastMaintenance),
            deduction: health.deductions.maintenance,
        },
        ...(health.deductions.overdue > 0 ? [{
            icon: AlertTriangle,
            label: 'Maintenance en retard',
            value: 'À FAIRE IMMÉDIATEMENT',
            deduction: health.deductions.overdue,
        }] : []),
        {
            icon: Wrench,
            label: "Ordres de travail ouverts",
            value: `${openWorkOrders} actif${openWorkOrders !== 1 ? 's' : ''}`,
            deduction: health.deductions.workOrders,
        },
        {
            icon: Zap,
            label: 'Interventions (30 jours)',
            value: `${recentInterventions} intervention${recentInterventions !== 1 ? 's' : ''}`,
            deduction: health.deductions.interventions,
        },
        ...(isDown
            ? [
                {
                    icon: AlertTriangle,
                    label: 'Statut machine',
                    value: 'EN PANNE / HORS SERVICE',
                    deduction: health.deductions.status,
                },
            ]
            : []),
        ...(health.deductions.predictive > 0 ? [{
            icon: Activity,
            label: 'Risque prédictif (IA)',
            value: health.deductions.predictive > 20 ? 'ÉLEVÉ' : 'MODÉRÉ',
            deduction: health.deductions.predictive,
        }] : []),
    ];

    return (
        <Card className="border-0 shadow-lg overflow-hidden">
            {/* Colored top band */}
            <div className={`h-1.5 w-full bg-gradient-to-r ${health.colorClass}`} />

            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-base font-semibold text-blue-50">
                        <Heart className={`h-4 w-4 ${iconColor}`} />
                        Santé Machine
                    </CardTitle>
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <button className="text-blue-400 hover:text-blue-200 transition-colors">
                                    <Info className="h-4 w-4" />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="left" className="max-w-[280px] text-xs">
                                <p className="font-semibold mb-1">Score de Santé Intelligent (IA) :</p>
                                <ul className="space-y-1 list-disc px-3">
                                    <li>Analyse multi-modèle (P1-P6)</li>
                                    <li>Télémétrie en temps réel (Temp, RPM, Couple)</li>
                                    <li>Indice de dérive et détection d'anomalies</li>
                                    <li>Fusion des cycles de maintenance réels</li>
                                </ul>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                </div>
            </CardHeader>

            <CardContent className="space-y-5">
                {/* Big Score */}
                <div className="text-center py-2">
                    <div className={`text-6xl font-black tracking-tight ${textColor}`}>{score}</div>
                    <div className="text-sm text-blue-400 font-medium">sur 100</div>
                </div>

                {/* Bar */}
                <MachineHealthBar health={health} />

                {/* Factors breakdown */}
                <div className="space-y-2 pt-1">
                    <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Facteurs</p>
                    {factorRows.map((row) => (
                        <div
                            key={row.label}
                            className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2"
                        >
                            <div className="flex items-center gap-2">
                                <row.icon className={`h-3.5 w-3.5 ${row.deduction > 15 ? 'text-red-400' : 'text-blue-400'}`} />
                                <span className="text-xs text-blue-200">{row.label}</span>
                            </div>
                            <div className="text-right">
                                <span className="text-xs font-semibold text-blue-100">{row.value}</span>
                                {row.deduction > 0 && (
                                    <span className="ml-2 text-xs text-red-500 font-bold">−{Math.round(row.deduction)}</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default MachineHealthPanel;
