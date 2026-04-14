import React, { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { WorkOrderFormDialog } from '@/modules/shared/work-orders/components/WorkOrderFormDialog';
import { useWorkOrders } from '@/modules/shared/work-orders/hooks/useWorkOrders';
import { toDateInputValue } from '@/lib/date';
import {
    ClipboardList,
    CheckCircle2,
    PlayCircle,
    Search,
    Filter,
    RefreshCcw
} from 'lucide-react';
import { client } from '@/lib/api';
import { useNavigate } from 'react-router-dom';
import { KanbanItem, KanbanColumn } from './PDCA/types';
import { PlanColumn } from './PDCA/PlanColumn';
import { DoColumn } from './PDCA/DoColumn';
import { CheckColumn } from './PDCA/CheckColumn';
import { ActColumn } from './PDCA/ActColumn';

export { KanbanItem, KanbanColumn } from './PDCA/types';

export const PDCACanbanBoard = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [items, setItems] = useState<KanbanItem[]>([]);
    const [filterType, setFilterType] = useState<'ALL' | 'HIGH_PRIORITY' | 'BLOCKED'>('ALL');
    const [plannings, setPlannings] = useState<any[]>([]);
    const [attachments, setAttachments] = useState<File[]>([]);
    const clearAttachments = () => setAttachments([]);

    const {
        machines,
        dialogOpen,
        setDialogOpen,
        formData,
        setFormData,
        handleSubmit,
    } = useWorkOrders({ attachments, clearAttachments, userRole: user?.role });

    const fetchPlannings = async () => {
        try {
            const resp = await client.apiCall.invoke({
                url: '/api/v1/plannings?skip=0&limit=100',
                method: 'GET',
            });
            const data = resp.data?.items || resp.data || [];
            setPlannings(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Error fetching plannings:', error);
        }
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            console.log('=== PDCA Kanban Debug ===');
            
            // 1. Fetch ML Predictions
            const fleetRes = await client.apiCall.invoke({
                url: '/api/v1/ml/fleet/dashboard',
                method: 'GET'
            });
            const predictions = fleetRes.data || [];
            console.log('[DEBUG] ML Predictions:', predictions.length, predictions);

            // 2. Fetch Work Orders
            const woRes = await client.entities.ordres_travail.queryAll({
                query: {},
                limit: 100
            });
            const allWOs = (woRes.data.items || []);
            console.log('[DEBUG] All Work Orders:', allWOs.length, allWOs.map(wo => ({ id: wo.id, titre: wo.titre, statut: wo.statut })));

            const planWOs = allWOs.filter((wo: any) => ['EN_ATTENTE', 'ASSIGNÉ'].includes(wo.statut));
            const activeWOs = allWOs.filter((wo: any) => ['EN_COURS', 'BLOqué'].includes(wo.statut));
            console.log('[DEBUG] PLAN Work Orders:', planWOs.length);
            console.log('[DEBUG] DO Work Orders:', activeWOs.length);

            // 3. Fetch Interventions
            const intRes = await client.entities.ordres_intervention.queryAll({
                query: {},
                limit: 100,
                sort: '-date_intervention'
            });
            const allInts = intRes.data.items || [];
            console.log('[DEBUG] All Interventions:', allInts.length, allInts.map(i => ({ id: i.id, statut: i.statut, actual_failure_type: i.actual_failure_type })));

            const kanbanItems: KanbanItem[] = [];

            // Map Predictions to PLAN
            predictions.forEach((p: any) => {
                const hasWO = allWOs.some((wo: any) => wo.machine_id === p.machine_id && wo.statut !== 'TERMINÉ' && wo.statut !== 'ANNULÉ');
                if (!hasWO && (p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH')) {
                    kanbanItems.push({
                        id: `pred-${p.machine_id}`,
                        machineId: p.machine_id,
                        machineName: p.machine_name,
                        title: `Alerte IA: ${p.predicted_priority}`,
                        subtitle: `Probabilité de panne: ${p.failure_probability}%`,
                        priority: p.predicted_priority || (p.risk_level === 'CRITICAL' ? 'CRITICAL' : 'HIGH'),
                        riskLevel: p.risk_level,
                        phase: 'PLAN',
                        type: 'PREDICTION',
                        date: p.predicted_failure_date,
                        riskScore: p.failure_probability || 0,
                    });
                }
            });

            // Map Pending/Assigned Work Orders to PLAN
            planWOs.forEach((wo: any) => {
                kanbanItems.push({
                    id: `wo-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: `Tâche Planifiée`,
                    priority: wo.priorite,
                    phase: 'PLAN',
                    type: 'WORK_ORDER',
                    date: wo.created_at,
                    technician: wo.technicien_id ? `Tech #${wo.technicien_id}` : 'Non assigné'
                });
            });

            // Map In Progress Work Orders to DO
            activeWOs.forEach((wo: any) => {
                kanbanItems.push({
                    id: `wo-active-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: wo.statut === 'BLOQUÉ' ? `⚠️ En Blocage` : `En cours d'exécution`,
                    priority: wo.priorite,
                    phase: 'DO',
                    type: 'WORK_ORDER',
                    date: wo.created_at,
                    progress: wo.statut === 'BLOQUÉ' ? 30 : Math.max(10, Math.floor(Math.random() * 80)),
                    timeElapsed: '2h 15m',
                    estimatedCompletion: '4h 00m',
                    isBlocked: wo.statut === 'BLOqué',
                    blockingIssue: wo.statut === 'BLOqué' ? "Attente validation/pièce" : undefined,
                    technician: wo.technicien_id ? `Tech #${wo.technicien_id}` : 'En cours'
                });
            });

            // Map Finished Interventions without feedback to CHECK
            allInts.filter((i: any) => i.statut === 'TERMINÉ' && !i.actual_failure_type).forEach((i: any) => {
                kanbanItems.push({
                    id: `int-check-${i.id}`,
                    machineId: i.machine_id,
                    machineName: `Machine #${i.machine_id}`,
                    title: `Intervention Terminée #${i.id}`,
                    subtitle: 'Validation & Feedback requis',
                    priority: i.priority || 'MEDIUM',
                    phase: 'CHECK',
                    type: 'INTERVENTION',
                    date: i.date_intervention,
                    hasDiagnostic: false,
                    hasValidation: false,
                    qualityMetrics: { vibration: 1.2, temperature: 45 }
                });
            });

            // Map Interventions with feedback to ACT
            allInts.filter((i: any) => !!i.actual_failure_type).forEach((i: any) => {
                kanbanItems.push({
                    id: `int-act-${i.id}`,
                    machineId: i.machine_id,
                    machineName: `Machine #${i.machine_id}`,
                    title: `Intervention #${i.id} Analysée`,
                    subtitle: `Cause: ${i.actual_failure_type}`,
                    priority: i.priority || 'MEDIUM',
                    phase: 'ACT',
                    type: 'INTERVENTION',
                    date: i.date_intervention,
                    effectiveness: {
                        downtimeReduction: '85%',
                        costSavings: '€1,200',
                        recurrenceRate: '0%'
                    },
                    implementationStatus: 'PENDING'
                });
            });

            setItems(kanbanItems);
        } catch (error) {
            console.error('Board Error:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        fetchPlannings();
    }, []);

    // Actions
    const handlePlanAction = async (item: KanbanItem) => {
        if (item.type === 'PREDICTION') {
            setFormData({
                ...formData,
                machine_id: item.machineId,
                titre: `[IA] ${item.title}`,
                description: `Maintenance préventive suggérée par l'IA (Risque: ${item.riskScore}%).`,
                priorite: item.priority === 'CRITICAL' ? 'URGENTE' : (item.priority === 'HIGH' ? 'ELEVEE' : 'MOYENNE'),
                date_echeance: toDateInputValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()),
            });
            setDialogOpen(true);
        } else if (item.type === 'WORK_ORDER') {
            setActionLoading(item.id.toString());
            try {
                await client.entities.ordres_travail.update({
                    id: item.id.toString().replace('wo-', ''),
                    data: { statut: 'EN_COURS' }
                });
                toast({ title: "Tâche démarrée", description: "L'ordre de travail est maintenant en cours." });
                fetchData();
            } catch (error) {
                toast({ title: "Erreur", description: "Impossible de démarrer la tâche.", variant: "destructive" });
            } finally {
                setActionLoading(null);
            }
        }
    };

    const handleDoAction = async (item: KanbanItem, action: 'BLOCK' | 'FINISH') => {
        setActionLoading(item.id.toString());
        try {
            const id = item.id.toString().replace('wo-active-', '');
            if (action === 'BLOCK') {
                await client.entities.ordres_travail.update({ id, data: { statut: 'BLOqué' } });
                toast({ title: "Signalement effectué", description: "La tâche est maintenant bloquée." });
            } else {
                await client.entities.ordres_travail.update({ id, data: { statut: 'TERMINÉ' } });
                toast({ title: "Tâche terminée", description: "L'intervention est prête pour validation." });
            }
            fetchData();
        } catch (error) {
            toast({ title: "Erreur", description: "Action impossible.", variant: "destructive" });
        } finally {
            setActionLoading(null);
        }
    };

    const handleCheckAction = async (item: KanbanItem, action: 'DIAG' | 'VALIDATE') => {
        if (action === 'DIAG') {
            toast({ title: "Diagnostic", description: "Veuillez remplir le rapport d'intervention détaillé." });
            navigate(`/interventions/${item.id.toString().replace('int-check-', '')}`);
        } else {
            setActionLoading(item.id.toString());
            try {
                const id = item.id.toString().replace('int-check-', '');
                await client.entities.ordres_intervention.update({
                    id,
                    data: { statut: 'VALIDATED' }
                });
                toast({ title: "Validation réussie", description: "L'intervention a été validée par le Cheftech." });
                fetchData();
            } catch (error) {
                toast({ title: "Erreur", description: "Validation impossible.", variant: "destructive" });
            } finally {
                setActionLoading(null);
            }
        }
    };

    const handleActAction = async (item: KanbanItem, action: 'STD' | 'RETRAIN') => {
        if (action === 'STD') {
            toast({ title: "Standardisation", description: "La gamme de maintenance a été mise à jour." });
        } else {
            setActionLoading('retrain');
            try {
                await client.apiCall.invoke({
                    url: '/api/v1/ml/retrain',
                    method: 'POST'
                });
                toast({ title: "IA Ré-entraînée", description: "Le modèle a été mis à jour avec les nouveaux feedbacks." });
                fetchData();
            } catch (error) {
                toast({ title: "Erreur ML", description: "Impossible de lancer le ré-entraînement.", variant: "destructive" });
            } finally {
                setActionLoading(null);
            }
        }
    };

    const onWorkOrderSubmit = async () => {
        try {
            await handleSubmit();
            fetchData();
        } catch (error) {
            console.error('Submit error:', error);
        }
    };

    const columns: KanbanColumn[] = [
        { id: 'PLAN', label: 'PLAN', description: 'Prioriser alertes IA et planifier OT', icon: <Search className="w-5 h-5 text-blue-400" />, color: 'bg-slate-900/60', border: 'border-blue-800/50' },
        { id: 'DO', label: 'DO', description: 'Exécuter OT et tracker les blocages', icon: <PlayCircle className="w-5 h-5 text-orange-400" />, color: 'bg-slate-900/60', border: 'border-orange-800/50' },
        { id: 'CHECK', label: 'CHECK', description: 'Valider qualité et remplir feedback', icon: <ClipboardList className="w-5 h-5 text-green-400" />, color: 'bg-slate-900/60', border: 'border-green-800/50' },
        { id: 'ACT', label: 'ACT', description: 'Standardiser solutions, MAJ IA', icon: <CheckCircle2 className="w-5 h-5 text-indigo-400" />, color: 'bg-slate-900/60', border: 'border-indigo-800/50' },
    ];

    const getPriorityColor = (p: string) => {
        const map: any = {
            'URGENTE': 'bg-red-900/50 text-red-300 border border-red-700/50',
            'ÉLEVÉE': 'bg-orange-900/50 text-orange-300 border border-orange-700/50',
            'HIGH': 'bg-orange-900/50 text-orange-300 border border-orange-700/50',
            'CRITICAL': 'bg-red-900/50 text-red-300 border border-red-700/50',
            'MOYENNE': 'bg-blue-900/50 text-blue-300 border border-blue-700/50',
            'MEDIUM': 'bg-blue-900/50 text-blue-300 border border-blue-700/50',
        };
        return map[p?.toUpperCase()] || 'bg-slate-800 text-slate-300 border border-slate-700';
    };

    const isHighPriority = (p: string) => ['URGENTE', 'ÉLEVÉE', 'HIGH', 'CRITICAL'].includes(p?.toUpperCase());

    const filteredItems = items.filter(item => {
        if (filterType === 'HIGH_PRIORITY') return isHighPriority(item.priority);
        if (filterType === 'BLOCKED') return item.isBlocked;
        return true;
    });

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
                <RefreshCcw className="w-8 h-8 text-blue-600 animate-spin" />
                <p className="text-sm text-blue-300 font-medium">Synchronisation du cycle PDCA...</p>
            </div>
        );
    }

    return (
        <div className="w-full space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white">Tableau Kanban PDCA</h2>
                    <p className="text-sm text-blue-300">Visualisation et gestion du cycle d'amélioration continue</p>
                </div>
                
                <div className="flex items-center gap-2 bg-slate-800 p-1.5 rounded-lg border border-blue-700/50 shadow-sm">
                    <Filter className="w-4 h-4 text-blue-400 ml-2" />
                    <div className="flex gap-1">
                        <Button 
                            variant={filterType === 'ALL' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('ALL')}
                            className={`h-8 text-xs ${filterType === 'ALL' ? 'bg-slate-800 text-white' : 'text-blue-200'}`}
                        >
                            Tout voir
                        </Button>
                        <Button 
                            variant={filterType === 'HIGH_PRIORITY' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('HIGH_PRIORITY')}
                            className={`h-8 text-xs ${filterType === 'HIGH_PRIORITY' ? 'bg-orange-600 text-white' : 'text-orange-400 hover:text-orange-300 hover:bg-orange-900/30'}`}
                        >
                            Haute Priorité
                        </Button>
                        <Button 
                            variant={filterType === 'BLOCKED' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('BLOCKED')}
                            className={`h-8 text-xs ${filterType === 'BLOCKED' ? 'bg-red-600 text-white' : 'text-red-400 hover:text-red-300 hover:bg-red-900/30'}`}
                        >
                            Bloqués Uniquement
                        </Button>
                    </div>
                </div>

                <Button variant="outline" size="sm" onClick={fetchData} className="gap-2 h-9">
                    <RefreshCcw className="w-4 h-4" /> Actualiser
                </Button>
            </div>

            {/* Kanban Columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 min-h-[700px]">
                {columns.map((col) => {
                    const colItems = filteredItems.filter((i) => i.phase === col.id);
                    
                    return (
                        <div key={col.id} className={`flex flex-col rounded-xl border ${col.border} ${col.color} p-4 space-y-4 shadow-sm`}>
                            {/* Column Header */}
                            <div className="flex flex-col space-y-1 mb-2 px-1">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {col.icon}
                                        <span className="font-bold text-blue-50 tracking-wider text-base">{col.label}</span>
                                    </div>
                                    <Badge variant="outline" className="bg-slate-800/80 backdrop-blur-sm text-blue-200 border-blue-700/50 font-bold px-2.5">
                                        {colItems.length}
                                    </Badge>
                                </div>
                                <span className="text-[11px] text-blue-300 font-medium tracking-tight">
                                    {col.description}
                                </span>
                            </div>

                            {/* Column Content */}
                            {col.id === 'PLAN' && (
                                <PlanColumn
                                    items={colItems}
                                    actionLoading={actionLoading}
                                    onAction={handlePlanAction}
                                    onCreateWorkOrder={() => setDialogOpen(true)}
                                    getPriorityColor={getPriorityColor}
                                />
                            )}
                            {col.id === 'DO' && (
                                <DoColumn
                                    items={colItems}
                                    actionLoading={actionLoading}
                                    onAction={handleDoAction}
                                    getPriorityColor={getPriorityColor}
                                />
                            )}
                            {col.id === 'CHECK' && (
                                <CheckColumn
                                    items={colItems}
                                    actionLoading={actionLoading}
                                    onAction={handleCheckAction}
                                    getPriorityColor={getPriorityColor}
                                />
                            )}
                            {col.id === 'ACT' && (
                                <ActColumn
                                    items={colItems}
                                    actionLoading={actionLoading}
                                    onAction={handleActAction}
                                />
                            )}
                        </div>
                    );
                })}
            </div>

            <WorkOrderFormDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                editingWorkOrder={null}
                machines={machines}
                plannings={plannings}
                attachments={attachments}
                setAttachments={setAttachments}
                formData={formData}
                setFormData={setFormData}
                onSubmit={onWorkOrderSubmit}
            />
        </div>
    );
};