import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
    BrainCircuit,
    AlertCircle,
    Calendar,
    TrendingDown,
    Zap,
    Info,
    ShieldAlert,
    Clock,
    ArrowUpCircle
} from 'lucide-react';
import { client } from '@/lib/api';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface XAIExplanation {
    factor: string;
    impact: number;
    intensity: 'high' | 'medium' | 'low';
}

interface MLPrediction {
    machine_id: number;
    machine_name: string;
    rul_days: number;
    risk_level: string;
    failure_probability: number;
    predicted_failure_date: string;
    data_points: number;
    predicted_priority?: string;
    is_anomaly?: boolean;
    anomaly_score?: number;
    explanations?: XAIExplanation[];
}

interface PredictivePanelProps {
    machineId: number;
}

const riskConfig: Record<string, { label: string; color: string; icon: any; bg: string }> = {
    CRITICAL: {
        label: 'Risque Critique',
        color: 'text-red-600',
        icon: AlertCircle,
        bg: 'bg-red-50 border-red-100'
    },
    HIGH: {
        label: 'Risque Élevé',
        color: 'text-orange-600',
        icon: AlertCircle,
        bg: 'bg-orange-50 border-orange-100'
    },
    MEDIUM: {
        label: 'Risque Modéré',
        color: 'text-amber-600',
        icon: TrendingDown,
        bg: 'bg-amber-50 border-amber-100'
    },
    LOW: {
        label: 'Risque Faible',
        color: 'text-emerald-600',
        icon: Zap,
        bg: 'bg-emerald-50 border-emerald-100'
    }
};

const priorityConfig: Record<string, { label: string; color: string; bg: string }> = {
    Critical: { label: 'Critique', color: 'text-red-700', bg: 'bg-red-100' },
    High: { label: 'Haute', color: 'text-orange-700', bg: 'bg-orange-100' },
    Medium: { label: 'Moyenne', color: 'text-amber-700', bg: 'bg-amber-100' },
    Low: { label: 'Basse', color: 'text-emerald-700', bg: 'bg-emerald-100' },
};

