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
import { PiecePicker, PlannedRow, PendingDraft, hasValidationErrors } from '@/components/inventory/PiecePicker';
import { SectionDivider } from '@/components/inventory/primitives';

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
  onSubmit: (
    data: {
      ordre_travail_id: number;
      machine_id: number | null;
      problem_description: string;
      priority: string;
      estimated_duration_minutes: number | null;
      required_materials: string | null;
    },
    extras?: {
      required_pieces: PlannedRow[];
      pending_pieces: PendingDraft[];
    }
  ) => void;
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
  const [plannedPieces, setPlannedPieces] = React.useState<PlannedRow[]>([]);
  const [pendingDrafts, setPendingDrafts] = React.useState<PendingDraft[]>([]);
  const [uploadingField, setUploadingField] = React.useState<'required_materials' | 'problem_description' | null>(null);

  const fetchMachines = async () => {
    try {
      setMachines([]); // Clear previous state to avoid showing stale data
      const token = getAuthToken();
      if (!token) {
        console.error('❌ No auth token found');
        return;
      }

      console.log('🔍 Fetching work order for restriction:', initialOrdreTravailId);

      // 1. Fetch the Work Order to get its machine_id
      const woRes = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_travail/${initialOrdreTravailId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!woRes.ok) {
        console.error('❌ Failed to fetch work order:', woRes.status);
        return;
      }

      const woResponseData = await woRes.json();
      console.log('📦 Work order raw response:', woResponseData);

      // Robust unwrap
      const woData = woResponseData.data || woResponseData;
      const targetMachineId = woData.machine_id;

      console.log('🎯 Target machine ID:', targetMachineId);

      if (!targetMachineId) {
        console.warn('⚠️ No machine_id found on work order');
        setMachines([]);
        return;
      }

      // 2. Fetch only that specific machine
      const mRes = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/machines/${targetMachineId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (mRes.ok) {
        const mResponseData = await mRes.json();
        console.log('📦 Machine raw response:', mResponseData);

        const mData = mResponseData.data || mResponseData;

        if (mData?.id) {
          console.log('✅ Setting restricted machine:', mData.nom);
          setMachines([mData]);
          setForm(prev => ({ ...prev, machine_id: mData.id }));
        } else {
          console.error('❌ Machine data format invalid');
        }
      } else {
        console.error('❌ Failed to fetch specific machine:', mRes.status);
      }
    } catch (e) {
      console.error('🚨 Error fetching restricted machines:', e);
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
    form.problem_description.trim().length > 0 &&
    form.priority.trim().length > 0 &&
    Number.isFinite(form.ordre_travail_id) &&
    !hasValidationErrors(plannedPieces);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
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
            <SectionDivider label="Pièces requises" tone="success" />
            <PiecePicker
              machineId={form.machine_id}
              selectedRows={plannedPieces}
              pendingDrafts={pendingDrafts}
              onSelectedChange={setPlannedPieces}
              onPendingChange={setPendingDrafts}
            />
          </div>

          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label className="text-blue-300 text-xs">Notes libres sur le matériel (optionnel)</Label>
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
                Joindre
              </Button>
            </div>
            <Textarea
              value={form.required_materials}
              onChange={(e) => setForm((prev) => ({ ...prev, required_materials: e.target.value }))}
              rows={2}
              placeholder="Notes complémentaires hors catalogue (outils, autorisations…)"
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
              }, {
                required_pieces: plannedPieces,
                pending_pieces: pendingDrafts,
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
