import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
    BrainCircuit,
    RefreshCcw,
    Database,
    CheckCircle2,
    TrendingUp,
    History,
    AlertCircle,
    Activity
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface MLStats {
    new_data_points: number;
}

interface RetrainResult {
    status: string;
    message: string;
    new_total_samples?: number;
}

export default function MLDashboard() {
    const [stats, setStats] = useState<MLStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [retraining, setRetraining] = useState(false);
    const { toast } = useToast();

    const fetchStats = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/v1/ml/retrain/stats');
            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch ML stats:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    const handleRetrain = async () => {
        try {
            setRetraining(true);
            const response = await fetch('/api/v1/ml/retrain', { method: 'POST' });
            const result: RetrainResult = await response.json();

            if (result.status === 'success') {
                toast({
                    title: "Modèle mis à jour",
                    description: result.message,
                    variant: "default",
                });
                fetchStats();
            } else if (result.status === 'skipped') {
                toast({
                    title: "Information",
                    description: result.message,
                    variant: "default",
                });
            } else {
                toast({
                    title: "Erreur",
                    description: result.message,
                    variant: "destructive",
                });
            }
        } catch (error) {
            toast({
                title: "Erreur",
                description: "Le pipeline de ré-entraînement a échoué.",
                variant: "destructive",
            });
        } finally {
            setRetraining(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-gray-900">IA & Maintenance Prédictive</h2>
                    <p className="text-sm text-gray-500 mt-1">
                        Surveillance des modèles ML et gestion de l'apprentissage continu (PDCA).
                    </p>
                </div>
                <Button
                    onClick={handleRetrain}
                    disabled={retraining || (stats?.new_data_points === 0)}
                    className="bg-blue-600 hover:bg-blue-700 font-semibold"
                >
                    <RefreshCcw className={`mr-2 h-4 w-4 ${retraining ? 'animate-spin' : ''}`} />
                    Ré-entraîner les modèles (P1)
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Data Collection Card */}
                <Card className="border-blue-100 shadow-sm">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <Database className="h-4 w-4 text-blue-500" />
                            <CardTitle className="text-sm font-medium">Capture Feedback (Ground Truth)</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col gap-1">
                            <span className="text-2xl font-bold">{stats?.new_data_points ?? 0}</span>
                            <span className="text-xs text-gray-500">Nouveaux points de données confirmés</span>
                            <Progress value={Math.min((stats?.new_data_points ?? 0) * 10, 100)} className="h-1.5 mt-2 bg-blue-50" />
                            <p className="text-[10px] text-gray-400 mt-2">
                                Seuil recommandé : 50 points pour un impact significatif.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Model Precision (Mock for demo) */}
                <Card className="border-green-100 shadow-sm">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-green-500" />
                            <CardTitle className="text-sm font-medium">Précision Modèle P1</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col gap-1">
                            <span className="text-2xl font-bold">94.2%</span>
                            <span className="text-xs text-gray-500">Global AUC-ROC Score</span>
                            <Progress value={94} className="h-1.5 mt-2 bg-green-50 [&>div]:bg-green-500" />
                        </div>
                    </CardContent>
                </Card>

                {/* System Activity */}
                <Card className="border-gray-100 shadow-sm">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <Activity className="h-4 w-4 text-gray-400" />
                            <CardTitle className="text-sm font-medium">Dernier Retraitement</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col gap-1">
                            <span className="text-xl font-bold text-gray-700">Il y a 2 jours</span>
                            <span className="text-xs text-gray-500 text-emerald-600 font-medium flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3" /> État : Stable
                            </span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Explainer & Roadmap Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <History className="h-4 w-4 text-blue-500" />
                            Cycle PDCA : Apprentissage Continu
                        </CardTitle>
                        <CardDescription className="text-xs">
                            Comment vos données améliorent l'IA.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="relative pl-6 border-l-2 border-blue-200 space-y-4 pb-1">
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-blue-600 flex items-center justify-center text-[10px] text-white">1</span>
                                <p className="text-sm font-semibold">PLAN: Prédiction IA</p>
                                <p className="text-xs text-gray-500 mt-0.5">L'IA analyse le risque et suggère une maintenance.</p>
                            </div>
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-blue-400 flex items-center justify-center text-[10px] text-white">2</span>
                                <p className="text-sm font-semibold">DO: Intervention Technique</p>
                                <p className="text-xs text-gray-500 mt-0.5">Le technicien répare la machine en suivant l'ordre de travail.</p>
                            </div>
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-blue-300 flex items-center justify-center text-[10px] text-white">3</span>
                                <p className="text-sm font-semibold">CHECK: Feedback (Vérité Terrain)</p>
                                <p className="text-xs text-gray-500 mt-0.5">Le technicien confirme le type de panne réel lors de la clôture.</p>
                            </div>
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center text-[10px] text-white">4</span>
                                <p className="text-sm font-semibold text-emerald-700">ACT: Ré-entraînement IA</p>
                                <p className="text-xs text-emerald-600 mt-0.5 font-medium">Cliquez sur ré-entraîner pour intégrer ces feedbacks.</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900 border-slate-800 text-slate-100 overflow-hidden relative">
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                        <BrainCircuit className="h-24 w-24" />
                    </div>
                    <CardHeader>
                        <CardTitle className="text-base text-slate-100 italic">"State-of-the-Art" AI</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                            <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">Explainability (XAI)</p>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                Nous utilisons la technologie <strong>SHAP</strong> pour décomposer chaque prédiction.
                                Les techniciens voient exactement quels capteurs (température, couple, usure) ont déclenché l'alerte.
                            </p>
                        </div>
                        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                            <p className="text-xs font-bold text-emerald-400 uppercase tracking-widest mb-1">Architecture P1-P6</p>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                Votre système n'est pas qu'un simple classifieur. Il possède 6 modèles interconnectés
                                optimisant de la détection d'anomalie jusqu'à l'ordonnancement intelligent.
                            </p>
                        </div>
                        <div className="flex gap-2 pt-2">
                            <Badge className="bg-blue-600/20 text-blue-400 border-blue-400/30">SHAP</Badge>
                            <Badge className="bg-emerald-600/20 text-emerald-400 border-emerald-400/30">XGBoost</Badge>
                            <Badge className="bg-purple-600/20 text-purple-400 border-purple-400/30">PDCA Loop</Badge>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
