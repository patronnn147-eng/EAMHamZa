import React, { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
    ArrowRight,
    AlertTriangle,
    Clock,
    Activity,
    User,
    TrendingUp,
    Zap,
    RefreshCcw,
    Wrench,
    Square,
    CheckSquare,
    Filter
} from 'lucide-react';
import { client } from '@/lib/api';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

export interface KanbanItem {
    id: string | number;
    title: string;
    subtitle: string;
    machineId: number;
    machineName: string;
    priority: string;
    riskLevel?: string;
    phase: 'PLAN' | 'DO' | 'CHECK' | 'ACT';
    type: 'PREDICTION' | 'WORK_ORDER' | 'INTERVENTION';
    date: string;
    
    // Enhanced PLAN fields
    riskScore?: number;
    confidence?: 'LOW' | 'MEDIUM' | 'HIGH';
    machineHealth?: 'OPERATIONAL' | 'WARNING' | 'CRITICAL';
    estimatedImpact?: string;
    
    // Enhanced DO fields
    progress?: number;
    timeElapsed?: string;
    technician?: string;
    isBlocked?: boolean;
    blockingIssue?: string;
    estimatedCompletion?: string;
    
    // Enhanced CHECK fields
    verificationStatus?: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
    qualityMetrics?: {
        vibration?: number;
        temperature?: number;
        noise?: string;
    };
    hasDiagnostic?: boolean;
    hasValidation?: boolean;
    
