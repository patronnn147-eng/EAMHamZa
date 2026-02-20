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
import { Paperclip, Loader2 } from 'lucide-react';
import type { Machine } from '@/lib/types';

const getAuthToken = () => localStorage.getItem('access_token');

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

  const [machines, setMachines] = React.useState<Machine[]>([]);
  const [uploadingField, setUploadingField] = React.useState<'required_materials' | 'problem_description' | null>(null);

  const fetchMachines = async () => {
    try {
      const token = getAuthToken();
      if (!token) return;
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/machines?limit=1000`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMachines(data.items || []);
      }
    } catch (e) {
      console.error('Error fetching machines:', e);
    }
  };

  React.useEffect(() => {
    if (open) {
      fetchMachines();
    }
  }, [open]);

  const handleFileUpload = async (field: 'required_materials' | 'problem_description') => {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      setUploadingField(field);
      try {
        const token = getAuthToken();
        if (!token) return;

        // 1. Get upload URL
        const fileName = `${Date.now()}_${file.name}`;
        const uploadRes = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/storage/upload-url`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            bucket_name: 'interventions',
            object_key: fileName
          })
        });

        if (!uploadRes.ok) throw new Error('Failed to get upload URL');
        const { upload_url } = await uploadRes.json();

        // 2. Upload to MinIO
        const putRes = await fetch(upload_url, {
          method: 'PUT',
          body: file
        });

        if (!putRes.ok) throw new Error('Upload failed');

        // 3. Create Archive entry in database
        await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/archives`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            identifiant_archive: `ARC-${Date.now()}`,
            nom: file.name,
            date_archivage: new Date().toISOString(),
            type: file.type || 'application/octet-stream',
            object_key: fileName,
            ordre_travail_id: form.ordre_travail_id
          })
        });

        // 4. Append to field with object key for retrieval
        const fileMarker = `\n[FILE:${fileName}|${file.name}]`;
        setForm(prev => ({
          ...prev,
          [field]: prev[field] ? `${prev[field]}${fileMarker}` : fileMarker
        }));

      } catch (err) {
        console.error('Upload error:', err);
      } finally {
        setUploadingField(null);
      }
    };
    input.click();
  };

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
            <Select
              value={form.machine_id?.toString() || 'none'}
              onValueChange={(v) => setForm(prev => ({ ...prev, machine_id: v === 'none' ? null : Number(v) }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner une machine" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucune</SelectItem>
                {machines.map(m => (
                  <SelectItem key={m.id} value={m.id.toString()}>
                    {m.nom} (#{m.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
            <div className="flex items-center justify-between">
              <Label>Matériels requis</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={() => handleFileUpload('required_materials')}
                disabled={uploadingField === 'required_materials'}
              >
                {uploadingField === 'required_materials' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Paperclip className="h-4 w-4 mr-1" />
                )}
                Joindre un fichier
              </Button>
            </div>
            <Textarea
              value={form.required_materials}
              onChange={(e) => setForm((prev) => ({ ...prev, required_materials: e.target.value }))}
              rows={3}
              placeholder="Liste des pièces/outils nécessaires"
            />
          </div>

          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label>Description du problème</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={() => handleFileUpload('problem_description')}
                disabled={uploadingField === 'problem_description'}
              >
                {uploadingField === 'problem_description' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Paperclip className="h-4 w-4 mr-1" />
                )}
                Joindre un fichier
              </Button>
            </div>
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
