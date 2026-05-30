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

            // WO lifecycle: DRAFT → SUBMITTED → APPROVED → ASSIGNED → IN_PROGRESS → COMPLETED → VALIDATED → CLOSED
            const planWOs = allWOs.filter((wo: any) => ['DRAFT', 'SUBMITTED', 'APPROVED'].includes(wo.statut));
            const activeWOs = allWOs.filter((wo: any) => ['ASSIGNED', 'IN_PROGRESS'].includes(wo.statut));
            // Also include COMPLETED WOs that haven't been validated yet in CHECK
            const completedWOs = allWOs.filter((wo: any) => wo.statut === 'COMPLETED');
            console.log('[DEBUG] PLAN Work Orders:', planWOs.length);
            console.log('[DEBUG] DO Work Orders:', activeWOs.length);
            console.log('[DEBUG] COMPLETED Work Orders (→CHECK):', completedWOs.length);

            // 3. Fetch Interventions
            const intRes = await client.entities.ordres_intervention.queryAll({
                query: {},
                limit: 100,
                sort: '-date_intervention'
            });
            const allInts = intRes.data.items || [];
            console.log('[DEBUG] All Interventions:', allInts.length, allInts.map(i => ({ id: i.id, statut: i.statut, actual_failure_type: i.actual_failure_type })));

            const kanbanItems: KanbanItem[] = [];

            // ── PLAN: ML predictions without active WO ──
            const ACTIVE_STATUSES = ['DRAFT', 'SUBMITTED', 'APPROVED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED'];
            predictions.forEach((p: any) => {
                const hasActiveWO = allWOs.some((wo: any) =>
                    wo.machine_id === p.machine_id && ACTIVE_STATUSES.includes(wo.statut)
                );
                if (!hasActiveWO && (p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH')) {
                    kanbanItems.push({
                        id: `pred-${p.machine_id}`,
                        machineId: p.machine_id,
                        machineName: p.machine_name,
                        title: `AI Alert: ${p.predicted_priority || 'High Risk'}`,
                        subtitle: `Failure probability: ${p.failure_probability}%`,
                        priority: p.predicted_priority || (p.risk_level === 'CRITICAL' ? 'CRITICAL' : 'HIGH'),
                        riskLevel: p.risk_level,
                        phase: 'PLAN',
                        type: 'PREDICTION',
                        date: p.predicted_failure_date,
                        riskScore: p.failure_probability || 0,
                    });
                }
            });

            // ── PLAN: Work orders awaiting assignment / start ──
            planWOs.forEach((wo: any) => {
                const statusLabel = wo.statut === 'DRAFT' ? 'Draft — needs approval'
                    : wo.statut === 'SUBMITTED' ? 'Awaiting CHEFTECH approval'
                    : 'Approved — ready to assign';
                kanbanItems.push({
                    id: `wo-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: statusLabel,
                    priority: wo.priorite,
                    phase: 'PLAN',
                    type: 'WORK_ORDER',
                    date: wo.created_at,
                    technician: wo.utilisateur_id ? `Tech #${wo.utilisateur_id}` : 'Unassigned',
                    statut: wo.statut,
                });
            });

            // ── DO: Work orders assigned / in progress ──
            activeWOs.forEach((wo: any) => {
                kanbanItems.push({
                    id: `wo-active-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: wo.statut === 'ASSIGNED'
                        ? 'Assigned — technician to start'
                        : 'In progress',
                    priority: wo.priorite,
                    phase: 'DO',
                    type: 'WORK_ORDER',
                    date: wo.created_at,
                    progress: wo.statut === 'IN_PROGRESS' ? 50 : 10,
                    timeElapsed: '—',
                    estimatedCompletion: '—',
                    technician: wo.utilisateur_id ? `Tech #${wo.utilisateur_id}` : 'Unassigned',
                    statut: wo.statut,
                });
            });

            // ── CHECK: Completed WOs awaiting CHEFTECH validation ──
            completedWOs.forEach((wo: any) => {
                kanbanItems.push({
                    id: `wo-check-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: 'Completed — needs CHEFTECH validation',
                    priority: wo.priorite,
                    phase: 'CHECK',
                    type: 'WORK_ORDER',
                    date: wo.date_fin || wo.created_at,
                    hasDiagnostic: false,
                    hasValidation: false,
                    statut: wo.statut,
                });
            });

            // ── CHECK: Interventions completed but not yet validated by CHEFTECH ──
            allInts
                .filter((i: any) => i.statut === 'TERMINÉ')
                .forEach((i: any) => {
                    kanbanItems.push({
                        id: `int-check-${i.id}`,
                        machineId: i.machine_id,
                        machineName: `Machine #${i.machine_id}`,
                        title: `Intervention #${i.id}`,
                        subtitle: i.actual_failure_type
                            ? 'Diagnosis done — needs CHEFTECH validation'
                            : 'Needs root-cause diagnosis + validation',
                        priority: i.priority || 'MEDIUM',
                        phase: 'CHECK',
                        type: 'INTERVENTION',
                        date: i.date_intervention,
                        hasDiagnostic: !!i.actual_failure_type,
                        hasValidation: false,
                        statut: i.statut,
                    });
                });

            // ── ACT: Validated interventions with diagnosis ──
            // These feed the retrain queue and standardization
            allInts
                .filter((i: any) => i.statut === 'VALIDATED' && !!i.actual_failure_type)
                .forEach((i: any) => {
                    kanbanItems.push({
                        id: `int-act-${i.id}`,
                        machineId: i.machine_id,
                        machineName: `Machine #${i.machine_id}`,
                        title: `Intervention #${i.id} — Validated`,
                        subtitle: `Root cause: ${i.actual_failure_type}`,
                        priority: i.priority || 'MEDIUM',
                        phase: 'ACT',
                        type: 'INTERVENTION',
                        date: i.date_intervention,
                        effectiveness: {
                            downtimeReduction: i.retrained ? '✓ Retrained' : 'Pending',
                            costSavings: '—',
                            recurrenceRate: '—',
                        },
                        implementationStatus: i.retrained ? 'RETRAINED' : 'PENDING',
                        statut: i.statut,
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

    // ── Helpers ──
    const userRole = (user?.role ?? '').toUpperCase();
    const isCheftech = userRole === 'CHEFTECH';
    const isAdmin    = userRole === 'ADMIN';
    const isTech     = userRole === 'TECHNICIEN';

    // Map WO lifecycle: DRAFT → SUBMITTED → APPROVED → ASSIGNED → IN_PROGRESS → COMPLETED → VALIDATED → CLOSED
    const nextWOStatus = (current: string): string | null => {
        const map: Record<string, string> = {
            DRAFT: 'SUBMITTED',
            SUBMITTED: 'APPROVED',
            APPROVED: 'ASSIGNED',
            ASSIGNED: 'IN_PROGRESS',
            IN_PROGRESS: 'COMPLETED',
            COMPLETED: 'VALIDATED',
        };
        return map[current] || null;
    };

    // ── PLAN actions ──
    const handlePlanAction = async (item: KanbanItem) => {
        // Predictions: open WO creation form (re-use multi-section technician form)
        if (item.type === 'PREDICTION') {
            if (!isCheftech && !isAdmin) {
                toast({
                    title: 'Action restricted',
                    description: 'Only CHEFTECH or ADMIN can create a work order from an AI prediction.',
                    variant: 'destructive',
                });
                return;
            }
            setFormData({
                ...formData,
                machine_id: item.machineId,
                titre: `[AI] ${item.title}`,
                description: `Preventive maintenance suggested by AI (Risk score: ${item.riskScore}%).`,
                priorite: item.priority === 'CRITICAL' ? 'URGENTE'
                    : item.priority === 'HIGH' ? 'ÉLEVÉE'
                    : 'MOYENNE',
                date_echeance: toDateInputValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()),
            });
            setDialogOpen(true);
            return;
        }

        // Work orders: advance through lifecycle
        if (item.type === 'WORK_ORDER') {
            const id = item.id.toString().replace('wo-', '');
            const next = nextWOStatus(item.statut || 'DRAFT');
            if (!next) {
                toast({ title: 'No transition available', variant: 'destructive' });
                return;
            }
            // Role checks for each transition
            if (item.statut === 'DRAFT' && !isCheftech && !isAdmin) {
                toast({ title: 'Only CHEFTECH/ADMIN can submit drafts', variant: 'destructive' });
                return;
            }
            if (item.statut === 'SUBMITTED' && !isCheftech) {
                toast({ title: 'Only CHEFTECH can approve work orders', variant: 'destructive' });
                return;
            }
            setActionLoading(item.id.toString());
            try {
                await client.entities.ordres_travail.update({ id, data: { statut: next } });
                toast({
                    title: 'Work order advanced',
                    description: `Status: ${item.statut} → ${next}`,
                });
                fetchData();
            } catch (error: any) {
                toast({
                    title: 'Action failed',
                    description: error?.message || 'Could not advance work order.',
                    variant: 'destructive',
                });
            } finally {
                setActionLoading(null);
            }
        }
    };

    // ── DO actions ──
    const handleDoAction = async (item: KanbanItem, action: 'BLOCK' | 'FINISH') => {
        if (!isTech && !isCheftech && !isAdmin) {
            toast({
                title: 'Action restricted',
                description: 'Only the assigned technician can update work in progress.',
                variant: 'destructive',
            });
            return;
        }
        setActionLoading(item.id.toString());
        try {
            const id = item.id.toString().replace('wo-active-', '');
            if (action === 'BLOCK') {
                // No BLOCKED status in OrdreStatut — use REJECTED with a tag, or
                // route to the dedicated blocking modal in the technician page.
                navigate(`/work-orders/${id}?action=block`);
                toast({
                    title: 'Block flow opened',
                    description: 'Use the technician interface to log the blocking reason.',
                });
            } else {
                // Tech completes WO — moves to COMPLETED (→ CHECK column)
                await client.entities.ordres_travail.update({
                    id,
                    data: { statut: 'COMPLETED', date_fin: new Date().toISOString() },
                });
                toast({
                    title: 'Work order completed',
                    description: 'Now awaiting CHEFTECH validation in the CHECK column.',
                });
                fetchData();
            }
        } catch (error: any) {
            toast({
                title: 'Action failed',
                description: error?.message || 'Could not update work order.',
                variant: 'destructive',
            });
        } finally {
            setActionLoading(null);
        }
    };

    // ── CHECK actions ──
    // Uses POST /api/v1/entities/ordres_intervention/{id}/validate (CHEFTECH only)
    const handleCheckAction = async (item: KanbanItem, action: 'DIAG' | 'VALIDATE') => {
        // DIAG: navigate to intervention detail to fill root cause
        if (action === 'DIAG') {
            const id = item.id.toString().replace('int-check-', '').replace('wo-check-', '');
            if (item.type === 'INTERVENTION') {
                navigate(`/interventions/${id}`);
            } else {
                navigate(`/work-orders/${id}`);
            }
            toast({
                title: 'Opening detail view',
                description: 'Fill in the root-cause diagnosis before validating.',
            });
            return;
        }

        // VALIDATE: CHEFTECH-only validation
        if (!isCheftech) {
            toast({
                title: 'Validation restricted',
                description: 'Only CHEFTECH can validate. Ask your supervisor.',
                variant: 'destructive',
            });
            return;
        }

        // Block validation if diagnosis missing on an intervention
        if (item.type === 'INTERVENTION' && !item.hasDiagnostic) {
            toast({
                title: 'Diagnosis required',
                description: 'Add the root-cause diagnosis before validating.',
                variant: 'destructive',
            });
            return;
        }

        setActionLoading(item.id.toString());
        try {
            if (item.type === 'INTERVENTION') {
                const id = item.id.toString().replace('int-check-', '');
                await client.apiCall.invoke({
                    url: `/api/v1/entities/ordres_intervention/${id}/validate`,
                    method: 'POST',
                    data: { action: 'APPROVE' },
                });
                toast({
                    title: 'Intervention validated',
                    description: 'Moved to ACT — ready for standardization & retrain.',
                });
            } else {
                // Work order completion → VALIDATED
                const id = item.id.toString().replace('wo-check-', '');
                await client.entities.ordres_travail.update({
                    id,
                    data: { statut: 'VALIDATED', date_validation: new Date().toISOString() },
                });
                toast({
                    title: 'Work order validated',
                    description: 'Work order closed and validated.',
                });
            }
            fetchData();
        } catch (error: any) {
            toast({
                title: 'Validation failed',
                description: error?.response?.data?.detail || error?.message || 'Check permissions and required fields.',
                variant: 'destructive',
            });
        } finally {
            setActionLoading(null);
        }
    };

    // ── ACT actions ──
    const handleActAction = async (item: KanbanItem, action: 'STD' | 'RETRAIN') => {
        // STD: navigate to intervention detail to update standard procedure
        if (action === 'STD') {
            const id = item.id.toString().replace('int-act-', '');
            navigate(`/interventions/${id}`);
            toast({
                title: 'Opening intervention',
                description: 'Update the standard maintenance procedure based on this validated root cause.',
            });
            return;
        }

        // RETRAIN: trigger ML pipeline (ADMIN/CHEFTECH only)
        if (!isAdmin && !isCheftech) {
            toast({
                title: 'Retrain restricted',
                description: 'Only ADMIN or CHEFTECH can trigger model retraining.',
                variant: 'destructive',
            });
            return;
        }

        setActionLoading('retrain');
        try {
            await client.apiCall.invoke({
                url: '/api/v1/ml/retrain',
                method: 'POST',
            });
            toast({
                title: 'AI retraining started',
                description: 'Model is being updated with the latest validated feedback.',
            });
            fetchData();
        } catch (error: any) {
            toast({
                title: 'Retrain failed',
                description: error?.response?.data?.detail || error?.message || 'Could not start retraining.',
                variant: 'destructive',
            });
        } finally {
            setActionLoading(null);
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
        {
            id: 'PLAN',
            label: 'PLAN',
            description: 'AI alerts + work orders being prepared',
            icon: <Search className="w-5 h-5 text-blue-400" />,
            color: 'bg-slate-900/60',
            border: 'border-blue-800/50',
        },
        {
            id: 'DO',
            label: 'DO',
            description: 'Work orders being executed by technicians',
            icon: <PlayCircle className="w-5 h-5 text-orange-400" />,
            color: 'bg-slate-900/60',
            border: 'border-orange-800/50',
        },
        {
            id: 'CHECK',
            label: 'CHECK',
            description: 'Completed work awaiting CHEFTECH validation',
            icon: <ClipboardList className="w-5 h-5 text-green-400" />,
            color: 'bg-slate-900/60',
            border: 'border-green-800/50',
        },
        {
            id: 'ACT',
            label: 'ACT',
            description: 'Validated work → standardize + retrain AI',
            icon: <CheckCircle2 className="w-5 h-5 text-indigo-400" />,
            color: 'bg-slate-900/60',
            border: 'border-indigo-800/50',
        },
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
                <p className="text-sm text-blue-300 font-medium">Loading PDCA workflow…</p>
            </div>
        );
    }

    return (
        <div className="w-full space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white">PDCA Workflow Board</h2>
                    <p className="text-sm text-blue-300">
                        AI predictions → planned work → execution → validation → improvement
                    </p>
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
                            All
                        </Button>
                        <Button
                            variant={filterType === 'HIGH_PRIORITY' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setFilterType('HIGH_PRIORITY')}
                            className={`h-8 text-xs ${filterType === 'HIGH_PRIORITY' ? 'bg-orange-600 text-white' : 'text-orange-400 hover:text-orange-300 hover:bg-orange-900/30'}`}
                        >
                            High Priority
                        </Button>
                        <Button
                            variant={filterType === 'BLOCKED' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setFilterType('BLOCKED')}
                            className={`h-8 text-xs ${filterType === 'BLOCKED' ? 'bg-red-600 text-white' : 'text-red-400 hover:text-red-300 hover:bg-red-900/30'}`}
                        >
                            Blocked Only
                        </Button>
                    </div>
                </div>

                <Button variant="outline" size="sm" onClick={fetchData} className="gap-2 h-9">
                    <RefreshCcw className="w-4 h-4" /> Refresh
                </Button>
            </div>

            {/* PDCA Flow Legend — helps non-technical users */}
            <div className="bg-slate-900/60 border border-blue-800/30 rounded-lg p-3 text-xs">
                <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-bold text-blue-300">How it flows:</span>
                    <span className="text-blue-200">
                        <span className="text-blue-400 font-bold">PLAN</span> AI predicts failure → CHEFTECH creates work order
                    </span>
                    <span className="text-slate-500">→</span>
                    <span className="text-blue-200">
                        <span className="text-orange-400 font-bold">DO</span> Technician executes & completes
                    </span>
                    <span className="text-slate-500">→</span>
                    <span className="text-blue-200">
                        <span className="text-green-400 font-bold">CHECK</span> CHEFTECH validates root cause
                    </span>
                    <span className="text-slate-500">→</span>
                    <span className="text-blue-200">
                        <span className="text-indigo-400 font-bold">ACT</span> Standardize fix + retrain AI
                    </span>
                </div>
                {user?.role && (
                    <p className="text-[10px] text-slate-400 mt-2">
                        Logged in as <strong className="text-blue-300">{user.role}</strong> — actions you can perform are highlighted; restricted actions will show an explanation.
                    </p>
                )}
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