export const PredictivePanel: React.FC<PredictivePanelProps> = ({ machineId }) => {
    const [prediction, setPrediction] = useState<MLPrediction | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPrediction = async () => {
            try {
                setLoading(true);
                // Use relative path for API compatibility
                const response = await fetch(`/api/v1/ml/machines/${machineId}/prediction`);
                if (response.ok) {
                    const data = await response.json();
                    setPrediction(data);
                }
            } catch (error) {
                console.error('Failed to fetch ML prediction:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchPrediction();
    }, [machineId]);

    if (loading) {
        return (
            <div className="animate-pulse space-y-4">
                <div className="h-40 bg-gray-100 rounded-xl" />
            </div>
        );
    }

    if (!prediction) return null;

    const config = riskConfig[prediction.risk_level] || riskConfig.LOW;
    const RiskIcon = config.icon;
    const pConfig = priorityConfig[prediction.predicted_priority || 'Medium'] || priorityConfig.Medium;

    return (
        <Card className="overflow-hidden border-blue-100 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-gray-50 flex flex-row items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-blue-50 rounded-lg">
                        <BrainCircuit className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base font-bold text-gray-800">Prédiction IA (Maintenance Prédictive)</CardTitle>
                        <p className="text-xs text-gray-400">Basé sur {prediction.data_points} points de données historiques</p>
                    </div>
                </div>
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button className="text-gray-400 hover:text-gray-600">
                                <Info className="h-4 w-4" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[250px] text-xs">
                            Cette prédiction utilise 6 modèles ML (P1-P6) pour analyser le risque de panne, le type de défaillance, la durée de vie restante, les anomalies, la priorité et la planification.
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            </CardHeader>
            <CardContent className="pt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Key Stats */}
                    <div className="space-y-6">
                        <div className={`p-4 rounded-xl border ${config.bg} flex items-start gap-4`}>
                            <RiskIcon className={`h-6 w-6 ${config.color} shrink-0`} />
                            <div>
                                <p className={`font-bold text-sm ${config.color}`}>{config.label}</p>
                                <p className="text-2xl font-black text-gray-900 mt-1">
                                    {prediction.rul_days} <span className="text-sm font-medium text-gray-500">Jours restants</span>
                                </p>
                                <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-500">
                                    <Calendar className="h-3.5 w-3.5" />
                                    <span>Panne probable : {new Date(prediction.predicted_failure_date).toLocaleDateString()}</span>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-end">
                                <p className="text-sm font-semibold text-gray-700">Probabilité de Défaillance</p>
                                <p className={`text-sm font-bold ${prediction.failure_probability > 70 ? 'text-red-600' : 'text-gray-600'}`}>
                                    {prediction.failure_probability}%
                                </p>
                            </div>
                            <Progress
                                value={prediction.failure_probability}
                                className={`h-2 bg-gray-100 ${prediction.failure_probability > 70 ? '[&>div]:bg-red-500' : '[&>div]:bg-blue-500'}`}
                            />
                        </div>

                        {/* P5: Suggested Priority */}
                        <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 border border-gray-100">
                            <div className="flex items-center gap-2">
                                <ArrowUpCircle className="h-4 w-4 text-gray-500" />
                                <span className="text-sm font-medium text-gray-600">Priorité Suggérée (P5)</span>
                            </div>
                            <Badge className={`${pConfig.bg} ${pConfig.color} border-0 font-semibold`}>
                                {pConfig.label}
                            </Badge>
                        </div>

                        {/* XAI: Risk Factors */}
                        {prediction.explanations && prediction.explanations.length > 0 && (
                            <div className="space-y-3 pt-2">
                                <div className="flex items-center gap-2">
                                    <BrainCircuit className="h-4 w-4 text-blue-500" />
                                    <span className="text-sm font-bold text-gray-700">Facteurs de Risque IA (SHAP)</span>
                                </div>
                                <div className="space-y-2">
                                    {prediction.explanations.map((exp, idx) => (
                                        <div key={idx} className="flex items-center justify-between text-xs p-2 bg-white border border-gray-100 rounded-md shadow-sm">
                                            <span className="font-medium text-gray-600">{exp.factor}</span>
                                            <Badge variant="outline" className={`
                                                ${exp.intensity === 'high' ? 'text-red-600 border-red-200 bg-red-50' :
                                                    exp.intensity === 'medium' ? 'text-orange-600 border-orange-200 bg-orange-50' :
                                                        'text-blue-600 border-blue-200 bg-blue-50'}
                                                capitalize py-0 px-1.5 text-[10px]
                                            `}>
                                                {exp.intensity}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column: Anomaly + Recommendations */}
                    <div className="space-y-4">
                        {/* P4: Anomaly Detection */}
                        <div className={`p-4 rounded-xl border ${prediction.is_anomaly ? 'bg-purple-50 border-purple-200' : 'bg-gray-50 border-gray-100'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <ShieldAlert className={`h-4 w-4 ${prediction.is_anomaly ? 'text-purple-600' : 'text-gray-400'}`} />
                                <p className={`text-xs font-bold uppercase tracking-wider ${prediction.is_anomaly ? 'text-purple-600' : 'text-gray-400'}`}>
                                    Détection d'Anomalie (P4)
                                </p>
                            </div>
                            {prediction.is_anomaly ? (
                                <div className="space-y-1">
                                    <Badge variant="destructive" className="bg-purple-600 animate-pulse">⚠️ Anomalie Détectée</Badge>
                                    <p className="text-xs text-purple-700 mt-2">
                                        Score: {prediction.anomaly_score?.toFixed(4)} — Les capteurs montrent un comportement anormal.
                                    </p>
                                </div>
                            ) : (
                                <p className="text-xs text-gray-500">Aucune anomalie détectée. Tous les capteurs fonctionnent normalement.</p>
                            )}
                        </div>

                        {/* P6: Scheduling Info */}
                        <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100 flex items-center gap-3">
                            <Clock className="h-4 w-4 text-blue-500 shrink-0" />
                            <div>
                                <p className="text-xs font-bold text-blue-700 uppercase tracking-wider">Planification (P6)</p>
                                <p className="text-sm text-gray-700 mt-0.5">
                                    Maintenance recommandée dans <span className="font-bold text-blue-700">{Math.max(0, Math.round(prediction.rul_days * 0.8))} jours</span>
                                </p>
                            </div>
                        </div>

                        {/* Recommendations */}
                        <div className="bg-gray-50/50 rounded-xl p-4 border border-gray-100 space-y-3">
                            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Action recommandée</p>

                            {prediction.risk_level === 'CRITICAL' || prediction.risk_level === 'HIGH' ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-gray-700 leading-relaxed">
                                        <span className="font-bold text-red-600">Urgent :</span> Un arrêt non planifié est imminent.
                                        Vérifiez les ordres de travail ouverts et programmez une inspection technique sous 48h.
                                    </p>
                                    <Badge variant="destructive" className="animate-pulse">Inspection Prioritaire</Badge>
                                </div>
                            ) : prediction.risk_level === 'MEDIUM' ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-gray-700 leading-relaxed">
                                        <span className="font-bold text-amber-600">Vigilance :</span> La dégradation de santé s'accélère.
                                        Assurez-vous que la maintenance préventive est à jour.
                                    </p>
                                    <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">Planifier révision</Badge>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <p className="text-sm text-gray-700 leading-relaxed">
                                        <span className="font-bold text-emerald-600">Stable :</span> Les indicateurs sont au vert. Continuez le suivi périodique normal.
                                    </p>
                                    <div className="flex items-center gap-2 text-emerald-600">
                                        <Zap className="h-4 w-4" />
                                        <span className="text-xs font-bold">Optimisation continue</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
