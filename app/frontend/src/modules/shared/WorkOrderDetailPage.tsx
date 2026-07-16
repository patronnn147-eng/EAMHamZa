import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    ArrowLeft,
    Calendar,
    AlertTriangle,
    FileText,
    History,
    Activity,
    User,
    MapPin,
    Wrench,
    RefreshCw,
    TrendingUp,
    TrendingDown,
    Minus,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import type { OrdreTravail, Machine, Intervention } from '@/lib/types';
import { CompleteWorkOrderModal } from './CompleteWorkOrderModal';
import { InterventionPartsPanel } from '@/components/inventory/InterventionPartsPanel';

export default function WorkOrderDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [ordre, setOrdre] = useState<OrdreTravail | null>(null);
    const [machine, setMachine] = useState<Machine | null>(null);
    const [interventions, setInterventions] = useState<Intervention[]>([]);
    const [loading, setLoading] = useState(true);
    const [completeModalOpen, setCompleteModalOpen] = useState(false);
    const [currentHealthScore, setCurrentHealthScore] = useState<number | null>(null);
    const { user } = useAuth();

    useEffect(() => {
        if (id) {
            fetchData();
        }
    }, [id]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const ordreResponse = await client.entities.ordres_travail.get({ id: id! });
            const ordreData = ordreResponse.data as OrdreTravail;
            setOrdre(ordreData);

            if (ordreData.machine_id) {
                const machineResponse = await client.entities.machines.get({ id: ordreData.machine_id.toString() });
                setMachine(machineResponse.data as Machine);

                // Fetch interventions for this machine
                const interventionsResponse = await client.entities.ordres_intervention.queryAll({
                    query: { machine_id: ordreData.machine_id },
                    sort: '-date_intervention',
                    limit: 10,
                });
                setInterventions(interventionsResponse.data.items || []);

                // Fetch current unified_health_score for Health Impact row.
                // Best-effort: silently null on failure (ML service may be down).
                try {
                    const token = localStorage.getItem('access_token');
                    const apiBase = import.meta.env.VITE_API_BASE_URL || '';
                    const hr = await fetch(
                        `${apiBase}/api/v1/ml/machines/${ordreData.machine_id}/unified-health`,
                        { headers: { Authorization: `Bearer ${token}` } },
                    );
                    if (hr.ok) {
                        const hd = await hr.json();
                        const live = hd?.unified_health_score ?? hd?.health_score ?? null;
                        setCurrentHealthScore(typeof live === 'number' ? live : null);
                    }
                } catch {
                    setCurrentHealthScore(null);
                }
            }
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

    const handleStartWorkOrder = async () => {
        if (!id) return;
        try {
            const token = localStorage.getItem('access_token');
            const apiBase = import.meta.env.VITE_API_BASE_URL || '';
            
            // Check localStorage for user role (more reliable)
            const storedUser = localStorage.getItem('user');
            const userData = storedUser ? JSON.parse(storedUser) : null;
            const userRole = userData?.role || user?.role || '';
            
            // Use correct endpoint based on user role
            let endpoint = 'chetop';
            if (userRole.toUpperCase() === 'TECHNICIEN' || userRole.toLowerCase() === 'technicien') {
                endpoint = 'technicien';
            }
            
            const response = await fetch(`${apiBase}/api/v1/${endpoint}/work-orders/${id}/start`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                toast({
                    title: 'Succès',
                    description: 'L\'intervention a commencé',
                });
                fetchData();
            } else {
                const error = await response.json();
                toast({
                    title: 'Erreur',
                    description: error.detail || 'Impossible de commencer l\'intervention',
                    variant: 'destructive',
                });
            }
        } catch (error) {
            console.error('Error starting WO:', error);
            toast({
                title: 'Erreur',
                description: 'Erreur réseau',
                variant: 'destructive',
            });
        }
    };

    const getPriorityColor = (priorite: string) => {
        switch (priorite) {
            case 'URGENTE':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'HAUTE':
                return 'bg-orange-100 text-orange-800 border-orange-300';
            case 'MOYENNE':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            default:
                return 'bg-gray-100 text-blue-50 border-blue-600/50';
        }
    };

    const getStatusColor = (statut: string) => {
        switch (statut) {
            case 'EN_COURS':
                return 'bg-blue-100 text-blue-800';
            case 'EN_ATTENTE':
                return 'bg-yellow-100 text-yellow-800';
            case 'TERMINE':
                return 'bg-green-100 text-green-800';
            case 'ASSIGNÉ':
                return 'bg-purple-100 text-purple-800';
            default:
                return 'bg-gray-100 text-blue-50';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!ordre) {
        return (
            <div className="text-center py-12">
                <p className="text-muted-foreground">Ordre de travail non trouvé</p>
                <Button onClick={() => navigate(-1)} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">
                    Retour
                </Button>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-6 space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate(-1)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Retour
                </Button>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold tracking-tight">Ordre de Travail #{ordre.id}</h1>
                    <div className="flex items-center gap-2 mt-2">
                        <Badge className={getPriorityColor(ordre.priorite)}>{ordre.priorite}</Badge>
                        <Badge className={getStatusColor(ordre.statut)}>{ordre.statut}</Badge>
                    </div>
                </div>
                {ordre.statut === 'EN_ATTENTE' && (
                    <Button
                        onClick={handleStartWorkOrder}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl px-8 shadow-lg shadow-emerald-500/20"
                    >
                        Commencer l'intervention
                    </Button>
                )}
                {ordre.statut === 'EN_COURS' && (
                    <Button
                        onClick={() => setCompleteModalOpen(true)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl px-8 shadow-lg shadow-emerald-500/20"
                    >
                        Terminer l'OT
                    </Button>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileText className="h-5 w-5 text-muted-foreground" />
                                Détails de l'Ordre
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-1">
                                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Titre</p>
                                    <p className="text-lg font-semibold">{ordre.titre}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Date d'Échéance</p>
                                    <p className="text-lg flex items-center gap-2">
                                        <Calendar className="h-4 w-4 text-primary" />
                                        {ordre.date_echeance ? new Date(ordre.date_echeance).toLocaleDateString('fr-FR') : 'Non définie'}
                                    </p>
                                </div>
                            </div>

                            <Separator />

                            <div className="space-y-2">
                                <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Description</p>
                                <p className="text-sm leading-relaxed whitespace-pre-wrap text-blue-100 bg-muted/30 p-4 rounded-lg border">
                                    {ordre.description || 'Aucune description fournie.'}
                                </p>
                            </div>

                            {ordre.priorite === 'URGENTE' && (
                                <div className="flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
                                    <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                                    <div>
                                        <p className="font-bold">Priorité Critique</p>
                                        <p className="text-sm opacity-90">Cette intervention est marquée comme urgente et doit être traitée immédiatement.</p>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Post-Maintenance Health Impact — shown when at least the creation snapshot exists */}
                    {(ordre.health_score_at_creation != null
                        || ordre.health_score_at_completion != null) && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Activity className="h-5 w-5 text-muted-foreground" />
                                    Impact sur la Santé Machine
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {(() => {
                                    const before = ordre.health_score_at_creation ?? null;
                                    const atCompletion = ordre.health_score_at_completion ?? null;
                                    const now = currentHealthScore;
                                    const delta = (before != null && now != null) ? (now - before) : null;
                                    const fmt = (v: number | null) => v == null ? '—' : v.toFixed(0);
                                    let deltaColor: string;
                                    if (delta == null) {
                                        deltaColor = 'text-muted-foreground';
                                    } else if (delta > 0) {
                                        deltaColor = 'text-emerald-500';
                                    } else if (delta < 0) {
                                        deltaColor = 'text-red-500';
                                    } else {
                                        deltaColor = 'text-muted-foreground';
                                    }

                                    let deltaLabel = '—';
                                    if (delta != null) {
                                        const deltaSign = delta > 0 ? '+' : '';
                                        deltaLabel = `${deltaSign}${delta.toFixed(1)} pts`;
                                    }

                                    let DeltaIcon: typeof Minus;
                                    if (delta == null) {
                                        DeltaIcon = Minus;
                                    } else if (delta > 0) {
                                        DeltaIcon = TrendingUp;
                                    } else if (delta < 0) {
                                        DeltaIcon = TrendingDown;
                                    } else {
                                        DeltaIcon = Minus;
                                    }

                                    return (
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="space-y-1">
                                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    Avant (OT ouvert)
                                                </p>
                                                <p className="text-2xl font-bold text-slate-300">{fmt(before)}</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    À la complétion
                                                </p>
                                                <p className="text-2xl font-bold text-slate-300">{fmt(atCompletion)}</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    Maintenant
                                                </p>
                                                <p className="text-2xl font-bold text-cyan-400">{fmt(now)}</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                    Amélioration nette
                                                </p>
                                                <p className={`text-2xl font-bold flex items-center gap-1 ${deltaColor}`}>
                                                    <DeltaIcon className="h-5 w-5" />
                                                    {deltaLabel}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })()}
                                <p className="text-xs text-muted-foreground mt-4 leading-relaxed">
                                    Score de santé unifié (DST fusion P1-P6) capturé à trois moments : ouverture
                                    de l'OT, complétion, et lecture actuelle de la télémétrie.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {ordre?.id != null && (
                        <InterventionPartsPanel workOrderId={ordre.id} />
                    )}

                    <Tabs defaultValue="history">
                        <TabsList>
                            <TabsTrigger value="history" className="flex items-center gap-2">
                                <History className="h-4 w-4" /> Historique Machine
                            </TabsTrigger>
                            <TabsTrigger value="activity" className="flex items-center gap-2">
                                <Activity className="h-4 w-4" /> Activité
                            </TabsTrigger>
                        </TabsList>
                        <TabsContent value="history" className="mt-4">
                            <Card>
                                <CardContent className="pt-6">
                                    {interventions.length === 0 ? (
                                        <div className="text-center py-8 text-muted-foreground">
                                            <p>Aucune intervention passée pour cette machine.</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-6">
                                            {interventions.map((int) => (
                                                <div key={int.id} className="flex flex-col gap-4 p-4 rounded-xl border bg-card hover:shadow-md transition-all">
                                                    <div className="flex items-start gap-4">
                                                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                                                            <Wrench className="h-5 w-5 text-primary" />
                                                        </div>
                                                        <div className="flex-1">
                                                            <div className="flex items-center justify-between mb-1">
                                                                <div className="flex items-center gap-2">
                                                                    <p className="font-bold text-base">Intervention #{int.id}</p>
                                                                    <Badge variant="outline" className="text-[10px] uppercase">
                                                                        {int.intervention_type || 'Curative'}
                                                                    </Badge>
                                                                </div>
                                                                <p className="text-xs text-muted-foreground font-medium">
                                                                    {new Date(int.date_intervention).toLocaleDateString('fr-FR', {
                                                                        day: '2-digit',
                                                                        month: 'long',
                                                                        year: 'numeric'
                                                                    })}
                                                                </p>
                                                            </div>
                                                            <p className="text-sm font-semibold text-blue-50">{int.rapport}</p>
                                                        </div>
                                                    </div>

                                                    {/* grid for diagnostic/PDCA info */}
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2 text-xs">
                                                        {/* --- Diagnostic Info (from DI) --- */}
                                                        <div className="space-y-2 p-3 bg-muted/30 rounded-lg border border-dashed">
                                                            <p className="font-bold text-muted-foreground uppercase flex items-center gap-1">
                                                                <Activity className="h-3 w-3" /> Diagnostic Initial
                                                            </p>
                                                            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                                                <p><span className="text-muted-foreground">État:</span> {int.operating_state || 'N/A'}</p>
                                                                <p><span className="text-muted-foreground">Fréquence:</span> {int.frequency || 'N/A'}</p>
                                                                <p className="col-span-2"><span className="text-muted-foreground">Symptômes:</span> {Array.isArray(int.symptoms) ? int.symptoms.join(', ') : (int.symptoms || 'Aucun')}</p>
                                                                <p className="col-span-2"><span className="text-muted-foreground">Impact:</span> {int.impact || 'Aucun'}</p>
                                                            </div>
                                                        </div>

                                                        {/* --- PDCA Summary --- */}
                                                        <div className="space-y-2 p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
                                                            <p className="font-bold text-emerald-700 uppercase flex items-center gap-1">
                                                                <RefreshCw className="h-3 w-3" /> Cycle PDCA
                                                            </p>
                                                            <div className="space-y-1">
                                                                <p><span className="font-bold text-emerald-600">P (Hypothèse):</span> {int.plan_hypothesis || 'N/A'}</p>
                                                                <p><span className="font-bold text-emerald-600">D (Cause):</span> {int.root_cause_category} - {int.root_cause_description}</p>
                                                                <p><span className="font-bold text-emerald-600">C (Résolu):</span> {int.check_resolved ? '✅ Oui' : '❌ Non'} via {int.check_verification_method || '?'}</p>
                                                                <p><span className="font-bold text-emerald-600">A (Préventif):</span> {int.act_preventive_actions || 'N/A'}</p>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Additional Details (Parts/Tools) */}
                                                    {(int.parts_replaced || int.tools_used) && (
                                                        <div className="flex gap-4 text-[11px] px-2 py-1 bg-slate-800/50 rounded-md">
                                                            {int.parts_replaced && (
                                                                <p><span className="font-bold text-blue-300 uppercase">Pièces:</span> {int.parts_replaced}</p>
                                                            )}
                                                            {int.tools_used && (
                                                                <p><span className="font-bold text-blue-300 uppercase">Outils:</span> {int.tools_used}</p>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </TabsContent>
                        <TabsContent value="activity">
                            <Card>
                                <CardContent className="py-12 text-center text-muted-foreground">
                                    <p>Le journal d'activité détaillé sera bientôt disponible.</p>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Activity className="h-5 w-5 text-primary" />
                                Détails Machine
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {machine ? (
                                <div className="space-y-4">
                                    <div className="aspect-video rounded-lg overflow-hidden border bg-muted">
                                        {machine.image_url ? (
                                            <img src={machine.image_url} alt={machine.nom} className="w-full h-full object-cover" />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center">
                                                <Activity className="h-12 w-12 text-muted-foreground opacity-20" />
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-3">
                                        <div>
                                            <p className="text-xs font-semibold text-muted-foreground uppercase">Nom</p>
                                            <p className="font-bold">{machine.nom}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs font-semibold text-muted-foreground uppercase">Localisation</p>
                                            <p className="text-sm flex items-center gap-1 mt-1">
                                                <MapPin className="h-3 w-3 text-muted-foreground" />
                                                {machine.emplacement || 'Non spécifié'}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-xs font-semibold text-muted-foreground uppercase text-center mb-2">Statut Machine</p>
                                            <Badge variant="outline" className="w-full justify-center py-1">
                                                {machine.statut}
                                            </Badge>
                                        </div>
                                    </div>
                                    <Button
                                        className="w-full"
                                        variant="outline"
                                        onClick={() => navigate(`/machines/${machine.id}`)}
                                    >
                                        Voir Details Machine
                                    </Button>
                                </div>
                            ) : (
                                <div className="text-center py-6 text-muted-foreground">
                                    <p>Machine non associée</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <User className="h-5 w-5 text-primary" />
                                Assignation
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                <div>
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">Créé par</p>
                                    <p className="text-sm font-medium">{ordre.utilisateur_id ? `Utilisateur #${ordre.utilisateur_id}` : 'Système'}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">Assigné à</p>
                                    <p className="text-sm font-medium italic">Consulter la liste des interventions pour plus de détails</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <CompleteWorkOrderModal
                open={completeModalOpen}
                onOpenChange={setCompleteModalOpen}
                workOrderId={Number.parseInt(id)}
                machineId={ordre?.machine_id ?? null}
                onSuccess={fetchData}
            />
        </div>
    );
}



