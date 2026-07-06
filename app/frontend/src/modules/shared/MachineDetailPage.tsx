import { useEffect, useState, lazy, Suspense } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    ArrowLeft,
    MapPin,
    History,
    FileText,
    AlertCircle,
    Activity,
    User,
    Beaker,
    Brain,
    Box,
    TrendingDown,
    Sparkles,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import type { Machine, Intervention } from '@/lib/types';

import { MLIntelligenceTab } from './machines/components/MLIntelligenceTab';
import { MachineForecastPanel } from './machines/components/MachineForecastPanel';
import { ChatPage } from './ChatInterface';
import { TelemetrySimulator } from './machines/components/TelemetrySimulator';
import { MachineHero3D } from './machines/components/3d/MachineHero3D';

const MachineViewer3D = lazy(() => import('./machines/components/3d/MachineViewer3D'));

interface MLPrediction {
    risk_level: string;
    rul_days: number;
    data_points: number;
    health_score?: number;
    health_breakdown?: any;
    reliability_score?: number;
    mtbf_pred?: number;
    mttr_pred?: number;
    availability_pred?: number;
}

function getMachineStatusConfig(statut: string) {
    const map: Record<string, { label: string; className: string }> = {
        OPERATIONNELLE: { label: '● Opérationnelle', className: 'bg-emerald-100 text-emerald-800 border border-emerald-200' },
        EN_MAINTENANCE: { label: '● En Maintenance', className: 'bg-amber-100 text-amber-800 border border-amber-200' },
        EN_PANNE: { label: '● En Panne', className: 'bg-red-100 text-red-800 border border-red-200 animate-pulse' },
        HORS_SERVICE: { label: '● Hors Service', className: 'bg-gray-100 text-blue-100 border border-blue-700/50' },
    };
    return map[statut] ?? { label: statut, className: 'bg-gray-100 text-blue-200' };
}

