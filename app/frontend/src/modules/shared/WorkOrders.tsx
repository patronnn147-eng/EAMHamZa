import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  DeleteWorkOrderDialog,
  WorkOrderFormDialog,
  WorkOrdersFilters,
  WorkOrdersHeader,
  WorkOrdersList,
} from './work-orders/components';
import { useWorkOrders } from './work-orders/hooks';
import type { Planning, OrdreTravail } from '@/lib/types';
import { WorkOrderDetailsDialog } from './work-orders/components/WorkOrderDetailsDialog';

export default function WorkOrders() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsWorkOrder, setDetailsWorkOrder] = useState<OrdreTravail | null>(null);

  const [assignOpen, setAssignOpen] = useState(false);
  const [assignWorkOrder, setAssignWorkOrder] = useState<OrdreTravail | null>(null);
  const [assignEstimatedDate, setAssignEstimatedDate] = useState<string>('');
  const [assignSelectedMachineIds, setAssignSelectedMachineIds] = useState<number[]>([]);
  const [assignSelectedTechIds, setAssignSelectedTechIds] = useState<number[]>([]);
  const [assignLinkedTechIds, setAssignLinkedTechIds] = useState<number[]>([]);
  const [assignTechnicians, setAssignTechnicians] = useState<Array<{ id: number; nom: string }>>([]);

  const canManage = user?.role === 'ADMIN' || user?.role === 'CHETOP' || user?.role === 'CHEFOP';
  const canAssign = user?.role === 'CHEFTECH';

  const clearAttachments = () => setAttachments([]);
  const {
    machines,
    filteredWorkOrders,
    loading,
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingWorkOrder,
    deletingWorkOrder,
    setDeletingWorkOrder,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
    refresh,
  } = useWorkOrders({ attachments, clearAttachments, userRole: user?.role });

  const apiBase = import.meta.env.VITE_API_BASE_URL || '';

  const toggleAssignMachine = (id: number) => {
    setAssignSelectedMachineIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleAssignTech = (id: number) => {
    setAssignSelectedTechIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const openAssignDialog = async (wo: OrdreTravail) => {
    setAssignWorkOrder(wo);
    setAssignEstimatedDate(wo.date_echeance ? new Date(wo.date_echeance).toISOString().slice(0, 10) : '');
    setAssignSelectedMachineIds(wo.machine_id ? [wo.machine_id] : []);
    setAssignSelectedTechIds([]);
    setAssignLinkedTechIds([]);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setAssignTechnicians([]);
        return;
      }

      const techResp = await fetch(`${apiBase}/api/v1/cheftech/techniciens`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const techData = techResp.ok ? ((await techResp.json()) as Array<{ id: number; nom: string }>) : [];
      setAssignTechnicians(Array.isArray(techData) ? techData : []);

      const interResp = await fetch(
        `${apiBase}/api/v1/entities/ordres_intervention?query=${encodeURIComponent(
          JSON.stringify({ ordre_travail_id: wo.id }),
        )}&limit=2000`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      const raw = interResp.ok ? ((await interResp.json()) as unknown) : null;
      const unwrap = (value: unknown): unknown => {
        let current = value;
        for (let i = 0; i < 5; i += 1) {
          if (!current || typeof current !== 'object') return current;
          if (Array.isArray(current)) return current;
          const obj = current as Record<string, unknown>;
          if ('items' in obj && Array.isArray(obj.items)) return obj;
          if ('data' in obj) {
            current = obj.data;
            continue;
          }
          return current;
        }
        return current;
      };

      const extracted = unwrap(raw) as
        | {
            items?: Array<{ technicien_id?: number | null; ordre_travail_id?: number | null }>;
          }
        | undefined;

      const relevantItems = (extracted?.items || []).filter((i) => i.ordre_travail_id === wo.id);
      const preselected = relevantItems
        .map((i) => i.technicien_id)
        .filter((id): id is number => typeof id === 'number');
      const unique = Array.from(new Set(preselected));
      setAssignLinkedTechIds(unique);
      setAssignSelectedTechIds(unique);
    } catch {
      setAssignTechnicians([]);
      setAssignSelectedTechIds([]);
      setAssignLinkedTechIds([]);
    }

    setAssignOpen(true);
  };

  const submitAssign = async () => {
    if (!assignWorkOrder) return;
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const resp = await fetch(`${apiBase}/api/v1/cheftech/ordres-travail/${assignWorkOrder.id}/assign`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          technicien_ids: assignSelectedTechIds,
          machine_ids: assignSelectedMachineIds,
          estimated_completion_date: assignEstimatedDate ? new Date(assignEstimatedDate).toISOString() : null,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || 'Failed to assign');
      }

      toast({ title: 'Success', description: 'Work order assigned' });
      setAssignOpen(false);
      refresh();
    } catch (e) {
      toast({
        title: 'Error',
        description: e instanceof Error ? e.message : 'Failed to assign',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    const fetchPlannings = async () => {
      try {
        const resp = await client.apiCall.invoke({
          url: '/api/v1/plannings?skip=0&limit=100',
          method: 'GET',
        });

        const unwrap = (value: unknown): unknown => {
          let current = value;
          for (let i = 0; i < 5; i += 1) {
            if (!current || typeof current !== 'object') return current;
            const obj = current as Record<string, unknown>;

            if ('items' in obj && Array.isArray(obj.items)) return current;
            if ('data' in obj) {
              current = obj.data;
              continue;
            }
            return current;
          }
          return current;
        };

        const maybeWrapped = (resp as { data?: unknown } | undefined)?.data;
        const extracted = unwrap(maybeWrapped) as { items?: Planning[] } | Planning[] | undefined;
        const items = Array.isArray(extracted) ? extracted : extracted?.items || [];
        setPlannings(items);
      } catch (error) {
        console.error('Error fetching plannings:', error);
      }
    };
    fetchPlannings();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkOrdersHeader onCreate={() => handleOpenDialog()} canCreate={canManage} />

      <WorkOrdersFilters
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        priorityFilter={priorityFilter}
        setPriorityFilter={setPriorityFilter}
      />

      <WorkOrdersList
        workOrders={filteredWorkOrders}
        machines={machines}
        canEdit={canManage}
        canDelete={canManage}
        canAssign={canAssign}
        onAssign={(wo) => void openAssignDialog(wo)}
        onViewDetails={(wo) => {
          setDetailsWorkOrder(wo);
          setDetailsOpen(true);
        }}
        onEdit={handleOpenDialog}
        onRequestDelete={(wo) => {
          setDeletingWorkOrder(wo);
          setDeleteDialogOpen(true);
        }}
      />

      <WorkOrderFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingWorkOrder={editingWorkOrder}
        machines={machines}
        plannings={plannings}
        attachments={attachments}
        setAttachments={setAttachments}
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
      />

      <DeleteWorkOrderDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        deletingWorkOrder={deletingWorkOrder}
        onDelete={handleDelete}
      />

      <WorkOrderDetailsDialog
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        workOrder={detailsWorkOrder}
        machines={machines}
      />

      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Assigner l'ordre de travail</DialogTitle>
            <DialogDescription>Choisis une ou plusieurs machines et techniciens.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid gap-2">
              <Label>Date estimée de fin (optionnel)</Label>
              <Input type="date" value={assignEstimatedDate} onChange={(e) => setAssignEstimatedDate(e.target.value)} />
            </div>

            <div className="space-y-2">
              <Label>Machines</Label>
              <div className="max-h-48 overflow-auto border rounded-md p-2 space-y-2">
                {machines.map((m) => (
                  <label key={m.id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={assignSelectedMachineIds.includes(m.id)}
                      onCheckedChange={() => toggleAssignMachine(m.id)}
                    />
                    <span>
                      {m.nom} (#{m.id})
                    </span>
                  </label>
                ))}
                {machines.length === 0 && <p className="text-sm text-blue-300">Aucune machine</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Techniciens</Label>
              <div className="max-h-64 overflow-auto border rounded-md p-2 space-y-2">
                {(assignLinkedTechIds.length > 0
                  ? assignTechnicians.filter((t) => assignLinkedTechIds.includes(t.id))
                  : assignTechnicians
                ).map((t) => (
                  <label key={t.id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={assignSelectedTechIds.includes(t.id)}
                      onCheckedChange={() => toggleAssignTech(t.id)}
                    />
                    <span>{t.nom}</span>
                  </label>
                ))}
                {assignTechnicians.length === 0 && <p className="text-sm text-blue-300">Aucun technicien</p>}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignOpen(false)}>
              Annuler
            </Button>
            <Button
              onClick={submitAssign}
              disabled={!assignWorkOrder || assignSelectedTechIds.length === 0 || assignSelectedMachineIds.length === 0}
            >
              Assigner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}