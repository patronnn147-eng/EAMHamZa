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
    actual_failure_type: string;
    ml_prediction_matched: string;
  };
  setFormData: (data: {
    date_intervention: string;
    rapport: string;
    ordre_travail_id: string;
    actual_failure_type: string;
    ml_prediction_matched: string;
  }) => void;
  onSubmit: () => void;
}

const FAILURE_TYPES = [
  { value: 'NONE', label: 'Aucune panne détectée' },
  { value: 'TWF', label: 'TWF — Tool Wear Failure (Usure outil)' },
  { value: 'HDF', label: 'HDF — Heat Dissipation Failure (Dissipation thermique)' },
  { value: 'PWF', label: 'PWF — Power Failure (Défaillance électrique)' },
  { value: 'OSF', label: 'OSF — Overstrain Failure (Surcharge)' },
  { value: 'RNF', label: 'RNF — Random Failure (Panne aléatoire)' },
];

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
              rows={6}
              className="resize-none"
            />
            <p className="text-xs text-gray-500">{formData.rapport.length} characters</p>
          </div>

          {/* PDCA Feedback Section */}
          <div className="border-t pt-4 mt-2">
            <p className="text-sm font-semibold text-blue-700 mb-3 flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
              Validation ML (PDCA)
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="actual_failure_type">Type de panne réel</Label>
                <Select
                  value={formData.actual_failure_type}
                  onValueChange={(value) => setFormData({ ...formData, actual_failure_type: value })}
                >
                  <SelectTrigger id="actual_failure_type">
                    <SelectValue placeholder="Sélectionner le type de panne" />
                  </SelectTrigger>
                  <SelectContent>
                    {FAILURE_TYPES.map((ft) => (
                      <SelectItem key={ft.value} value={ft.value}>
                        {ft.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-400">Quel type de panne avez-vous constaté ?</p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="ml_prediction_matched">Prédiction ML correcte ?</Label>
                <Select
                  value={formData.ml_prediction_matched}
                  onValueChange={(value) => setFormData({ ...formData, ml_prediction_matched: value })}
                >
                  <SelectTrigger id="ml_prediction_matched">
                    <SelectValue placeholder="La prédiction était-elle correcte ?" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">✅ Oui — La prédiction ML était correcte</SelectItem>
                    <SelectItem value="false">❌ Non — La prédiction ML était incorrecte</SelectItem>
                    <SelectItem value="unknown">❓ Pas de prédiction ML disponible</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-400">La prédiction du modèle correspondait-elle à la réalité ?</p>
              </div>
            </div>
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
