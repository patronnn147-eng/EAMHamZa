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

export type InterventionRequestFormData = {
  ordre_travail_id: number;
  machine_id: number | null;
  problem_description: string;
  priority: string;
  estimated_duration_minutes: string;
  required_materials: string;
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialOrdreTravailId: number;
  initialMachineId?: number | null;
  onSubmit: (data: {
    ordre_travail_id: number;
    machine_id: number | null;
    problem_description: string;
    priority: string;
    estimated_duration_minutes: number | null;
    required_materials: string | null;
  }) => void;
};

export const InterventionRequestDialog: React.FC<Props> = ({
  open,
  onOpenChange,
  initialOrdreTravailId,
  initialMachineId = null,
  onSubmit,
}) => {
  const [form, setForm] = React.useState<InterventionRequestFormData>({
    ordre_travail_id: initialOrdreTravailId,
    machine_id: initialMachineId,
    problem_description: '',
    priority: 'MOYENNE',
    estimated_duration_minutes: '',
    required_materials: '',
  });

  React.useEffect(() => {
    if (!open) return;
    setForm({
      ordre_travail_id: initialOrdreTravailId,
      machine_id: initialMachineId,
      problem_description: '',
      priority: 'MOYENNE',
      estimated_duration_minutes: '',
      required_materials: '',
    });
  }, [open, initialOrdreTravailId, initialMachineId]);

  const canSubmit =
    form.problem_description.trim().length > 0 && form.priority.trim().length > 0 && Number.isFinite(form.ordre_travail_id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Demande de démarrage d'intervention</DialogTitle>
          <DialogDescription>
            Remplis le formulaire. Le ChefTech doit approuver avant que tu puisses démarrer.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label>Ordre de travail</Label>
            <Input value={`#${form.ordre_travail_id}`} disabled />
          </div>

          <div className="grid gap-2">
            <Label>Machine concernée (optionnel)</Label>
            <Input
              type="number"
              value={form.machine_id ?? ''}
              onChange={(e) => {
                const v = e.target.value;
                setForm((prev) => ({ ...prev, machine_id: v ? Number.parseInt(v) : null }));
              }}
              placeholder="ID machine"
            />
          </div>

          <div className="grid gap-2">
            <Label>Priorité</Label>
            <Select
              value={form.priority}
              onValueChange={(value) => setForm((prev) => ({ ...prev, priority: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BASSE">Basse</SelectItem>
                <SelectItem value="MOYENNE">Moyenne</SelectItem>
                <SelectItem value="ELEVEE">Élevée</SelectItem>
                <SelectItem value="URGENTE">Urgente</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label>Durée estimée (minutes)</Label>
            <Input
              type="number"
              value={form.estimated_duration_minutes}
              onChange={(e) => setForm((prev) => ({ ...prev, estimated_duration_minutes: e.target.value }))}
              placeholder="ex: 90"
            />
          </div>

          <div className="grid gap-2">
            <Label>Matériels requis</Label>
            <Textarea
              value={form.required_materials}
              onChange={(e) => setForm((prev) => ({ ...prev, required_materials: e.target.value }))}
              rows={3}
              placeholder="Liste des pièces/outils nécessaires"
            />
          </div>

          <div className="grid gap-2">
            <Label>Description du problème</Label>
            <Textarea
              value={form.problem_description}
              onChange={(e) => setForm((prev) => ({ ...prev, problem_description: e.target.value }))}
              rows={5}
              placeholder="Décris le problème et le contexte"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button
            onClick={() => {
              const est = form.estimated_duration_minutes.trim();
              onSubmit({
                ordre_travail_id: form.ordre_travail_id,
                machine_id: form.machine_id,
                problem_description: form.problem_description.trim(),
                priority: form.priority,
                estimated_duration_minutes: est ? Number.parseInt(est) : null,
                required_materials: form.required_materials.trim() ? form.required_materials.trim() : null,
              });
            }}
            disabled={!canSubmit}
          >
            Envoyer pour approbation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
