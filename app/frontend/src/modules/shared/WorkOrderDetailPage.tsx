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
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { OrdreTravail, Machine, Intervention } from '@/lib/types';

export default function WorkOrderDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [ordre, setOrdre] = useState<OrdreTravail | null>(null);
    const [machine, setMachine] = useState<Machine | null>(null);
    const [interventions, setInterventions] = useState<Intervention[]>([]);
    const [loading, setLoading] = useState(true);

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

    const getPriorityColor = (priorite: string) => {
        switch (priorite) {
            case 'URGENTE':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'HAUTE':
                return 'bg-orange-100 text-orange-800 border-orange-300';
            case 'MOYENNE':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
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
                return 'bg-gray-100 text-gray-800';
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
                <Button onClick={() => navigate(-1)} className="mt-4">
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
                                <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-700 bg-muted/30 p-4 rounded-lg border">
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
                                        <div className="space-y-4">
                                            {interventions.map((int) => (
                                                <div key={int.id} className="flex gap-4 p-3 rounded-lg border bg-card hover:bg-accent transition-colors">
                                                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                                                        <Wrench className="h-5 w-5 text-primary" />
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-center justify-between mb-1">
                                                            <p className="font-semibold text-sm">Intervention #{int.id}</p>
                                                            <p className="text-xs text-muted-foreground">
                                                                {new Date(int.date_intervention).toLocaleDateString('fr-FR')}
                                                            </p>
                                                        </div>
                                                        <p className="text-sm text-muted-foreground line-clamp-2">{int.rapport || 'Pas de rapport'}</p>
                                                    </div>
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
        </div>
    );
}
