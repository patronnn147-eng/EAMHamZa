import React from 'react';
import { Button } from '@/components/ui/button';
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
import type { Machine, OrdreTravail } from '@/lib/types';

interface WorkOrderFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingWorkOrder: OrdreTravail | null;
  machines: Machine[];
  formData: {
    machine_id: string;
    utilisateur_id: string;
    date_echeance: string;
    priorite: string;
    statut: string;
  };
  setFormData: (data: {
    machine_id: string;
    utilisateur_id: string;
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
  formData,
  setFormData,
  onSubmit,
}) => {
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
            <Label htmlFor="machine_id">Machine</Label>
            <Select
              value={formData.machine_id}
              onValueChange={(value) => setFormData({ ...formData, machine_id: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a machine" />
              </SelectTrigger>
              <SelectContent>
                {machines.map((machine) => (
                  <SelectItem key={machine.id} value={machine.id.toString()}>
                    {machine.nom} ({machine.identifiant_machine})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
                <SelectItem value="EN_COURS">In Progress</SelectItem>
                <SelectItem value="TERMINE">Completed</SelectItem>
                <SelectItem value="ANNULE">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="utilisateur_id">Assign To User ID (Optional)</Label>
            <Input
              id="utilisateur_id"
              type="number"
              value={formData.utilisateur_id}
              onChange={(e) => setFormData({ ...formData, utilisateur_id: e.target.value })}
              placeholder="Enter user ID"
            />
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
