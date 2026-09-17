import React, { useEffect, useState } from 'react';
import { Columns, Filter, RefreshCcw as RefreshIcon } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { DoColumn } from '@/modules/shared/machines/components/PDCA/DoColumn';
import { KanbanItem } from '@/modules/shared/machines/components/PDCA/types';
import { WorkOrderCompleteDialog, WorkOrderCompletePayload } from '@/modules/technicien/components/WorkOrderCompleteDialog';
import type { WorkOrderTechnicien } from '@/lib/types';

const apiBase = import.meta.env.VITE_API_BASE_URL || '';

const PENDING_START_STATUSES = new Set(['EN_ATTENTE', 'ASSIGNÉ', 'ASSIGNED']);
const IN_PROGRESS_STATUSES = new Set(['EN_COURS', 'IN_PROGRESS']);

function getPriorityColor(priority: string): string {
    switch (priority) {
        case 'URGENTE': return 'bg-red-600/20 text-red-300 border border-red-500/30';
        case 'ÉLEVÉE': return 'bg-orange-600/20 text-orange-300 border border-orange-500/30';
        case 'MOYENNE': return 'bg-yellow-600/20 text-yellow-300 border border-yellow-500/30';
        default: return 'bg-slate-600/20 text-slate-300 border border-slate-500/30';
    }
}

function toKanbanItem(wo: WorkOrderTechnicien): KanbanItem {
    const isPending = PENDING_START_STATUSES.has(wo.statut);
    return {
        id: `wo-active-${wo.id}`,
        machineId: wo.machine_id,
        machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
        title: wo.titre,
        subtitle: isPending ? 'Assignée — à démarrer' : 'En cours',
        priority: wo.priorite,
        phase: 'DO',
        type: 'WORK_ORDER',
        date: wo.created_at,
        progress: isPending ? 10 : 50,
        statut: isPending ? 'ASSIGNED' : 'IN_PROGRESS',
    };
}

export default function TechnicianPDCA() {
    const { toast } = useToast();
    const [items, setItems] = useState<KanbanItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [completingWoId, setCompletingWoId] = useState<number | null>(null);
    const [completeModalOpen, setCompleteModalOpen] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${apiBase}/api/v1/technicien/work-orders`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const all: WorkOrderTechnicien[] = Array.isArray(data) ? data : (data.items || []);
            const mine = all.filter(
                (wo) => PENDING_START_STATUSES.has(wo.statut) || IN_PROGRESS_STATUSES.has(wo.statut)
            );
            setItems(mine.map(toKanbanItem));
        } catch (error) {
            console.error('Error fetching technician PDCA board:', error);
            toast({
                title: 'Erreur',
                description: 'Impossible de charger vos ordres de travail.',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleAction = async (item: KanbanItem, action: 'START' | 'FINISH') => {
        const id = Number(item.id.toString().replace('wo-active-', ''));
        if (action === 'START') {
            setActionLoading(item.id.toString());
            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch(`${apiBase}/api/v1/technicien/work-orders/${id}/start`, {
                    method: 'PATCH',
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (response.ok) {
                    toast({ title: 'Succès', description: "L'intervention a commencé" });
                    fetchData();
                } else {
                    const err = await response.json().catch(() => ({}));
                    toast({ title: 'Erreur', description: err.detail || 'Impossible de démarrer', variant: 'destructive' });
                }
            } catch {
                toast({ title: 'Erreur réseau', description: 'Veuillez réessayer', variant: 'destructive' });
            } finally {
                setActionLoading(null);
            }
            return;
        }
        // FINISH — open the real PDCA completion form (rapport, cause, pièces, télémétrie)
        setCompletingWoId(id);
        setCompleteModalOpen(true);
    };

    const completingItem = items.find((i) => i.id === `wo-active-${completingWoId}`);

    return (
        <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Columns className="h-5 w-5 text-orange-400" />
                        Mon Suivi PDCA
                    </h1>
                    <p className="text-sm text-blue-300 mt-1">
                        Vos ordres de travail en cours — la partie "DO" du cycle PDCA.
                    </p>
                </div>
                <button
                    onClick={fetchData}
                    disabled={loading}
                    className="inline-flex items-center gap-2 text-xs font-medium text-blue-200 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 hover:bg-slate-700/60 disabled:opacity-50"
                >
                    <RefreshIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Actualiser
                </button>
            </div>

            <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-4 py-3 text-xs text-blue-300 flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 shrink-0" />
                <span>
                    <span className="text-slate-500">PLAN</span> (Chef Tech planifie) →
                    <span className="text-orange-300 font-semibold"> DO</span> (vous exécutez) →
                    <span className="text-slate-500"> CHECK</span> (Chef Tech valide) →
                    <span className="text-slate-500"> ACT</span> (standardisation)
                </span>
            </div>

            {loading ? (
                <div className="h-32 rounded-lg bg-slate-800 animate-pulse" />
            ) : (
                <div className="max-w-2xl">
                    <DoColumn
                        items={items}
                        actionLoading={actionLoading}
                        onAction={handleAction}
                        getPriorityColor={getPriorityColor}
                    />
                </div>
            )}

            {completingWoId && (
                <WorkOrderCompleteDialog
                    open={completeModalOpen}
                    onOpenChange={setCompleteModalOpen}
                    workOrderId={completingWoId}
                    workOrderTitle={completingItem?.title || ''}
                    machineName={completingItem?.machineName}
                    machineId={completingItem?.machineId ?? null}
                    onConfirm={async (data: WorkOrderCompletePayload) => {
                        try {
                            const token = localStorage.getItem('access_token');
                            const response = await fetch(`${apiBase}/api/v1/technicien/work-orders/${completingWoId}/complete`, {
                                method: 'PATCH',
                                headers: {
                                    Authorization: `Bearer ${token}`,
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(data),
                            });
                            if (response.ok) {
                                toast({ title: 'Succès', description: 'Ordre de travail terminé avec succès!' });
                                setCompleteModalOpen(false);
                                setCompletingWoId(null);
                                fetchData();
                            } else {
                                const err = await response.json().catch(() => ({}));
                                toast({ title: 'Erreur', description: err.detail || 'Impossible de terminer', variant: 'destructive' });
                            }
                        } catch {
                            toast({ title: 'Erreur réseau', description: 'Veuillez réessayer', variant: 'destructive' });
                        }
                    }}
                />
            )}
        </div>
    );
}
