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
    ArrowUpCircle,
    ChevronDown,
    ChevronUp,
    Activity
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface XAIExplanation {
    factor: string;
    impact: number;
    intensity: 'high' | 'medium' | 'low';
}

interface ModelOutputEntry {
    health_index?: number;
    rul_estimate?: number;
    uncertainty?: number;
    is_anomaly?: boolean;
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
    health_score: number;
    reliability_score: number;
    mtbf_pred: number;
    mttr_pred: number;
    availability_pred: number;
    // DST fusion fields (from /unified-health)
    unified_health_score?: number;
    dst_verdict?: string;
    conflict_factor_K?: number;
    kalman_hi?: number;
    kalman_rul?: number;
    sensor_fault_flag?: boolean;
    model_outputs?: {
        pinn_rul?: ModelOutputEntry | null;
        survival?: ModelOutputEntry | null;
        mahal_hi?: ModelOutputEntry | null;
        anomaly?: ModelOutputEntry | null;
    };
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
    const [showSignalBreakdown, setShowSignalBreakdown] = useState(false);

    useEffect(() => {
        const fetchPrediction = async () => {
            try {
                setLoading(true);
                // Try unified-health endpoint first (DST fusion), fall back to /prediction
                let data: MLPrediction | null = null;
                const unifiedRes = await fetch(`/api/v1/ml/machines/${machineId}/unified-health`);
                if (unifiedRes.ok) {
                    data = await unifiedRes.json();
                } else {
                    const fallbackRes = await fetch(`/api/v1/ml/machines/${machineId}/prediction`);
                    if (fallbackRes.ok) data = await fallbackRes.json();
                }
                setPrediction(data);
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
        <Card className="overflow-hidden border-blue-100 bg-slate-800 shadow-sm">
            <CardHeader className="pb-3 border-b border-gray-50 flex flex-row items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-blue-50 rounded-lg">
                        <BrainCircuit className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base font-bold text-blue-50">Prédiction IA (Maintenance Prédictive)</CardTitle>
                        <p className="text-xs text-blue-400">Basé sur {prediction.data_points} points de données historiques</p>
                    </div>
                </div>
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button className="text-blue-400 hover:text-blue-200">
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
                                <p className="text-2xl font-black text-white mt-1">
                                    {prediction.rul_days} <span className="text-sm font-medium text-blue-300">Jours restants</span>
                                </p>
                                <div className="flex items-center gap-1.5 mt-2 text-xs text-blue-300">
                                    <Calendar className="h-3.5 w-3.5" />
                                    <span>Panne probable : {new Date(prediction.predicted_failure_date).toLocaleDateString()}</span>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-end">
                                <p className="text-sm font-semibold text-blue-100">Probabilité de Défaillance</p>
                                <p className={`text-sm font-bold ${prediction.failure_probability > 70 ? 'text-red-600' : 'text-blue-200'}`}>
                                    {prediction.failure_probability}%
                                </p>
                            </div>
                            <Progress
                                value={prediction.failure_probability}
                                className={`h-2 bg-gray-100 ${prediction.failure_probability > 70 ? '[&>div]:bg-red-500' : '[&>div]:bg-blue-500'}`}
                            />
                        </div>

                        {/* P5: Suggested Priority */}
                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-blue-800/50">
                            <div className="flex items-center gap-2">
                                <ArrowUpCircle className="h-4 w-4 text-blue-300" />
                                <span className="text-sm font-medium text-blue-200">Priorité Suggérée (P5)</span>
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
                                    <span className="text-sm font-bold text-blue-100">Facteurs de Risque IA (SHAP)</span>
                                </div>
                                <div className="space-y-2">
                                    {prediction.explanations.map((exp, idx) => (
                                        <div key={idx} className="flex items-center justify-between text-xs p-2 bg-slate-800 border border-blue-800/50 rounded-md shadow-sm">
                                            <span className="font-medium text-blue-200">{exp.factor}</span>
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
                        <div className={`p-4 rounded-xl border ${prediction.is_anomaly ? 'bg-purple-50 border-purple-200' : 'bg-slate-800/50 border-blue-800/50'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <ShieldAlert className={`h-4 w-4 ${prediction.is_anomaly ? 'text-purple-600' : 'text-blue-400'}`} />
                                <p className={`text-xs font-bold uppercase tracking-wider ${prediction.is_anomaly ? 'text-purple-600' : 'text-blue-400'}`}>
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
                                <p className="text-xs text-blue-300">Aucune anomalie détectée. Tous les capteurs fonctionnent normalement.</p>
                            )}
                        </div>

                        {/* P6: Scheduling Info */}
                        <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100 flex items-center gap-3">
                            <Clock className="h-4 w-4 text-blue-500 shrink-0" />
                            <div>
                                <p className="text-xs font-bold text-blue-700 uppercase tracking-wider">Planification (P6)</p>
                                <p className="text-sm text-blue-100 mt-0.5">
                                    Maintenance recommandée dans <span className="font-bold text-blue-700">{Math.max(0, Math.round(prediction.rul_days * 0.8))} jours</span>
                                </p>
                            </div>
                        </div>

                        {/* Recommendations */}
                        <div className="bg-slate-800/50/50 rounded-xl p-4 border border-blue-800/50 space-y-3">
                            <p className="text-xs font-bold text-blue-400 uppercase tracking-wider">Action recommandée</p>

                            {prediction.risk_level === 'CRITICAL' || prediction.risk_level === 'HIGH' ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-blue-100 leading-relaxed">
                                        <span className="font-bold text-red-600">Urgent :</span> Un arrêt non planifié est imminent.
                                        Vérifiez les ordres de travail ouverts et programmez une inspection technique sous 48h.
                                    </p>
                                    <Badge variant="destructive" className="animate-pulse">Inspection Prioritaire</Badge>
                                </div>
                            ) : prediction.risk_level === 'MEDIUM' ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-blue-100 leading-relaxed">
                                        <span className="font-bold text-amber-600">Vigilance :</span> La dégradation de santé s'accélère.
                                        Assurez-vous que la maintenance préventive est à jour.
                                    </p>
                                    <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">Planifier révision</Badge>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <p className="text-sm text-blue-100 leading-relaxed">
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
                {/* ── DST Signal Breakdown (collapsible) ── */}
                {(prediction.dst_verdict || prediction.model_outputs) && (
                    <div className="mt-4 border-t border-blue-800/40 pt-4">
                        <button
                            className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider hover:text-blue-200 transition-colors w-full text-left"
                            onClick={() => setShowSignalBreakdown(v => !v)}
                        >
                            <Activity className="h-4 w-4" />
                            Fusion des signaux (DST)
                            {showSignalBreakdown ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                        </button>

                        {showSignalBreakdown && (
                            <div className="mt-3 space-y-3">
                                {/* Verdict + conflict */}
                                {prediction.dst_verdict && (
                                    <div className="flex items-center justify-between text-xs p-2 bg-slate-700/50 rounded-md border border-blue-800/40">
                                        <span className="text-blue-300 font-medium">Verdict DST</span>
                                        <div className="flex items-center gap-2">
                                            <Badge className={`text-[10px] py-0 px-1.5 ${
                                                prediction.dst_verdict === 'Healthy' ? 'bg-emerald-100 text-emerald-700' :
                                                prediction.dst_verdict === 'Degrading' ? 'bg-amber-100 text-amber-700' :
                                                prediction.dst_verdict === 'Critical' ? 'bg-red-100 text-red-700' :
                                                'bg-gray-100 text-gray-600'
                                            }`}>
                                                {prediction.dst_verdict}
                                            </Badge>
                                            {prediction.conflict_factor_K !== undefined && (
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span className={`text-[10px] font-mono ${prediction.conflict_factor_K > 0.8 ? 'text-red-400' : 'text-blue-400'}`}>
                                                                K={prediction.conflict_factor_K.toFixed(3)}
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent className="text-xs max-w-[200px]">
                                                            Facteur de conflit Dempster-Shafer. K &lt; 0.8 signifie que les modèles sont en accord.
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Kalman smoothed state */}
                                {prediction.kalman_hi !== undefined && (
                                    <div className="flex items-center justify-between text-xs p-2 bg-slate-700/50 rounded-md border border-blue-800/40">
                                        <span className="text-blue-300 font-medium">État Kalman (lissé)</span>
                                        <span className="text-blue-200 font-mono">
                                            HI={prediction.kalman_hi?.toFixed(1)} · RUL={prediction.kalman_rul?.toFixed(1)}j
                                            {prediction.sensor_fault_flag && (
                                                <Badge className="ml-2 text-[9px] py-0 px-1 bg-yellow-100 text-yellow-700">Défaut capteur</Badge>
                                            )}
                                        </span>
                                    </div>
                                )}

                                {/* Per-model breakdown */}
                                {prediction.model_outputs && (
                                    <div className="space-y-1.5">
                                        <p className="text-[10px] text-blue-500 uppercase tracking-wider font-bold">Indices par modèle</p>
                                        {Object.entries({
                                            'PINN RUL (A)': prediction.model_outputs.pinn_rul,
                                            'Survie Cox/AFT (B)': prediction.model_outputs.survival,
                                            'Mahalanobis (C)': prediction.model_outputs.mahal_hi,
                                            'Anomalie CUSUM (E)': prediction.model_outputs.anomaly,
                                        }).map(([label, out]) => out ? (
                                            <div key={label} className="flex items-center justify-between text-xs p-1.5 bg-slate-800/70 rounded border border-blue-900/30">
                                                <span className="text-blue-400">{label}</span>
                                                <div className="flex items-center gap-3 text-blue-200 font-mono">
                                                    {out.health_index !== undefined && (
                                                        <span>HI={out.health_index.toFixed(1)}</span>
                                                    )}
                                                    {out.rul_estimate !== undefined && out.rul_estimate !== null && (
                                                        <span className="text-blue-400">{out.rul_estimate.toFixed(1)}j</span>
                                                    )}
                                                    {out.uncertainty !== undefined && (
                                                        <span className="text-blue-500 text-[9px]">±{out.uncertainty.toFixed(1)}</span>
                                                    )}
                                                    {out.is_anomaly !== undefined && (
                                                        <Badge className={`text-[9px] py-0 px-1 ${out.is_anomaly ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                                                            {out.is_anomaly ? '⚠' : '✓'}
                                                        </Badge>
                                                    )}
                                                </div>
                                            </div>
                                        ) : null)}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
