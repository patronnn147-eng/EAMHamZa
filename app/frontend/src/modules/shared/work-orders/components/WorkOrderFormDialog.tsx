import React, { useEffect, useState } from 'react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import type { Machine, OrdreTravail } from '@/lib/types';
import { client } from '@/lib/api';

interface PlanningUser {
  id: number;
  nom: string;
  email: string;
  role: string;
}

interface PlanningOption {
  id: number;
  identifiant_planning: string;
  chef_technique_id?: number | null;
  assigned_users?: PlanningUser[];
  machine_ids?: number[];
}

interface WorkOrderFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingWorkOrder: OrdreTravail | null;
  machines: Machine[];
  plannings: PlanningOption[];
  attachments: File[];
  setAttachments: (files: File[]) => void;
  formData: {
    titre: string;
    description: string;
    machine_ids: number[];
    planning_id: number | null;
    chef_technique_id: number | null;
    technicien_ids: number[];
    date_echeance: string;
    priorite: string;
    statut: string;
  };
  setFormData: (data: {
    titre: string;
    description: string;
    machine_ids: number[];
    planning_id: number | null;
    chef_technique_id: number | null;
    technicien_ids: number[];
    date_echeance: string;
    priorite: string;
    statut: string;
  }) => void;
  onSubmit: () => void;
}