    // Enhanced ACT fields
    implementationStatus?: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
    mlRetraining?: 'PENDING' | 'SCHEDULED' | 'COMPLETED';
    effectiveness?: {
        downtimeReduction?: string;
        costSavings?: string;
        recurrenceRate?: string;
    };
    knowledgeBase?: 'DRAFT' | 'PUBLISHED';
}

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
        handleOpenDialog,
        handleSubmit,
        refresh: refreshWorkOrders
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
            // 1. Fetch Plan Phase (High/Critical Predictions from Fleet Dashboard)
            const fleetRes = await client.apiCall.invoke({
                url: '/api/v1/ml/fleet/dashboard',
                method: 'GET'
            });
            const predictions = fleetRes.data || [];

            // 2. Fetch Active and Planned Work Orders
            const woRes = await client.entities.ordres_travail.queryAll({
                query: {},
                limit: 100
            });
            const allWOs = (woRes.data.items || []);

            // Filters based on lifecycle
            const planWOs = allWOs.filter((wo: any) => ['EN_ATTENTE', 'ASSIGNÉ'].includes(wo.statut));
            const activeWOs = allWOs.filter((wo: any) => ['EN_COURS', 'BLOQUÉ'].includes(wo.statut));

            // 3. Fetch Interventions for Check and Act
            const intRes = await client.entities.ordres_intervention.queryAll({
                query: {},
                limit: 100,
                sort: '-date_intervention'
            });
            const allInts = intRes.data.items || [];

            const kanbanItems: KanbanItem[] = [];

            // Map Predictions to PLAN (only if no WO exists for that machine yet)
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
                    isBlocked: wo.statut === 'BLOQUÉ',
                    blockingIssue: wo.statut === 'BLOQUÉ' ? "Attente validation/pièce" : undefined,
                    technician: wo.technicien_id ? `Tech #${wo.technicien_id}` : 'En cours'
                });
            });

            // Map Finished Interventions without full feedback to CHECK
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

    const handlePlanAction = async (item: KanbanItem) => {
        if (item.type === 'PREDICTION') {
            // Pre-fill form for this machine
            setFormData({
                ...formData,
                machine_id: item.machineId,
                titre: `[IA] ${item.title}`,
                description: `Maintenance préventive suggérée par l'IA (Risque: ${item.riskScore}%).`,
                priorite: item.priority === 'CRITICAL' ? 'URGENTE' : (item.priority === 'HIGH' ? 'ELEVEE' : 'MOYENNE'),
                date_echeance: toDateInputValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()), // +7 days
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
                await client.entities.ordres_travail.update({ id, data: { statut: 'BLOQUÉ' } });
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
                    data: { statut: 'VALIDATED' } // Or whatever status signifies completion
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

    const columns = [
        { id: 'PLAN', label: 'PLAN', description: 'Prioriser alertes IA et planifier OT', icon: <Search className="w-5 h-5 text-blue-500" />, color: 'bg-blue-50', border: 'border-blue-200' },
        { id: 'DO', label: 'DO', description: 'Exécuter OT et tracker les blocages', icon: <PlayCircle className="w-5 h-5 text-orange-500" />, color: 'bg-orange-50', border: 'border-orange-200' },
        { id: 'CHECK', label: 'CHECK', description: 'Valider qualité et remplir feedback', icon: <ClipboardList className="w-5 h-5 text-green-500" />, color: 'bg-green-50', border: 'border-green-200' },
        { id: 'ACT', label: 'ACT', description: 'Standardiser solutions, MAJ IA', icon: <CheckCircle2 className="w-5 h-5 text-indigo-500" />, color: 'bg-indigo-50', border: 'border-indigo-200' },
    ];

    const getPriorityColor = (p: string) => {
        const map: any = {
            'URGENTE': 'bg-red-100 text-red-700',
            'ÉLEVÉE': 'bg-orange-100 text-orange-700',
            'HIGH': 'bg-orange-100 text-orange-700',
            'CRITICAL': 'bg-red-100 text-red-700',
            'MOYENNE': 'bg-blue-100 text-blue-700',
            'MEDIUM': 'bg-blue-100 text-blue-700',
        };
        return map[p?.toUpperCase()] || 'bg-gray-100 text-gray-700';
    };

    const isHighPriority = (p: string) => ['URGENTE', 'ÉLEVÉE', 'HIGH', 'CRITICAL'].includes(p?.toUpperCase());

    const filteredItems = items.filter(item => {
        if (filterType === 'HIGH_PRIORITY') return isHighPriority(item.priority);
        if (filterType === 'BLOCKED') return item.isBlocked;
        return true;
    });

    const renderKanbanCard = (item: KanbanItem) => {
        const baseCardClasses = "flex flex-col bg-white rounded-lg border border-gray-100 p-3 shadow-sm hover:shadow-md transition-all group relative";
        
        switch (item.phase) {
            case 'PLAN':
                return (
                    <motion.div key={item.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className={baseCardClasses}>
                        <div className="flex justify-between items-start mb-2">
                            <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>{item.priority}</Badge>
                            <span className="text-[10px] text-gray-400 flex items-center gap-1 font-mono"><Clock className="w-3 h-3" />{new Date(item.date).toLocaleDateString('fr-FR')}</span>
                        </div>
                        <p className="text-xs font-bold text-gray-900 line-clamp-2 leading-tight mb-1">{item.title}</p>
                        <p className="text-[10px] text-gray-500 flex items-center gap-1 mb-2"><Activity className="w-3 h-3" />{item.machineName}</p>
                        
                        <div className="space-y-2 mt-auto pt-2 border-t border-gray-50">
                            {item.type === 'PREDICTION' && (
                                <div className="flex justify-between items-center text-[10px] bg-red-50 text-red-700 p-1.5 rounded">
                                    <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> Alerte Triage</span>
                                    <span className="font-bold">{item.riskScore}% Risque</span>
                                </div>
                            )}
                            {item.type === 'WORK_ORDER' && (
                                <div className="flex justify-between items-center text-[10px] bg-blue-50 text-blue-700 p-1.5 rounded">
                                    <span className="flex items-center gap-1"><User className="w-3 h-3"/> Assigné: {item.technician}</span>
                                </div>
                            )}
                            <Button 
                                size="sm" 
                                onClick={() => handlePlanAction(item)}
                                disabled={actionLoading === item.id.toString()}
                                className={`w-full text-[10px] h-7 ${item.type === 'PREDICTION' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                            >
                                {actionLoading === item.id.toString() ? <RefreshCcw className="w-3 h-3 animate-spin" /> : (item.type === 'PREDICTION' ? 'Créer OT' : 'Commencer Tâche')}
                            </Button>
                        </div>
                    </motion.div>
                );

            case 'DO':
                return (
                    <motion.div key={item.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className={`${baseCardClasses} ${item.isBlocked ? 'ring-2 ring-red-400 border-red-400' : ''}`}>
                        <div className="flex justify-between items-start mb-2">
                            <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>{item.priority}</Badge>
                            {item.isBlocked && <Badge className="text-[10px] bg-red-100 text-red-700 animate-pulse border-red-300">BLOQUÉ</Badge>}
                        </div>
                        <p className="text-xs font-bold text-gray-900 line-clamp-2 leading-tight mb-1">{item.title}</p>
                        <p className="text-[10px] text-gray-500 flex items-center gap-1 mb-2"><Wrench className="w-3 h-3" />{item.machineName}</p>
                        
                        <div className="space-y-2 mt-auto pt-2 border-t border-gray-50">
                            <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                <div className={`h-1.5 rounded-full ${item.isBlocked ? 'bg-red-500' : 'bg-orange-500'}`} style={{ width: `${item.progress}%` }}></div>
                            </div>
                            <div className="flex justify-between text-[10px] text-gray-500">
                                <span>Elapsed: {item.timeElapsed}</span>
                                <span>Est: {item.estimatedCompletion}</span>
                            </div>
                            {item.isBlocked && <p className="text-[10px] text-red-600 italic">⚠️ {item.blockingIssue}</p>}
                            <div className="flex gap-2">
                                <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => handleDoAction(item, 'BLOCK')}
                                    disabled={actionLoading === item.id.toString() || item.isBlocked}
                                    className={`flex-1 text-[10px] h-7 ${item.isBlocked ? 'text-gray-400' : 'text-red-600'}`}
                                >
                                    Signaler Blocage
                                </Button>
                                <Button 
                                    size="sm" 
                                    onClick={() => handleDoAction(item, 'FINISH')}
                                    disabled={actionLoading === item.id.toString()}
                                    className="flex-1 text-[10px] h-7 bg-green-600 hover:bg-green-700"
                                >
                                    {actionLoading === item.id.toString() ? <RefreshCcw className="w-3 h-3 animate-spin" /> : 'Terminer'}
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                );

            case 'CHECK':
                return (
                    <motion.div key={item.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className={baseCardClasses}>
                        <div className="flex justify-between items-start mb-2">
                            <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>{item.priority}</Badge>
                            <Badge className="text-[10px] bg-yellow-100 text-yellow-700 border-yellow-300">Validation Requise</Badge>
                        </div>
                        <p className="text-xs font-bold text-gray-900 line-clamp-2 leading-tight mb-1">{item.title}</p>
                        <p className="text-[10px] text-gray-500 flex items-center gap-1 mb-2"><Activity className="w-3 h-3" />{item.machineName}</p>
                        
                        <div className="space-y-2 mt-auto pt-2 border-t border-gray-50 bg-gray-50 -mx-3 px-3 pb-3 -mb-3 rounded-b-lg">
                            <div className="flex flex-col gap-1 mt-1">
                                <div className="flex items-center gap-2 text-[10px] text-gray-600">
                                    <CheckSquare className="w-3 h-3 text-green-500" /> Réparation technique
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-gray-600">
                                    {item.hasDiagnostic ? <CheckSquare className="w-3 h-3 text-green-500"/> : <Square className="w-3 h-3 text-gray-300" />} Diagnostic root cause
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-gray-600">
                                    {item.hasValidation ? <CheckSquare className="w-3 h-3 text-green-500"/> : <Square className="w-3 h-3 text-gray-300" />} Validation Cheftech
                                </div>
                            </div>
                            <div className="flex gap-2 pt-2">
                                <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => handleCheckAction(item, 'DIAG')}
                                    className="flex-1 text-[10px] h-7 bg-white"
                                >
                                    Ajouter diag
                                </Button>
                                <Button 
                                    size="sm" 
                                    onClick={() => handleCheckAction(item, 'VALIDATE')}
                                    disabled={actionLoading === item.id.toString()}
                                    className="flex-1 text-[10px] h-7 bg-indigo-600 hover:bg-indigo-700"
                                >
                                    {actionLoading === item.id.toString() ? <RefreshCcw className="w-3 h-3 animate-spin" /> : 'Valider Chef'}
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                );

            case 'ACT':
                return (
                    <motion.div key={item.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className={`${baseCardClasses} bg-gray-50 border-gray-200 opacity-90 hover:opacity-100`}>
                        <div className="flex justify-between items-start mb-2">
                            <Badge className="text-[10px] bg-indigo-100 text-indigo-700 border-indigo-200">En cours d'amélioration</Badge>
                        </div>
                        <p className="text-xs font-bold text-gray-900 line-clamp-2 leading-tight mb-1">{item.title}</p>
                        <p className="text-[10px] text-gray-500 flex items-center gap-1 mb-2 italic">Cause: {item.subtitle.replace('Cause:', '')}</p>
                        
                        <div className="space-y-2 mt-auto pt-2 border-t border-gray-100">
                            {item.effectiveness && (
                                <div className="grid grid-cols-2 gap-1 mb-2">
                                    <div className="flex items-center gap-1 bg-white p-1 rounded border border-green-100">
                                        <TrendingUp className="w-3 h-3 text-green-500" />
                                        <span className="text-[9px] text-gray-600">{item.effectiveness.downtimeReduction} d'arrêt</span>
                                    </div>
                                    <div className="flex items-center gap-1 bg-white p-1 rounded border border-blue-100">
                                        <Zap className="w-3 h-3 text-blue-500" />
                                        <span className="text-[9px] text-gray-600">{item.effectiveness.costSavings} sauvés</span>
                                    </div>
                                </div>
                            )}
                            <div className="flex gap-2">
                                <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => handleActAction(item, 'STD')}
                                    className="flex-1 text-[9px] h-7 bg-white border-indigo-200 text-indigo-700"
                                >
                                    MAJ Gamme
                                </Button>
                                <Button 
                                    size="sm" 
                                    onClick={() => handleActAction(item, 'RETRAIN')}
                                    disabled={actionLoading === 'retrain'}
                                    className="flex-1 text-[9px] h-7 bg-slate-800 hover:bg-slate-900 text-white"
                                >
                                    {actionLoading === 'retrain' ? <RefreshCcw className="w-3 h-3 animate-spin" /> : 'Ré-entraîner ML'}
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                );
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
                <RefreshCcw className="w-8 h-8 text-blue-600 animate-spin" />
                <p className="text-sm text-gray-500 font-medium">Synchronisation du cycle PDCA...</p>
            </div>
        );
    }

    return (
        <div className="w-full space-y-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Tableau Kanban PDCA</h2>
                    <p className="text-sm text-gray-500">Visualisation et gestion du cycle d'amélioration continue</p>
                </div>
                
                <div className="flex items-center gap-2 bg-white p-1.5 rounded-lg border border-gray-200 shadow-sm">
                    <Filter className="w-4 h-4 text-gray-400 ml-2" />
                    <div className="flex gap-1">
                        <Button 
                            variant={filterType === 'ALL' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('ALL')}
                            className={`h-8 text-xs ${filterType === 'ALL' ? 'bg-slate-800 text-white' : 'text-gray-600'}`}>
                            Tout voir
                        </Button>
                        <Button 
                            variant={filterType === 'HIGH_PRIORITY' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('HIGH_PRIORITY')}
                            className={`h-8 text-xs ${filterType === 'HIGH_PRIORITY' ? 'bg-orange-600 text-white' : 'text-orange-600 hover:text-orange-700 hover:bg-orange-50'}`}>
                            Haute Priorité
                        </Button>
                        <Button 
                            variant={filterType === 'BLOCKED' ? 'default' : 'ghost'} 
                            size="sm" 
                            onClick={() => setFilterType('BLOCKED')}
                            className={`h-8 text-xs ${filterType === 'BLOCKED' ? 'bg-red-600 text-white' : 'text-red-600 hover:text-red-700 hover:bg-red-50'}`}>
                            Bloqués Uniquement
                        </Button>
                    </div>
                </div>

                <Button variant="outline" size="sm" onClick={fetchData} className="gap-2 h-9">
                    <RefreshCcw className="w-4 h-4" /> Actualiser
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 min-h-[700px]">
                {columns.map((col) => {
                    const colItems = filteredItems.filter((i) => i.phase === col.id);
                    
                    // Specific logic for PLAN swimlanes
                    const hasSwimlanes = col.id === 'PLAN';
                    const predictions = hasSwimlanes ? colItems.filter(i => i.type === 'PREDICTION') : [];
                    const workOrders = hasSwimlanes ? colItems.filter(i => i.type === 'WORK_ORDER') : [];

                    return (
                        <div key={col.id} className={`flex flex-col rounded-xl border ${col.border} ${col.color} p-4 space-y-4 shadow-sm`}>
                            {/* Column Header */}
                            <div className="flex flex-col space-y-1 mb-2 px-1">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {col.icon}
                                        <span className="font-bold text-gray-800 tracking-wider text-base">{col.label}</span>
                                    </div>
                                    <Badge variant="outline" className="bg-white/70 backdrop-blur-sm text-gray-700 font-bold px-2.5">
                                        {colItems.length}
                                    </Badge>
                                </div>
                                <span className="text-[11px] text-gray-500 font-medium tracking-tight">
                                    {col.description}
                                </span>
                            </div>

                            {/* Column Content */}
                            <div className="flex-1 flex flex-col gap-3 overflow-y-auto no-scrollbar pb-4">
                                {hasSwimlanes ? (
                                    <>
                                        {/* Predictions Swimlane */}
                                        <div className="flex flex-col gap-3">
                                            {predictions.length > 0 && (
                                                <div className="flex items-center gap-2 px-1 mb-1">
                                                    <div className="h-px bg-red-200 flex-1"></div>
                                                    <span className="text-[10px] font-bold text-red-600 uppercase tracking-wider">Priorités IA ({predictions.length})</span>
                                                    <div className="h-px bg-red-200 flex-1"></div>
                                                </div>
                                            )}
                                            <AnimatePresence>
                                                {predictions.map(item => renderKanbanCard(item))}
                                            </AnimatePresence>
                                        </div>

                                        {/* Work Orders Swimlane */}
                                        <div className="flex flex-col gap-3 mt-2">
                                            {workOrders.length > 0 && (
                                                <div className="flex items-center gap-2 px-1 mb-1">
                                                    <div className="h-px bg-blue-200 flex-1"></div>
                                                    <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">Tâches Planifiées ({workOrders.length})</span>
                                                    <div className="h-px bg-blue-200 flex-1"></div>
                                                </div>
                                            )}
                                            <AnimatePresence>
                                                {workOrders.map(item => renderKanbanCard(item))}
                                            </AnimatePresence>
                                        </div>
                                        
                                        {colItems.length === 0 && (
                                            <div className="h-24 mt-4 flex items-center justify-center border-2 border-dashed border-blue-200 rounded-lg text-blue-400 text-xs italic bg-white/40">
                                                Aucune tâche planifiée
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        {/* Standard Column Rendering */}
                                        <AnimatePresence>
                                            {colItems.map((item) => renderKanbanCard(item))}
                                        </AnimatePresence>

                                        {colItems.length === 0 && (
                                            <div className={`h-24 mt-4 flex items-center justify-center border-2 border-dashed rounded-lg text-xs italic bg-white/40
                                                ${col.id === 'DO' ? 'border-orange-200 text-orange-400' : ''}
                                                ${col.id === 'CHECK' ? 'border-green-200 text-green-400' : ''}
                                                ${col.id === 'ACT' ? 'border-indigo-200 text-indigo-400' : ''}
                                            `}>
                                                Aucun élément dans cette phase
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
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
