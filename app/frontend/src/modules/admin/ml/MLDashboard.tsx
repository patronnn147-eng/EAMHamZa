import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import {
    BrainCircuit,
    RefreshCcw,
    Database,
    CheckCircle2,
    TrendingUp,
    History,
    Activity,
    Zap,
    Wrench,
    Clock,
    Radar,
    ListOrdered,
    CalendarClock,
    PackageSearch,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { ModelHealthTable } from './ModelHealthTable';

interface MLStats {
    new_data_points: number;
}

interface ModelMetrics {
    roc_auc?: number;
    pr_auc?: number;
    f1_failure?: number;
    retrained_at?: string;
}

function formatRelativeTime(isoDate: string): string {
    const then = new Date(isoDate).getTime();
    if (Number.isNaN(then)) return 'Date inconnue';
    const diffMs = Date.now() - then;
    const diffMin = Math.round(diffMs / 60000);
    if (diffMin < 1) return "À l'instant";
    if (diffMin < 60) return `Il y a ${diffMin} min`;
    const diffH = Math.round(diffMin / 60);
    if (diffH < 24) return `Il y a ${diffH} h`;
    const diffD = Math.round(diffH / 24);
    return `Il y a ${diffD} j`;
}

interface RetrainResult {
    status: string;
    message: string;
    new_total_samples?: number;
}

export default function MLDashboard() {
    const [stats, setStats] = useState<MLStats | null>(null);
    const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
    const [retraining, setRetraining] = useState(false);
    const { toast } = useToast();

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/v1/ml/retrain/stats');
            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch ML stats:', error);
        }
    };

    const fetchMetrics = async () => {
        try {
            const response = await fetch('/api/v1/ml/model/metrics');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.metrics) {
                    setMetrics(data.metrics);
                }
            }
        } catch (error) {
            console.error('Failed to fetch model metrics:', error);
        }
    };

    useEffect(() => {
        fetchStats();
        fetchMetrics();
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
        } catch {
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
                    <h2 className="text-3xl font-bold tracking-tight text-white">IA & Maintenance Prédictive</h2>
                    <p className="text-sm text-blue-300 mt-1">
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

            <ModelHealthTable />

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
                            <span className="text-xs text-blue-300">Nouveaux points de données confirmés</span>
                            <Progress value={Math.min((stats?.new_data_points ?? 0) * 10, 100)} className="h-1.5 mt-2 bg-blue-50" />
                            <p className="text-[10px] text-blue-400 mt-2">
                                Seuil recommandé : 50 points pour un impact significatif.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Model Precision - Real metrics from backend */}
                <Card className="border-green-100 shadow-sm">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-green-500" />
                            <CardTitle className="text-sm font-medium">Précision Modèle P1</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col gap-1">
                            {metrics ? (
                                <>
                                    <span className="text-2xl font-bold">{(metrics.roc_auc || 0) * 100}%</span>
                                    <span className="text-xs text-blue-300">ROC-AUC Score</span>
                                    <Progress value={(metrics.roc_auc || 0) * 100} className="h-1.5 mt-2 bg-green-50 [&>div]:bg-green-500" />
                                    <div className="mt-2 pt-2 border-t border-green-100 grid grid-cols-2 gap-2">
                                        <div>
                                            <span className="text-xs text-gray-500">PR-AUC</span>
                                            <p className="text-sm font-semibold">{(metrics.pr_auc || 0).toFixed(3)}</p>
                                        </div>
                                        <div>
                                            <span className="text-xs text-gray-500">F1 (Failure)</span>
                                            <p className="text-sm font-semibold">{(metrics.f1_failure || 0).toFixed(3)}</p>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <span className="text-2xl font-bold">--</span>
                                    <span className="text-xs text-blue-300">Chargement...</span>
                                </>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* System Activity */}
                <Card className="border-blue-800/50 shadow-sm">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <Activity className="h-4 w-4 text-blue-400" />
                            <CardTitle className="text-sm font-medium">Dernier Retraitement</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col gap-1">
                            <span className="text-xl font-bold text-blue-100">
                                {metrics?.retrained_at ? formatRelativeTime(metrics.retrained_at) : 'Jamais'}
                            </span>
                            <span className="text-xs text-blue-300 text-emerald-600 font-medium flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3" />
                                État : {metrics?.retrained_at ? 'Stable' : 'Aucune donnée'}
                            </span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Model Explainer for non-technical users */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <BrainCircuit className="h-4 w-4 text-purple-400" />
                        Comprendre vos 7 modèles IA
                    </CardTitle>
                    <CardDescription className="text-xs">
                        Ce que chaque modèle fait concrètement — sans jargon technique.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Accordion type="multiple" className="space-y-1">
                        {[
                            {
                                id: 'p1',
                                icon: <Zap className="h-4 w-4 text-red-400" />,
                                label: 'Probabilité de panne',
                                badge: 'P1',
                                badgeColor: 'bg-red-600/20 text-red-300 border-red-500/30',
                                summary: 'Évalue le risque qu\'une machine tombe en panne prochainement.',
                                detail: 'Ce modèle analyse 7 mesures en temps réel (température, couple, vitesse…) et calcule un pourcentage de risque de défaillance. C\'est comme un médecin qui lit vos analyses de sang : il ne dit pas exactement quand vous tomberez malade, mais il lève un drapeau rouge quand les signes s\'accumulent. Un score élevé déclenche automatiquement une alerte pour anticiper la panne avant qu\'elle arrive.',
                            },
                            {
                                id: 'p2',
                                icon: <Wrench className="h-4 w-4 text-orange-400" />,
                                label: 'Type de panne',
                                badge: 'P2',
                                badgeColor: 'bg-orange-600/20 text-orange-300 border-orange-500/30',
                                summary: 'Identifie quelle panne est la plus probable parmi 5 catégories.',
                                detail: 'Quand une panne est détectée, ce modèle la classe automatiquement : surchauffe, usure d\'outil, dissipation thermique, défaillance mécanique ou électrique. C\'est comme un médecin généraliste qui vous dit "c\'est probablement une angine, pas une pneumonie" avant même de faire tous les examens. Le technicien arrive sur place avec les bons outils et les bonnes pièces, sans perdre de temps à diagnostiquer sur place.',
                            },
                            {
                                id: 'p3',
                                icon: <Clock className="h-4 w-4 text-yellow-400" />,
                                label: 'Durée de vie restante',
                                badge: 'P3',
                                badgeColor: 'bg-yellow-600/20 text-yellow-300 border-yellow-500/30',
                                summary: 'Estime en jours combien de temps la machine peut encore fonctionner.',
                                detail: 'Ce modèle calcule le nombre de jours d\'utilisation restants avant qu\'une intervention devienne nécessaire. Imaginez la jauge d\'essence de votre voiture, mais au lieu du carburant, elle mesure l\'usure globale de la machine. Un résultat de "14 jours" signifie : planifiez la maintenance avant cette date pour éviter une panne imprévue. Cela permet d\'organiser les interventions à l\'avance, sans perturber la production.',
                            },
                            {
                                id: 'p4',
                                icon: <Radar className="h-4 w-4 text-cyan-400" />,
                                label: 'Détection d\'anomalie comportementale',
                                badge: 'P4',
                                badgeColor: 'bg-cyan-600/20 text-cyan-300 border-cyan-500/30',
                                summary: 'Détecte un comportement anormal même sans panne visible.',
                                detail: 'Ce modèle surveille en permanence les capteurs et compare le comportement actuel de la machine à son comportement habituel. Il peut repérer qu\'une machine "vibre différemment" ou "chauffe un peu plus que d\'habitude" bien avant que quiconque le remarque — même si tout semble normal en surface. C\'est un système de surveillance 24h/24 qui ne se fatigue jamais et ne rate aucun signe avant-coureur subtil.',
                            },
                            {
                                id: 'p5',
                                icon: <ListOrdered className="h-4 w-4 text-green-400" />,
                                label: 'Priorité des interventions',
                                badge: 'P5',
                                badgeColor: 'bg-green-600/20 text-green-300 border-green-500/30',
                                summary: 'Classe automatiquement les ordres de travail par ordre d\'urgence.',
                                detail: 'Quand plusieurs machines nécessitent une intervention en même temps, ce modèle décide laquelle traiter en premier. Il prend en compte la criticité de la machine pour la production, la gravité du problème et le risque si on attend. C\'est comme le triage aux urgences : le patient en arrêt cardiaque passe avant celui avec une fracture. Vos équipes ne perdent plus de temps à se demander "par où commencer ?".',
                            },
                            {
                                id: 'p6',
                                icon: <CalendarClock className="h-4 w-4 text-blue-400" />,
                                label: 'Planification de la maintenance',
                                badge: 'P6',
                                badgeColor: 'bg-blue-600/20 text-blue-300 border-blue-500/30',
                                summary: 'Suggère les meilleures dates pour la maintenance préventive.',
                                detail: 'Ce modèle propose un calendrier d\'entretien intelligent en tenant compte de l\'état réel de chaque machine (pas juste un calendrier fixe tous les 3 mois). Si une machine est en bonne santé, on peut reculer la maintenance. Si elle montre des signes de fatigue, on l\'avance. C\'est la différence entre changer l\'huile de voiture tous les 10 000 km exactement et la changer quand votre voiture en a vraiment besoin.',
                            },
                            {
                                id: 'p7',
                                icon: <PackageSearch className="h-4 w-4 text-purple-400" />,
                                label: 'Besoin en pièces de rechange',
                                badge: 'P7',
                                badgeColor: 'bg-purple-600/20 text-purple-300 border-purple-500/30',
                                summary: 'Prédit quelles pièces commander et quand, avant qu\'elles manquent.',
                                detail: 'En croisant les prédictions de pannes avec l\'historique des réparations, ce modèle anticipe quelles pièces de rechange seront nécessaires dans les prochaines semaines. Il génère automatiquement des suggestions de commande pour éviter les ruptures de stock. Plus jamais une réparation bloquée parce qu\'une pièce est en rupture — les commandes partent avant même que la panne arrive.',
                            },
                        ].map((m) => (
                            <AccordionItem key={m.id} value={m.id} className="border border-slate-700 rounded-lg px-1">
                                <AccordionTrigger className="px-3 py-2 hover:no-underline">
                                    <div className="flex items-center gap-3 text-left">
                                        {m.icon}
                                        <span className="text-sm font-medium text-slate-100">{m.label}</span>
                                        <Badge className={`text-[10px] border ${m.badgeColor} ml-1`}>{m.badge}</Badge>
                                        <span className="text-xs text-slate-400 font-normal hidden sm:block">{m.summary}</span>
                                    </div>
                                </AccordionTrigger>
                                <AccordionContent className="px-3 pb-3">
                                    <p className="text-sm text-slate-300 leading-relaxed">{m.detail}</p>
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                </CardContent>
            </Card>

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
                                <p className="text-xs text-blue-300 mt-0.5">L'IA analyse le risque et suggère une maintenance.</p>
                            </div>
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-blue-400 flex items-center justify-center text-[10px] text-white">2</span>
                                <p className="text-sm font-semibold">DO: Intervention Technique</p>
                                <p className="text-xs text-blue-300 mt-0.5">Le technicien répare la machine en suivant l'ordre de travail.</p>
                            </div>
                            <div className="relative">
                                <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-blue-300 flex items-center justify-center text-[10px] text-white">3</span>
                                <p className="text-sm font-semibold">CHECK: Feedback (Vérité Terrain)</p>
                                <p className="text-xs text-blue-300 mt-0.5">Le technicien confirme le type de panne réel lors de la clôture.</p>
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