export const WorkOrderFormDialog: React.FC<WorkOrderFormDialogProps> = ({
  open,
  onOpenChange,
  editingWorkOrder,
  machines,
  plannings,
  attachments,
  setAttachments,
  formData,
  setFormData,
  onSubmit,
}) => {
  const selectedPlanning = formData.planning_id
    ? plannings.find((p) => p.id === formData.planning_id)
    : null;

  const planningTechnicians = (selectedPlanning?.assigned_users || []).filter((u) => u.role === 'TECHNICIEN');
  const planningChefTechs = (selectedPlanning?.assigned_users || []).filter((u) => u.role === 'CHEFTECH');
  const [planningMachines, setPlanningMachines] = useState<Machine[]>([]);
  const availableMachines = selectedPlanning ? planningMachines : [];

  let machinesEmptyMessage: string | null = null;
  if (!selectedPlanning) {
    machinesEmptyMessage = 'Select a planning to see its machines';
  } else if (availableMachines.length === 0) {
    machinesEmptyMessage = 'No machines in this planning';
  }

  useEffect(() => {
    const fetchPlanningMachines = async () => {
      if (!selectedPlanning) {
        setPlanningMachines([]);
        return;
      }

      try {
        const resp = await client.apiCall.invoke({
          url: `/api/v1/plannings/${selectedPlanning.id}/machines`,
          method: 'GET',
        });

        const unwrap = (value: unknown): unknown => {
          let current = value;
          for (let i = 0; i < 5; i += 1) {
            if (!current || typeof current !== 'object') return current;
            const obj = current as Record<string, unknown>;
            if (Array.isArray(current)) return current;
            if ('data' in obj) {
              current = obj.data;
              continue;
            }
            return current;
          }
          return current;
        };

        const maybeWrapped = (resp as { data?: unknown } | undefined)?.data;
        const extracted = unwrap(maybeWrapped);
        const items = Array.isArray(extracted) ? (extracted as Machine[]) : [];
        setPlanningMachines(items);
      } catch (e) {
        setPlanningMachines([]);
      }
    };

    fetchPlanningMachines();
  }, [selectedPlanning?.id]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editingWorkOrder ? 'Edit Work Order' : 'Create Work Order'}</DialogTitle>
          <DialogDescription>
            {editingWorkOrder
              ? 'Update work order information'
              : 'Enter the details for the new work order'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="titre">Title</Label>
            <Input
              id="titre"
              value={formData.titre}
              onChange={(e) => setFormData({ ...formData, titre: e.target.value })}
              placeholder="Work order title"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe the work to be done"
              rows={4}
            />
          </div>
          <div className="grid gap-2">
            <Label>Machines</Label>
            <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
              {machinesEmptyMessage ? (
                <p className="text-sm text-gray-500">{machinesEmptyMessage}</p>
              ) : (
                availableMachines.map((m) => (
                  <div key={m.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                    <Checkbox
                      id={`machine-${m.id}`}
                      checked={formData.machine_ids.includes(m.id)}
                      onCheckedChange={() =>
                        setFormData({
                          ...formData,
                          machine_ids: formData.machine_ids.includes(m.id)
                            ? formData.machine_ids.filter((id) => id !== m.id)
                            : [...formData.machine_ids, m.id],
                        })
                      }
                    />
                    <label htmlFor={`machine-${m.id}`} className="text-sm font-medium cursor-pointer flex-1">
                      {m.nom} (#{m.id})
                    </label>
                  </div>
                ))
              )}
            </div>
            <p className="text-xs text-gray-500">Selected: {formData.machine_ids.length} machine(s)</p>
          </div>

          <div className="grid gap-2">
            <Label>Planning</Label>
            <Select
              value={formData.planning_id?.toString() || ''}
              onValueChange={(value) => {
                const pid = value ? Number.parseInt(value) : null;
                const p = pid ? plannings.find((x) => x.id === pid) : null;

                const chefTechFromPlanning =
                  (p?.assigned_users || []).find((u) => u.role === 'CHEFTECH')?.id || p?.chef_technique_id || null;

                setFormData({
                  ...formData,
                  planning_id: pid,
                  chef_technique_id: chefTechFromPlanning,
                  technicien_ids: [],
                  machine_ids: [],
                });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a planning" />
              </SelectTrigger>
              <SelectContent>
                {plannings.map((p) => (
                  <SelectItem key={p.id} value={p.id.toString()}>
                    {p.identifiant_planning}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedPlanning && (
            <div className="grid gap-2">
              <Label>Related users (from planning)</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>ChefTech</Label>
                  <Select
                    value={formData.chef_technique_id?.toString() || ''}
                    onValueChange={(value) =>
                      setFormData({
                        ...formData,
                        chef_technique_id: value ? Number.parseInt(value) : null,
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select ChefTech" />
                    </SelectTrigger>
                    <SelectContent>
                      {planningChefTechs.length === 0 ? (
                        <SelectItem value="none" disabled>
                          No ChefTech in this planning
                        </SelectItem>
                      ) : (
                        planningChefTechs.map((u) => (
                          <SelectItem key={u.id} value={u.id.toString()}>
                            {u.nom} - {u.email}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label>Technicians</Label>
                  <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
                    {planningTechnicians.length === 0 ? (
                      <p className="text-sm text-gray-500">No technicians in this planning</p>
                    ) : (
                      planningTechnicians.map((t) => (
                        <div key={t.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                          <Checkbox
                            id={`tech-${t.id}`}
                            checked={formData.technicien_ids.includes(t.id)}
                            onCheckedChange={() =>
                              setFormData({
                                ...formData,
                                technicien_ids: formData.technicien_ids.includes(t.id)
                                  ? formData.technicien_ids.filter((id) => id !== t.id)
                                  : [...formData.technicien_ids, t.id],
                              })
                            }
                          />
                          <label htmlFor={`tech-${t.id}`} className="text-sm font-medium cursor-pointer flex-1">
                            {t.nom} - {t.email}
                          </label>
                        </div>
                      ))
                    )}
                  </div>
                  <p className="text-xs text-gray-500">Selected: {formData.technicien_ids.length} technician(s)</p>
                </div>
              </div>
            </div>
          )}

          <div className="grid gap-2">
            <Label htmlFor="date_echeance">Due Date</Label>
            <Input
              id="date_echeance"
              type="date"
              value={formData.date_echeance}
              onChange={(e) => setFormData({ ...formData, date_echeance: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="priorite">Priority</Label>
            <Select
              value={formData.priorite}
              onValueChange={(value) => setFormData({ ...formData, priorite: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BASSE">Low</SelectItem>
                <SelectItem value="MOYENNE">Medium</SelectItem>
                <SelectItem value="ELEVEE">High</SelectItem>
                <SelectItem value="URGENTE">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="statut">Status</Label>
            <Select
              value={formData.statut}
              onValueChange={(value) => setFormData({ ...formData, statut: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="EN_ATTENTE">Pending</SelectItem>
                <SelectItem value="ASSIGNÉ">Assigned</SelectItem>
                <SelectItem value="EN_COURS">In Progress</SelectItem>
                <SelectItem value="TERMINÉ">Completed</SelectItem>
                <SelectItem value="BLOQUÉ">Blocked</SelectItem>
                <SelectItem value="ANNULÉ">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>Attachments</Label>
            <Input type="file" multiple onChange={(e) => setAttachments(Array.from(e.target.files || []))} />
            <p className="text-xs text-gray-500">Selected: {attachments.length} file(s)</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit}>{editingWorkOrder ? 'Update' : 'Create'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
