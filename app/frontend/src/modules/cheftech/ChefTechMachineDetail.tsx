import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    ArrowLeft,
    MapPin,
    Wrench,
    History,
    FileText,
    Heart,
    Activity,
    Calendar,
    User,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Machine, Intervention } from '@/lib/types';
import MachineHealthPanel from './machines/components/MachineHealthPanel';
import { computeHealthScore } from './machines/utils/healthScore';

function getMachineStatusConfig(statut: string) {
    const map: Record<string, { label: string; className: string }> = {
        OPERATIONNELLE: { label: '● Opérationnelle', className: 'bg-emerald-100 text-emerald-800 border border-emerald-200' },
        EN_MAINTENANCE: { label: '● En Maintenance', className: 'bg-amber-100 text-amber-800 border border-amber-200' },
        EN_PANNE: { label: '● En Panne', className: 'bg-red-100 text-red-800 border border-red-200 animate-pulse' },
        HORS_SERVICE: { label: '● Hors Service', className: 'bg-gray-100 text-gray-700 border border-gray-200' },
    };
    return map[statut] ?? { label: statut, className: 'bg-gray-100 text-gray-600' };
}

export default function ChefTechMachineDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [machine, setMachine] = useState<Machine | null>(null);
    const [interventions, setInterventions] = useState<Intervention[]>([]);
    const [openWorkOrders, setOpenWorkOrders] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (id) fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            setLoading(true);

            // Fetch machine
            const machineRes = await client.entities.machines.get({ id: id! });
            const m: Machine = machineRes.data;
            setMachine(m);

            // Fetch interventions for this machine (filter client-side)
            const intRes = await client.entities.ordres_intervention.queryAll({
                query: {},
                sort: '-date_intervention',
                limit: 100,
            });
            const allInterventions = intRes.data.items || [];
            const machineInterventions = allInterventions.filter(
                (i: Intervention) => i.machine_id === m.id
            );
            setInterventions(machineInterventions);

            // Count open work orders for this machine
            const woRes = await client.entities.ordres_travail.queryAll({
                query: {},
                limit: 200,
            });
            const openWOs = (woRes.data.items || []).filter(
                (wo: { machine_id: number; statut: string }) =>
                    wo.machine_id === m.id &&
                    !['TERMINE', 'ANNULE'].includes(wo.statut)
            );
            setOpenWorkOrders(openWOs.length);
        } catch (error) {
            console.error('Error fetching machine detail:', error);
            toast({
                title: 'Erreur',
                description: 'Impossible de charger les détails de la machine',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">Chargement de la machine...</p>
                </div>
            </div>
        );
    }

    if (!machine) {
        return (
            <div className="text-center py-16">
                <p className="text-gray-500 text-lg">Machine introuvable</p>
                <Button onClick={() => navigate('/cheftech/machines')} className="mt-4">
                    Retour à la liste
                </Button>
            </div>
        );
    }

    const statusConfig = getMachineStatusConfig(machine.statut ?? '');
    const recentInterventionsCount = interventions.filter((i) => {
        const d = new Date(i.date_intervention);
        return d > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    }).length;
    const health = computeHealthScore(machine, openWorkOrders, recentInterventionsCount);

    return (
        <div className="space-y-6">
            {/* ── Header ── */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate('/cheftech/machines')}
                    className="self-start"
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Retour
                </Button>

                <div className="flex-1 min-w-0">
                    <h1 className="text-2xl font-bold text-gray-900 truncate">{machine.nom}</h1>
                    <p className="text-sm text-gray-500 mt-0.5">
                        {[machine.zone, machine.sous_zone, machine.ordre].filter(Boolean).join(' · ')} &mdash; #{machine.id}
                    </p>
                </div>

                <Badge className={`shrink-0 text-sm px-3 py-1 ${statusConfig.className}`}>
                    {statusConfig.label}
                </Badge>
            </div>

            {/* ── Main grid: content left + health panel right ── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* LEFT — tabs, 2/3 width */}
                <div className="lg:col-span-2">
                    <Tabs defaultValue="overview" className="w-full">
                        <TabsList className="grid grid-cols-2 w-full max-w-sm">
                            <TabsTrigger value="overview" className="flex items-center gap-1.5">
                                <Activity className="h-3.5 w-3.5" /> Aperçu
                            </TabsTrigger>
                            <TabsTrigger value="history" className="flex items-center gap-1.5">
                                <History className="h-3.5 w-3.5" /> Historique
                            </TabsTrigger>
                        </TabsList>

                        {/* ── Overview Tab ── */}
                        <TabsContent value="overview" className="mt-4 space-y-4">
                            {/* Machine image */}
                            {machine.image_url && (
                                <div className="rounded-xl overflow-hidden shadow-sm border border-gray-100 h-52">
                                    <img
                                        src={machine.image_url}
                                        alt={machine.nom}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            )}

                            {/* Technical info */}
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <Wrench className="h-4 w-4 text-gray-500" />
                                        Informations Techniques
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
                                        {[
                                            { label: 'Type', value: machine.type },
                                            { label: 'Emplacement', value: machine.emplacement },
                                            { label: 'Zone', value: machine.zone },
                                            { label: 'Sous-zone', value: machine.sous_zone },
                                            { label: 'Ordre', value: machine.ordre },
                                        ]
                                            .filter((f) => f.value)
                                            .map((field) => (
                                                <div key={field.label}>
                                                    <dt className="font-medium text-gray-500">{field.label}</dt>
                                                    <dd className="mt-0.5 text-gray-900">{field.value}</dd>
                                                </div>
                                            ))}
                                        {machine.date_derniere_maintenance && (
                                            <div>
                                                <dt className="font-medium text-gray-500 flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" /> Dernière maintenance
                                                </dt>
                                                <dd className="mt-0.5 text-gray-900">
                                                    {new Date(machine.date_derniere_maintenance).toLocaleDateString('fr-FR')}
                                                </dd>
                                            </div>
                                        )}
                                        {machine.date_prochaine_maintenance && (
                                            <div>
                                                <dt className="font-medium text-gray-500 flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" /> Prochaine maintenance
                                                </dt>
                                                <dd className={`mt-0.5 font-semibold ${new Date(machine.date_prochaine_maintenance) < new Date() ? 'text-red-600' : 'text-amber-600'}`}>
                                                    {new Date(machine.date_prochaine_maintenance).toLocaleDateString('fr-FR')}
                                                </dd>
                                            </div>
                                        )}
                                    </dl>
                                </CardContent>
                            </Card>

                            {/* Stats row */}
                            <div className="grid grid-cols-3 gap-4">
                                {[
                                    { label: 'Interventions (30j)', value: recentInterventionsCount, color: 'text-blue-600' },
                                    { label: 'OT Ouverts', value: openWorkOrders, color: openWorkOrders > 0 ? 'text-red-600' : 'text-gray-600' },
                                    { label: 'Total historique', value: interventions.length, color: 'text-gray-600' },
                                ].map((stat) => (
                                    <Card key={stat.label} className="text-center p-4">
                                        <div className={`text-3xl font-black ${stat.color}`}>{stat.value}</div>
                                        <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
                                    </Card>
                                ))}
                            </div>
                        </TabsContent>

                        {/* ── History Tab ── */}
                        <TabsContent value="history" className="mt-4">
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <History className="h-4 w-4 text-gray-500" />
                                        Historique des Interventions
                                        <Badge variant="secondary" className="ml-auto">{interventions.length}</Badge>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {interventions.length === 0 ? (
                                        <div className="text-center py-12 text-gray-400">
                                            <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
                                            <p>Aucune intervention enregistrée pour cette machine</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-3">
                                            {interventions.map((intervention) => (
                                                <div
                                                    key={intervention.id}
                                                    className="p-4 border border-gray-100 rounded-xl hover:border-blue-200 hover:bg-blue-50/30 transition-colors"
                                                >
                                                    <div className="flex items-start justify-between mb-2">
                                                        <div className="flex items-center gap-2">
                                                            <FileText className="h-4 w-4 text-blue-600 shrink-0" />
                                                            <p className="font-semibold text-sm text-gray-800">
                                                                Intervention #{intervention.id}
                                                            </p>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            {intervention.statut && (
                                                                <Badge variant="outline" className="text-xs">
                                                                    {intervention.statut}
                                                                </Badge>
                                                            )}
                                                            <p className="text-xs text-gray-400 shrink-0">
                                                                {new Date(intervention.date_intervention).toLocaleDateString('fr-FR')}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    {intervention.technicien_id && (
                                                        <p className="text-xs text-gray-500 flex items-center gap-1 mb-1.5">
                                                            <User className="h-3 w-3" /> Technicien ID: {intervention.technicien_id}
                                                        </p>
                                                    )}
                                                    {intervention.rapport && (
                                                        <p className="text-sm text-gray-600 line-clamp-3 whitespace-pre-wrap leading-relaxed">
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
                    </Tabs>
                </div>

                {/* RIGHT — Health Panel, 1/3 width */}
                <div className="lg:col-span-1">
                    <div className="sticky top-6">
                        <MachineHealthPanel health={health} />

                        {/* Location card */}
                        <Card className="mt-4 border-0 shadow-sm">
                            <CardContent className="pt-4">
                                <div className="flex items-start gap-3">
                                    <MapPin className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <p className="font-medium text-gray-700">Localisation</p>
                                        <p className="text-gray-500 mt-0.5">
                                            {[machine.emplacement, machine.zone, machine.sous_zone]
                                                .filter(Boolean)
                                                .join(', ')}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}