export default function MachineDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { user } = useAuth();

    const [machine, setMachine] = useState<Machine | null>(null);
    const [interventions, setInterventions] = useState<Intervention[]>([]);
    const [mlPrediction, setMlPrediction] = useState<MLPrediction | null>(null);
    const [loading, setLoading] = useState(true);
    const [openWorkOrdersCount, setOpenWorkOrdersCount] = useState(0);

    // Status update states (Technician only)
    const [statusDialogOpen, setStatusDialogOpen] = useState(false);
    const [newStatus, setNewStatus] = useState('');
    const [statusComment, setStatusComment] = useState('');

    const [telemetryDialogOpen, setTelemetryDialogOpen] = useState(false);

    const handleTelemetrySuccess = () => {
        fetchData();
    };

    useEffect(() => {
        if (id) {
            fetchData();
        }
    }, [id]);

    const fetchData = async () => {
        try {
            setLoading(true);

            const machineResponse = await client.entities.machines.get({ id: id! });
            const m: Machine = machineResponse.data;
            setMachine(m);

            // Fetch unified health (DST-fused); fall back to /prediction if unavailable
            try {
                const unifiedRes = await fetch(`/api/v1/ml/machines/${id}/unified-health`);
                if (unifiedRes.ok) {
                    const predictionData = await unifiedRes.json();
                    setMlPrediction(predictionData);
                } else {
                    // Fallback: legacy prediction endpoint
                    const mlRes = await fetch(`/api/v1/ml/machines/${id}/prediction`);
                    if (mlRes.ok) {
                        setMlPrediction(await mlRes.json());
                    }
                }
            } catch (err) {
                console.error('Failed to fetch ML Prediction for header:', err);
            }

            // Fetch intervention history (using shared query logic)
            const interventionsResponse = await client.entities.ordres_intervention.queryAll({
                query: {},
                sort: '-date_intervention',
                limit: 200,
            });
            const allInterventions = interventionsResponse.data.items || [];
            const machineInterventions = allInterventions.filter(
                (i: Intervention) => i.machine_id === m.id
            );
            setInterventions(machineInterventions);

            // Count open work orders
            const woRes = await client.entities.ordres_travail.queryAll({
                query: {},
                limit: 200,
            });
            const openWOs = (woRes.data.items || []).filter(
                (wo: { machine_id: number; statut: string }) =>
                    wo.machine_id === m.id &&
                    !['TERMINE', 'ANNULE'].includes(wo.statut)
            );
            setOpenWorkOrdersCount(openWOs.length);

        } catch (error) {
            console.error('Error fetching data:', error);
            toast({
                title: 'Erreur',
                description: 'Impossible de charger les détails',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const handleStatusUpdate = async () => {
        if (!machine || !newStatus || !statusComment.trim()) {
            toast({
                title: 'Erreur',
                description: 'Veuillez remplir tous les champs',
                variant: 'destructive',
            });
            return;
        }

        try {
            await client.entities.machines.update({
                id: machine.id.toString(),
                data: { statut: newStatus },
            });

            toast({
                title: 'Succès',
                description: 'Statut de la machine mis à jour',
            });

            setStatusDialogOpen(false);
            setNewStatus('');
            setStatusComment('');
            fetchData();
        } catch (error: any) {
            const detail = error?.data?.detail || error?.response?.data?.detail || error?.message;
            toast({
                title: 'Erreur',
                description: detail || 'Échec de la mise à jour',
                variant: 'destructive',
            });
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64 text-center">
                <div>
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-3" />
                    <p className="text-sm text-blue-300">Chargement de la machine...</p>
                </div>
            </div>
        );
    }

    if (!machine) {
        return (
            <div className="text-center py-16">
                <p className="text-blue-300 text-lg">Machine non trouvée</p>
                <Button onClick={() => navigate(-1)} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">
                    Retour
                </Button>
            </div>
        );
    }

    const statusConfig = getMachineStatusConfig(machine.statut ?? '');
    const recentInterventionsCount = interventions.filter((i) => {
        const d = new Date(i.date_intervention);
        return d > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    }).length;

    const getMlRiskBadge = (prediction: MLPrediction | null) => {
        if (!prediction) return null;
        const config: Record<string, { label: string; className: string }> = {
            CRITICAL: { label: `CRITIQUE (${prediction.rul_days}j restants)`, className: 'bg-red-600 text-white border-red-700 animate-pulse' },
            HIGH: { label: `ÉLEVÉ (${prediction.rul_days}j restants)`, className: 'bg-orange-500 text-white border-orange-600' },
            MEDIUM: { label: `MODÉRÉ`, className: 'bg-amber-500 text-white border-amber-600' },
            LOW: { label: `FAIBLE`, className: 'bg-emerald-500 text-white border-emerald-600' }
        };
        const c = config[prediction.risk_level] || config.LOW;
        return (
            <Badge className={`shrink-0 text-sm px-3 py-1 flex items-center gap-1.5 shadow-sm ${c.className}`}>
                <Activity className="h-4 w-4" />
                Risque ML: {c.label}
            </Badge>
        );
    };

    const getRecoveryBadge = (prediction: MLPrediction | null) => {
        const rec = prediction?.recovery;
        if (!rec || !rec.within_recovery_window) return null;
        // Only render meaningful states; suppress Monitoring + No baseline noise.
        if (rec.status !== 'Recovered' && rec.status !== 'Recovering' && rec.status !== 'No improvement') {
            return null;
        }
        const config: Record<string, { className: string; label: string }> = {
            'Recovered':      { className: 'bg-emerald-600 text-white border-emerald-700', label: 'Récupérée' },
            'Recovering':     { className: 'bg-amber-500 text-white border-amber-600',     label: 'En récupération' },
            'No improvement': { className: 'bg-red-600 text-white border-red-700',         label: 'Aucune amélioration' },
        };
        const c = config[rec.status];
        let deltaLabel = '';
        if (rec.delta != null) {
            const deltaSign = rec.delta > 0 ? '+' : '';
            deltaLabel = ` (${deltaSign}${rec.delta.toFixed(0)} pts)`;
        }
        return (
            <Badge className={`shrink-0 text-sm px-3 py-1 flex items-center gap-1.5 shadow-sm ${c.className}`}>
                <Activity className="h-4 w-4" />
                {c.label}{deltaLabel}
            </Badge>
        );
    };

    return (
        <div className="space-y-6">
            {/* ── Header ── */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="self-start">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Retour
                </Button>
                <div className="flex-1 min-w-0">
                    <h1 className="text-2xl font-bold text-white truncate">{machine.nom}</h1>
                    <p className="text-sm text-blue-300 mt-0.5">
                        {[machine.zone, machine.sous_zone, machine.ordre].filter(Boolean).join(' · ')} &mdash; #{machine.id}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <Badge className={`shrink-0 text-sm px-3 py-1 ${statusConfig.className}`}>
                        {statusConfig.label}
                    </Badge>
                    {getMlRiskBadge(mlPrediction)}
                    {getRecoveryBadge(mlPrediction)}
                    {(user?.role === 'CHEFOP' || user?.role === 'ADMIN') && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setTelemetryDialogOpen(true)}
                            className="bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100"
                        >
                            <Beaker className="mr-2 h-4 w-4" />
                            Simuler Défaillance
                        </Button>
                    )}
                    {user?.role === 'TECHNICIEN' && (
                        <Button onClick={() => setStatusDialogOpen(true)} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                            <AlertCircle className="mr-2 h-4 w-4" />
                            Changer Statut
                        </Button>
                    )}
                </div>
            </div>

            {/* ── Full-width Tabs ── */}
            <MachineHero3D machine={machine} mlPrediction={mlPrediction as any} />
            <Tabs defaultValue="ml" className="w-full">
                <TabsList className="grid grid-cols-5 w-full max-w-2xl">
                    <TabsTrigger value="ml" className="flex items-center gap-1.5 text-sm">
                        <Brain className="h-3.5 w-3.5" /> ML Intelligence
                    </TabsTrigger>
                    <TabsTrigger value="history" className="flex items-center gap-1.5 text-sm">
                        <History className="h-3.5 w-3.5" /> Historique
                    </TabsTrigger>
                    <TabsTrigger value="3d" className="flex items-center gap-1.5 text-sm">
                        <Box className="h-3.5 w-3.5" /> 3D Vue
                    </TabsTrigger>
                    <TabsTrigger value="chat" className="flex items-center gap-1.5 text-sm">
                        <Sparkles className="h-3.5 w-3.5" /> Assistant IA
                    </TabsTrigger>
                    <TabsTrigger value="forecast" className="flex items-center gap-1.5 text-sm">
                        <TrendingDown className="h-4 w-4" /> Prévisions
                    </TabsTrigger>
                </TabsList>

                {/* ML Intelligence Tab — full width */}
                <TabsContent value="ml" className="mt-4">
                    <MLIntelligenceTab
                        machine={machine}
                        mlPrediction={mlPrediction as any}
                        interventions={interventions}
                        onProvisioned={fetchData}
                    />
                </TabsContent>

                {/* 3D Vue Tab — lazy-loaded canvas */}
                <TabsContent value="3d" className="mt-4">
                    <Suspense
                        fallback={
                            <div
                                style={{
                                    height: 'min(500px, 60vh)',
                                    background: '#0a1628',
                                    borderRadius: '0.75rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: '#475569',
                                    fontSize: '0.8rem',
                                    fontFamily: 'Manrope, sans-serif',
                                }}
                            >
                                Chargement 3D…
                            </div>
                        }
                    >
                        <MachineViewer3D machine={machine} mlPrediction={mlPrediction as any} />
                    </Suspense>
                </TabsContent>

                {/* Assistant IA Tab — machine-scoped chat (live ML context + docs) */}
                <TabsContent value="chat" className="mt-4">
                    <ChatPage machineId={machine.id} />
                </TabsContent>

                {/* History Tab */}
                <TabsContent value="history" className="mt-4">
                    {[machine.emplacement, machine.zone, machine.sous_zone].some(Boolean) && (
                        <div className="flex items-center gap-2 mb-4 text-sm text-blue-300">
                            <MapPin className="h-4 w-4 text-blue-400 shrink-0" />
                            {[machine.emplacement, machine.zone, machine.sous_zone].filter(Boolean).join(' · ')}
                        </div>
                    )}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base flex items-center gap-2 font-bold text-blue-50">
                                <History className="h-4 w-4 text-blue-300" />
                                Historique des Interventions
                                <Badge variant="secondary" className="ml-auto">{interventions.length}</Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {interventions.length === 0 ? (
                                <div className="text-center py-12 text-blue-400">
                                    <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
                                    <p>Aucune intervention enregistrée</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {interventions.map((intervention) => (
                                        <div key={intervention.id} className="p-4 border border-blue-800/50 rounded-xl hover:border-blue-200 hover:bg-blue-50/30 transition-colors">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <FileText className="h-4 w-4 text-blue-600 shrink-0" />
                                                    <p className="font-semibold text-sm text-blue-50">Intervention #{intervention.id}</p>
                                                </div>
                                                <p className="text-xs text-blue-400 shrink-0">
                                                    {new Date(intervention.date_intervention).toLocaleDateString('fr-FR')}
                                                </p>
                                            </div>
                                            {intervention.technicien_id && (
                                                <p className="text-xs text-blue-300 flex items-center gap-1 mb-1.5">
                                                    <User className="h-3 w-3" /> Technicien ID: {intervention.technicien_id}
                                                </p>
                                            )}
                                            {intervention.rapport && (
                                                <p className="text-sm text-blue-200 line-clamp-3 whitespace-pre-wrap leading-relaxed">
                                                    {intervention.rapport}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="forecast" className="mt-4">
                    {machine && <MachineForecastPanel machineId={machine.id} />}
                </TabsContent>
            </Tabs>

            {/* Technician Status Update Dialog */}
            <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Changer le Statut de la Machine</DialogTitle>
                        <DialogDescription>Mettez à jour le statut de {machine.nom} avec une justification.</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="status">Nouveau Statut *</Label>
                            <Select value={newStatus} onValueChange={setNewStatus}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner un statut" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="OPERATIONNELLE">Opérationnelle</SelectItem>
                                    <SelectItem value="EN_MAINTENANCE">En Maintenance</SelectItem>
                                    <SelectItem value="EN_PANNE">En Panne</SelectItem>
                                    <SelectItem value="HORS_SERVICE">Hors Service</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="comment">Commentaire de Justification *</Label>
                            <Textarea
                                id="comment"
                                value={statusComment}
                                onChange={(e) => setStatusComment(e.target.value)}
                                placeholder="Raison du changement..."
                                rows={4}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setStatusDialogOpen(false)}>Annuler</Button>
                        <Button onClick={handleStatusUpdate} className="bg-blue-600 hover:bg-blue-700 text-white">Mettre à Jour</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {machine && (
                <TelemetrySimulator
                    machine={machine}
                    open={telemetryDialogOpen}
                    onOpenChange={setTelemetryDialogOpen}
                    onSuccess={handleTelemetrySuccess}
                />
            )}
        </div>
    );
}