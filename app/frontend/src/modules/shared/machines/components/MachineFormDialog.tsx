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
import type { Machine } from '@/lib/types';

interface MachineFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingMachine: Machine | null;
  formData: {
    nom: string;
    identifiant_machine: string;
    type: string;
    emplacement: string;
    statut: string;
    date_derniere_maintenance: string;
    date_prochaine_maintenance: string;
    image_url: string;
  };
  setFormData: (data: {
    nom: string;
    identifiant_machine: string;
    type: string;
    emplacement: string;
    statut: string;
    date_derniere_maintenance: string;
    date_prochaine_maintenance: string;
    image_url: string;
  }) => void;
  onSubmit: () => void;
}

export const MachineFormDialog: React.FC<MachineFormDialogProps> = ({
  open,
  onOpenChange,
  editingMachine,
  formData,
  setFormData,
  onSubmit,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingMachine ? 'Edit Machine' : 'Add New Machine'}</DialogTitle>
          <DialogDescription>
            {editingMachine ? 'Update machine information' : 'Enter the details for the new machine'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="nom">Name</Label>
            <Input
              id="nom"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              placeholder="Machine name"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="identifiant_machine">Machine ID</Label>
            <Input
              id="identifiant_machine"
              value={formData.identifiant_machine}
              onChange={(e) => setFormData({ ...formData, identifiant_machine: e.target.value })}
              placeholder="e.g., MCH-001"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="type">Type</Label>
            <Input
              id="type"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              placeholder="Machine type"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="emplacement">Location</Label>
            <Input
              id="emplacement"
              value={formData.emplacement}
              onChange={(e) => setFormData({ ...formData, emplacement: e.target.value })}
              placeholder="Machine location"
            />
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
            <Label htmlFor="date_derniere_maintenance">Last Maintenance Date</Label>
            <Input
              id="date_derniere_maintenance"
              type="date"
              value={formData.date_derniere_maintenance}
              onChange={(e) => setFormData({ ...formData, date_derniere_maintenance: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="date_prochaine_maintenance">Next Maintenance Date</Label>
            <Input
              id="date_prochaine_maintenance"
              type="date"
              value={formData.date_prochaine_maintenance}
              onChange={(e) => setFormData({ ...formData, date_prochaine_maintenance: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="image_url">Image URL</Label>
            <Input
              id="image_url"
              value={formData.image_url}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
              placeholder="/images/ImageUpload.jpg"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit}>{editingMachine ? 'Update' : 'Create'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
