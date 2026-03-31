import React, { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { getAPIBaseURL } from '@/lib/config';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Search, Clock, Calendar, User, ExternalLink } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { 
    Table, 
    TableBody, 
    TableCell, 
    TableHead, 
    TableHeader, 
    TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { PriorityBadge, StatusBadge } from '@/modules/shared/work-orders/utils/badges';
import { toast } from 'sonner';

interface AdminWorkOrder {
    id: number;
    titre: string;
    description: string;
    priorite: string;
    statut: string;
    machine_id: number;
    machine_nom: string;
    chefop_id: number | null;
    chefop_nom: string;
    chefop_email: string;
    intervention_id: number | null;
    created_at: string;
    date_debut: string | null;
    date_fin: string | null;
    duration_minutes: number;
}

export default function AdminWorkOrdersTable() {
    const [workOrders, setWorkOrders] = useState<AdminWorkOrder[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentTime, setCurrentTime] = useState(new Date());
    
    // Timer to update live durations
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const fetchWorkOrders = async () => {
        try {
            const apiBase = getAPIBaseURL();
            const response = await fetch(`${apiBase}/api/v1/admin/work-orders`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            if (!response.ok) throw new Error('Failed to fetch');
            const data = await response.json();
            setWorkOrders(data);
        } catch (error) {
            console.error('Error fetching admin work orders:', error);
            toast.error("Erreur lors du chargement des ordres de travail");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWorkOrders();
    }, []);

    const handleExport = async (woId: number) => {
        try {
            toast.info("Génération du rapport en cours...");
            const apiBase = getAPIBaseURL();
            const response = await fetch(`${apiBase}/api/v1/admin/work-orders/${woId}/export`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            if (!response.ok) throw new Error('Export failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Rapport_OT_${woId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success("Rapport téléchargé avec succès");
        } catch (error) {
            console.error('Export error:', error);
            toast.error("Erreur lors de l'export du rapport");
        }
    };

    const calculateLiveDuration = (dateDebutStr: string | null) => {
        if (!dateDebutStr) return 0;
        const start = new Date(dateDebutStr);
        const diff = currentTime.getTime() - start.getTime();
        return Math.floor(diff / 60000); // Minutes
    };

    const formatDuration = (minutes: number) => {
        if (minutes < 0) return "0 min";
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        if (h > 0) return `${h}h ${m}min`;
        return `${m} min`;
    };

    const filtered = workOrders.filter(wo => 
        wo.titre.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wo.machine_nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wo.chefop_nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
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
                        Gestion des Ordres de Travail
                    </h1>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Suivi en temps réel, monitoring de la durée et export des rapports PDCA.
                    </p>
                </div>
            </div>

            <Card className="border-none shadow-xl bg-white/50 backdrop-blur-sm overflow-hidden">
                <CardHeader className="border-b bg-gray-50/50 pb-4">
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <Input
                                placeholder="Rechercher par ID, Titre, Machine ou ChefOp..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-9 bg-white border-gray-200"
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader className="bg-gray-50/80">
                                <TableRow>
                                    <TableHead className="w-[80px] font-bold">ID</TableHead>
                                    <TableHead className="min-w-[200px] font-bold">Machine & Intervention</TableHead>
                                    <TableHead className="min-w-[180px] font-bold">Chef Opérateur</TableHead>
                                    <TableHead className="font-bold">Priorité</TableHead>
                                    <TableHead className="font-bold">Statut</TableHead>
                                    <TableHead className="font-bold">Dates</TableHead>
                                    <TableHead className="font-bold">Chrono (Durée)</TableHead>
                                    <TableHead className="text-right font-bold">Rapport</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filtered.map((wo) => {
                                    const isEnCours = wo.statut === 'EN_COURS';
                                    const duration = isEnCours 
                                        ? calculateLiveDuration(wo.date_debut) 
                                        : wo.duration_minutes;

                                    return (
                                        <TableRow key={wo.id} className="hover:bg-blue-50/30 transition-colors group">
                                            <TableCell className="font-mono font-bold text-blue-600">
                                                #{wo.id}
                                            </TableCell>
                                            <TableCell>
                                                <div className="space-y-1">
                                                    <div className="font-semibold text-gray-900">{wo.machine_nom}</div>
                                                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                                                        <ExternalLink className="h-3 w-3" />
                                                        ITV #{wo.intervention_id || 'N/A'}
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="space-y-0.5">
                                                    <div className="text-sm font-medium flex items-center gap-1">
                                                        <User className="h-3 w-3 text-gray-400" />
                                                        {wo.chefop_nom}
                                                    </div>
                                                    <div className="text-[10px] text-muted-foreground">
                                                        {wo.chefop_email}
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
                                                    <div className="flex items-center gap-1 text-gray-500">
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
                                                <div className={`flex items-center gap-2 font-mono font-medium ${isEnCours ? 'text-amber-600' : 'text-gray-600'}`}>
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
                                                    className="border-blue-200 hover:bg-blue-50 text-blue-600 shadow-sm"
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
        </div>
    );
}
