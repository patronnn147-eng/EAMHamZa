import React, { useEffect, useState } from 'react';
import { getAPIBaseURL } from '@/lib/config';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Search, Clock, Calendar, User, ExternalLink, Wrench } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { 
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { PriorityBadge, StatusBadge } from '@/modules/shared/work-orders/utils/badges';
import { toast } from 'sonner';
import { AppPagination } from '@/components/shared/AppPagination';

interface ChefTechWorkOrder {
    id: number;
    titre: string;
    machine_nom: string;
    technicien_id: number | null;
    technicien_nom: string;
    technicien_email: string;
    intervention_id: number | null;
    statut: string;
    priorite: string;
    created_at: string;
    date_debut: string | null;
    date_fin: string | null;
    duration_min: number | null;
    live_seconds: number | null;
}

export default function ChefTechWorkOrdersTable() {
    const [workOrders, setWorkOrders] = useState<ChefTechWorkOrder[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [pageSize] = useState(100);
    const [currentTime, setCurrentTime] = useState(new Date());

    // Live timer tick
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const fetchWorkOrders = async () => {
        try {
            setLoading(true);
            const apiBase = getAPIBaseURL();
            const response = await fetch(`${apiBase}/api/v1/cheftech/work-orders-table?page=${page}&size=${pageSize}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });
            if (!response.ok) throw new Error('Failed to fetch');
            const data = await response.json();
            setWorkOrders(data.items || []);
            setTotalPages(data.total_pages || 1);
        } catch (error) {
            console.error('Error fetching cheftech work orders:', error);
            toast.error("Erreur lors du chargement des ordres de travail");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchWorkOrders(); }, [page]);

    const handleExport = async (woId: number) => {
        try {
            toast.info("Génération du rapport en cours...");
            const apiBase = getAPIBaseURL();
            const response = await fetch(`${apiBase}/api/v1/cheftech/work-orders-table/${woId}/export`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });
            if (!response.ok) throw new Error('Export failed');
            const blob = await response.blob();
            const url = globalThis.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Rapport_OT_${woId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            globalThis.URL.revokeObjectURL(url);
            toast.success("Rapport téléchargé avec succès");
        } catch (error) {
            console.error('Export error:', error);
            toast.error("Erreur lors de l'export du rapport");
        }
    };

    const calculateLiveDuration = (dateDebutStr: string | null): number => {
        if (!dateDebutStr) return 0;
        const start = new Date(dateDebutStr);
        const diff = currentTime.getTime() - start.getTime();
        return Math.max(0, Math.floor(diff / 60000));
    };

    const formatDuration = (minutes: number) => {
        if (minutes < 0) return "0 min";
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return h > 0 ? `${h}h ${m}min` : `${m} min`;
    };

    const filtered = workOrders.filter(wo =>
        wo.titre.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wo.machine_nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wo.technicien_nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wo.id.toString().includes(searchTerm)
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6 pb-20">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                        Suivi des Ordres de Travail
                    </h1>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Monitoring en temps réel des interventions assignées aux techniciens.
                    </p>
                </div>
            </div>

            <Card className="border-none shadow-xl bg-slate-800/80 backdrop-blur-md border border-orange-800/30 overflow-hidden">
                <CardHeader className="border-b border-orange-800/30 bg-slate-900/50 pb-4">
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-blue-400" />
                            <Input
                                placeholder="Rechercher par ID, Titre, Machine ou Technicien..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-9 bg-slate-800 border-blue-700/50"
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader className="bg-slate-900/80 border-b border-orange-800/30">
                                <TableRow>
                                    <TableHead className="w-[80px] font-bold">ID</TableHead>
                                    <TableHead className="min-w-[200px] font-bold">Machine & Intervention</TableHead>
                                    <TableHead className="min-w-[180px] font-bold">Technicien</TableHead>
                                    <TableHead className="font-bold">Priorité</TableHead>
                                    <TableHead className="font-bold">Statut</TableHead>
                                    <TableHead className="font-bold">Dates</TableHead>
                                    <TableHead className="font-bold">Chrono (Durée)</TableHead>
                                    <TableHead className="text-right font-bold">Rapport</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filtered.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                                            <Wrench className="h-8 w-8 mx-auto mb-2 opacity-30" />
                                            Aucun ordre de travail trouvé
                                        </TableCell>
                                    </TableRow>
                                ) : filtered.map((wo) => {
                                    const isEnCours = wo.statut === 'EN_COURS';
                                    const duration = isEnCours
                                        ? calculateLiveDuration(wo.date_debut)
                                        : (wo.duration_min ?? 0);

                                    return (
                                        <TableRow key={wo.id} className="hover:bg-orange-900/20 border-b border-orange-800/20 transition-colors group">
                                            <TableCell className="font-mono font-bold text-orange-600">
                                                #{wo.id}
                                            </TableCell>
                                            <TableCell>
                                                <div className="space-y-1">
                                                    <div className="font-semibold text-white">{wo.machine_nom}</div>
                                                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                                                        <ExternalLink className="h-3 w-3" />
                                                        ITV #{wo.intervention_id ?? 'N/A'}
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="space-y-0.5">
                                                    <div className="text-sm font-medium flex items-center gap-1">
                                                        <User className="h-3 w-3 text-blue-400" />
                                                        {wo.technicien_nom}
                                                    </div>
                                                    <div className="text-[10px] text-muted-foreground">
                                                        {wo.technicien_email}
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <PriorityBadge priorite={wo.priorite} />
                                            </TableCell>
                                            <TableCell>
                                                <StatusBadge statut={wo.statut} />
                                            </TableCell>
                                            <TableCell>
                                                <div className="text-[11px] space-y-1">
                                                    <div className="flex items-center gap-1 text-blue-300">
                                                        <Calendar className="h-3 w-3" />
                                                        Créé: {new Date(wo.created_at).toLocaleDateString()}
                                                    </div>
                                                    {wo.date_fin && (
                                                        <div className="flex items-center gap-1 text-emerald-600">
                                                            <Clock className="h-3 w-3" />
                                                            Fin: {new Date(wo.date_fin).toLocaleDateString()}
                                                        </div>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className={`flex items-center gap-2 font-mono font-medium ${isEnCours ? 'text-amber-600' : 'text-blue-200'}`}>
                                                    <Clock className={`h-4 w-4 ${isEnCours ? 'animate-pulse' : ''}`} />
                                                    {formatDuration(duration)}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    disabled={wo.statut !== 'TERMINÉ'}
                                                    onClick={() => handleExport(wo.id)}
                                                    className="border-orange-700/50 hover:bg-orange-800/40 text-orange-100 hover:text-white shadow-sm bg-slate-800/50"
                                                >
                                                    <Download className="h-4 w-4 mr-2" />
                                                    Excel
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-end mt-4">
                <AppPagination
                    currentPage={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                />
            </div>
        </div>
    );
}
