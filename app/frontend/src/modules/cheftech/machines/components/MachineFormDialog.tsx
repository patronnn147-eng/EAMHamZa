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

const ZONE_OPTIONS = ['ZONE CMS1 - COMPONENT SURFACE MOUNTING', 'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)'];
const SOUS_ZONE_OPTIONS_BY_ZONE: Record<string, string[]> = {
  'ZONE CMS1 - COMPONENT SURFACE MOUNTING': [
    'CMS LINE 1 (e.g., BBS - Broadband Products)',
    'CMS LINE 2 (e.g., AVS - Audio Video Products)',
  ],
  'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)': [
    'TEST IN-SITU (Test des Composants)',
    'TEST FONCTIONNEL (Test de Fonctionnement)',
    'TEST WiFi (Test Sans Fil)',
  ],
};

interface MachineFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingMachine: Machine | null;
  formData: {
    nom: string;
    identifiant_machine: string;
    type: string;
    emplacement: string;
    zone: string;
    sous_zone: string;
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
    zone: string;
    sous_zone: string;
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
            <Label htmlFor="nom">Machine Name</Label>
            <Input
              id="nom"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              placeholder="Enter machine name"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="identifiant_machine">Machine ID</Label>
            <Input
              id="identifiant_machine"
              value={formData.identifiant_machine}
              onChange={(e) => setFormData({ ...formData, identifiant_machine: e.target.value })}
              placeholder="Enter machine identifier"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="type">Type</Label>
            <Input
              id="type"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              placeholder="Enter machine type"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="emplacement">Location</Label>
            <Input
              id="emplacement"
              value={formData.emplacement}
              onChange={(e) => setFormData({ ...formData, emplacement: e.target.value })}
              placeholder="Enter location"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="zone">Zone</Label>
            <Select
              value={formData.zone}
              onValueChange={(value) => setFormData({ ...formData, zone: value, sous_zone: '' })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a zone" />
              </SelectTrigger>
              <SelectContent>
                {ZONE_OPTIONS.map((z) => (
                  <SelectItem key={z} value={z}>
                    {z}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="sous_zone">Sub-Zone / Line / Test Step</Label>
            <Select
              value={formData.sous_zone}
              onValueChange={(value) => setFormData({ ...formData, sous_zone: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a sub-zone" />
              </SelectTrigger>
              <SelectContent>
                {(
                  (formData.zone &&
                  SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone]
                    ? SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone]
                    : Object.values(SOUS_ZONE_OPTIONS_BY_ZONE).flat()) ||
                  []
                ).map((sz) => (
                  <SelectItem key={sz} value={sz}>
                    {sz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="statut">Status</Label>
            <Select value={formData.statut} onValueChange={(value) => setFormData({ ...formData, statut: value })}>
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
              placeholder="Enter image URL (optional)"
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
