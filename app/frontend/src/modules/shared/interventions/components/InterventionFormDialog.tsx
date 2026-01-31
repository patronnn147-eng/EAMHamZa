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
import { Textarea } from '@/components/ui/textarea';
import type { Intervention, OrdreTravail } from '@/lib/types';

interface InterventionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingIntervention: Intervention | null;
  workOrders: OrdreTravail[];
  formData: {
    date_intervention: string;
    rapport: string;
    ordre_travail_id: string;
  };
  setFormData: (data: {
    date_intervention: string;
    rapport: string;
    ordre_travail_id: string;
  }) => void;
  onSubmit: () => void;
}

export const InterventionFormDialog: React.FC<InterventionFormDialogProps> = ({
  open,
  onOpenChange,
  editingIntervention,
  workOrders,
  formData,
  setFormData,
  onSubmit,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editingIntervention ? 'Edit Intervention' : 'Record Intervention'}</DialogTitle>
          <DialogDescription>
            {editingIntervention
              ? 'Update intervention details'
              : 'Document a new maintenance intervention'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="ordre_travail_id">Work Order *</Label>
            <Select
              value={formData.ordre_travail_id}
              onValueChange={(value) => setFormData({ ...formData, ordre_travail_id: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a work order" />
              </SelectTrigger>
              <SelectContent>
                {workOrders.map((wo) => (
                  <SelectItem key={wo.id} value={wo.id.toString()}>
                    Work Order #{wo.id} - {wo.statut}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="date_intervention">Intervention Date *</Label>
            <Input
              id="date_intervention"
              type="date"
              value={formData.date_intervention}
              onChange={(e) => setFormData({ ...formData, date_intervention: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="rapport">Report *</Label>
            <Textarea
              id="rapport"
              value={formData.rapport}
              onChange={(e) => setFormData({ ...formData, rapport: e.target.value })}
              placeholder="Describe the intervention performed, issues found, and actions taken..."
              rows={8}
              className="resize-none"
            />
            <p className="text-xs text-gray-500">{formData.rapport.length} characters</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit}>{editingIntervention ? 'Update' : 'Record'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
