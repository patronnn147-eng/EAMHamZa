import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Upload, X, CheckSquare, AlertTriangle, Boxes, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { Checkbox } from "@/components/ui/checkbox";
import { useInterventionPartsByWO } from '@/hooks/useInventory';
import { PartsConsumedSelector, ConsumedRow, buildInitialConsumedRows, serializeConsumedRows } from '@/components/inventory/PartsConsumedSelector';
import { DirectConsumeSelector, DirectConsumeRow, PendingDraftRow, directHasErrors, serializeDirect, serializePendingDirect } from '@/components/inventory/DirectConsumeSelector';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAuth } from '@/contexts/AuthContext';
import { MachineMetricsForm, TelemetryFormData } from '@/components/technicien/MachineMetricsForm';

interface CompleteWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workOrderId: number;
  machineId?: number | null;
  onSuccess: () => void;
}

const STEPS = [
  { id: 1, label: 'Rapport' },
  { id: 2, label: 'Diagnostic' },
  { id: 3, label: 'Pièces & Outils' },
  { id: 4, label: 'Télémétrie' },
  { id: 5, label: 'Preuves' },
];

function StepIndicator({ current }: Readonly<{ current: number }>) {
  return (
    <div className="flex items-center w-full mb-2">
      {STEPS.map((s, i) => {
        let circleClass: string;
        if (current > s.id) {
          circleClass = 'bg-green-600 border-green-600 text-white';
        } else if (current === s.id) {
          circleClass = 'bg-blue-600 border-blue-600 text-white';
        } else {
          circleClass = 'bg-transparent border-slate-600 text-slate-400';
        }

        let connectorClass = 'bg-slate-700';
        if (current > s.id + 1) {
          connectorClass = 'bg-green-600';
        } else if (current > s.id) {
          connectorClass = 'bg-blue-600';
        }

        return (
          <React.Fragment key={s.id}>
            <div className="flex flex-col items-center gap-1 shrink-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors ${circleClass}`}>
                {current > s.id ? <Check className="h-3.5 w-3.5" /> : s.id}
              </div>
              <span className={`text-[10px] whitespace-nowrap ${current === s.id ? 'text-blue-400 font-medium' : 'text-slate-500'}`}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-1 mb-4 transition-colors ${connectorClass}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export function CompleteWorkOrderModal({ open, onOpenChange, workOrderId, machineId, onSuccess }: Readonly<CompleteWorkOrderModalProps>) {
  const { user } = useAuth();
  const { toast } = useToast();
  const apiBase = import.meta.env.VITE_API_BASE_URL || '';

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    rapport: '',
    intervention_type: 'CURATIVE',
    root_cause_category: 'MECANIQUE',
    root_cause_description: '',
    actions_performed: '',
    parts_replaced: '',
    tools_used: '',
    machine_status_after: 'EN_MARCHE',
  });

  const [attachments, setAttachments] = useState<File[]>([]);
  const [consumedRows, setConsumedRows] = useState<ConsumedRow[]>([]);
  const [directRows, setDirectRows] = useState<DirectConsumeRow[]>([]);
  const [pendingRows, setPendingRows] = useState<PendingDraftRow[]>([]);
  const [telemetryData, setTelemetryData] = useState<TelemetryFormData>({});

  const { data: partsDetail } = useInterventionPartsByWO(open ? workOrderId : null);
  React.useEffect(() => {
    if (partsDetail?.required) {
      setConsumedRows(buildInitialConsumedRows(partsDetail.required));
    } else {
      setConsumedRows([]);
    }
  }, [partsDetail]);

  React.useEffect(() => {
    if (!open) {
      setStep(1);
      setFormData({
        rapport: '',
        intervention_type: 'CURATIVE',
        root_cause_category: 'MECANIQUE',
        root_cause_description: '',
        actions_performed: '',
        parts_replaced: '',
        tools_used: '',
        machine_status_after: 'EN_MARCHE',
      });
      setAttachments([]);
      setSymptoms([]);
      setTelemetryData({});
      setDirectRows([]);
      setPendingRows([]);
    }
  }, [open]);

  const canProceed = () => {
    if (step === 1) return formData.rapport.trim().length > 0;
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments((prev) => [...prev, ...Array.from(e.target.files)]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!formData.rapport.trim()) {
      toast({ title: 'Erreur', description: "Veuillez saisir un rapport d'intervention.", variant: 'destructive' });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) throw new Error('Non authentifié');

      const storedUser = localStorage.getItem('user');
      const userData = storedUser ? JSON.parse(storedUser) : null;
      const userRole = userData?.role || user?.role || '';

      let endpoint = 'chetop';
      if (userRole.toUpperCase() === 'TECHNICIEN' || userRole.toLowerCase() === 'technicien') {
        endpoint = 'technicien';
      }

      const res = await fetch(`${apiBase}/api/v1/${endpoint}/work-orders/${workOrderId}/complete`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          symptoms: symptoms.length > 0 ? symptoms.join(', ') : undefined,
          parts_consumed: consumedRows.length > 0 ? serializeConsumedRows(consumedRows) : undefined,
          parts_consumed_direct: directRows.length > 0 ? serializeDirect(directRows) : undefined,
          pending_pieces_direct: pendingRows.length > 0 ? serializePendingDirect(pendingRows) : undefined,
          air_temperature: telemetryData.air_temperature,
          process_temperature: telemetryData.process_temperature,
          rotational_speed: telemetryData.rotational_speed,
          torque: telemetryData.torque,
          tool_wear: telemetryData.tool_wear,
          telemetry_notes: telemetryData.notes,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erreur lors de la clôture');
      }

      for (const file of attachments) {
        const objectKey = `${workOrderId}/completion_${Date.now()}_${file.name}`;
        try {
          const uploadUrlResp = await client.apiCall.invoke({
            url: '/api/v1/storage/upload-url',
            method: 'POST',
            data: { bucket_name: 'attachments', object_key: objectKey },
          });
          const uploadUrl = (uploadUrlResp as { data?: { upload_url?: string } }).data?.upload_url;
          if (uploadUrl) {
            const putRes = await fetch(uploadUrl, { method: 'PUT', body: file });
            if (putRes.ok) {
              await client.entities.archives.create({
                data: {
                  identifiant_archive: `ARCH-C-${Date.now()}`,
                  nom: file.name,
                  date_archivage: new Date().toISOString(),
                  type: file.type.startsWith('video/') ? 'VIDEO' : 'DOCUMENT',
                  object_key: objectKey,
                  ordre_travail_id: workOrderId,
                  created_at: new Date().toISOString(),
                },
              });
            }
          }
        } catch (uploadErr) {
          console.error('File upload failed', uploadErr);
        }
      }

      toast({ title: 'Succès', description: "L'ordre de travail a été clôturé avec succès." });
      onSuccess();
      onOpenChange(false);
    } catch (error: unknown) {
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Erreur inconnue',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-emerald-600" />
            Clôture de l'Intervention
          </DialogTitle>
          <DialogDescription>
            Remplissez les informations techniques pour valider l'ordre de travail.
          </DialogDescription>
        </DialogHeader>

        <StepIndicator current={step} />

        <ScrollArea className="pr-4 max-h-[55vh]">
          <div className="space-y-5 py-2">

            {/* Step 1 — Rapport & Contexte */}
            {step === 1 && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="rapport" className="font-semibold text-red-400 flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4" />
                    Rapport d'intervention * (obligatoire)
                  </Label>
                  <Textarea
                    id="rapport"
                    placeholder="Décrivez les actions réalisées étape par étape..."
                    className="min-h-[120px]"
                    value={formData.rapport}
                    onChange={(e) => setFormData({ ...formData, rapport: e.target.value })}
                    autoFocus
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="itv_type">Type d'intervention</Label>
                    <Select
                      value={formData.intervention_type}
                      onValueChange={(val) => setFormData({ ...formData, intervention_type: val })}
                    >
                      <SelectTrigger id="itv_type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CURATIVE">Curative (Dépannage)</SelectItem>
                        <SelectItem value="PREVENTIVE">Préventive (Systématique)</SelectItem>
                        <SelectItem value="PREDICTIVE">Prédictive (Basée état)</SelectItem>
                        <SelectItem value="AMELIORATIVE">Améliorative (Modif)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="m_status">État machine final</Label>
                    <Select
                      value={formData.machine_status_after}
                      onValueChange={(val) => setFormData({ ...formData, machine_status_after: val })}
                    >
                      <SelectTrigger id="m_status"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="EN_MARCHE">En marche (Fonctionnel)</SelectItem>
                        <SelectItem value="ARRETEE">Arrêtée (En attente/HS)</SelectItem>
                        <SelectItem value="FONCTIONNEMENT_RESTREINT">Fonctionnement restreint</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            {/* Step 2 — Diagnostic */}
            {step === 2 && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rc_cat">Catégorie Cause Racine</Label>
                    <Select
                      value={formData.root_cause_category}
                      onValueChange={(val) => setFormData({ ...formData, root_cause_category: val })}
                    >
                      <SelectTrigger id="rc_cat"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MECANIQUE">Mécanique</SelectItem>
                        <SelectItem value="ELECTRIQUE">Électrique</SelectItem>
                        <SelectItem value="AUTOMATISME">Automatisme / Soft</SelectItem>
                        <SelectItem value="HUMAIN">Erreur Humaine</SelectItem>
                        <SelectItem value="AUTRE">Autre</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Symptômes observés</Label>
                  <div className="grid grid-cols-2 gap-2 p-3 rounded-lg border border-slate-700 bg-slate-800/50">
                    {['Bruit anormal', 'Vibrations', 'Surchauffe', 'Fuite', 'Panne électrique', 'Baisse de performance'].map((s) => (
                      <div key={s} className="flex items-center space-x-2">
                        <Checkbox
                          id={`sym-modal-${s}`}
                          checked={symptoms.includes(s)}
                          onCheckedChange={(checked) => {
                            if (checked) setSymptoms(prev => [...prev, s]);
                            else setSymptoms(prev => prev.filter(x => x !== s));
                          }}
                        />
                        <label htmlFor={`sym-modal-${s}`} className="text-xs font-medium cursor-pointer">{s}</label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="rc_desc">Description de la Cause Racine</Label>
                  <Textarea
                    id="rc_desc"
                    placeholder="Pourquoi la panne est arrivée ?"
                    className="min-h-[80px]"
                    value={formData.root_cause_description}
                    onChange={(e) => setFormData({ ...formData, root_cause_description: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Actions effectuées</Label>
                  <Textarea
                    placeholder="- Action 1&#10;- Action 2&#10;- Action 3"
                    className="min-h-[80px]"
                    value={formData.actions_performed}
                    onChange={(e) => setFormData({ ...formData, actions_performed: e.target.value })}
                  />
                </div>
              </>
            )}

            {/* Step 3 — Pièces & Outils */}
            {step === 3 && (
              <>
                {partsDetail && partsDetail.required.length > 0 && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Boxes className="h-4 w-4 text-emerald-400" />
                      Consommation des pièces réservées
                    </Label>
                    <PartsConsumedSelector
                      required={partsDetail.required}
                      rows={consumedRows}
                      onChange={setConsumedRows}
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Boxes className="h-4 w-4 text-blue-400" />
                    Pièces remplacées (depuis l'inventaire)
                  </Label>
                  <DirectConsumeSelector
                    machineId={machineId ?? null}
                    consumedRows={directRows}
                    pendingRows={pendingRows}
                    onConsumedChange={setDirectRows}
                    onPendingChange={setPendingRows}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="parts">Pièces remplacées (notes libres)</Label>
                    <Textarea
                      id="parts"
                      placeholder="Optionnel — notes complémentaires"
                      className="min-h-[60px]"
                      value={formData.parts_replaced}
                      onChange={(e) => setFormData({ ...formData, parts_replaced: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tools">Outils utilisés</Label>
                    <Textarea
                      id="tools"
                      placeholder="ex: Clé dynamométrique, Multimètre..."
                      className="min-h-[60px]"
                      value={formData.tools_used}
                      onChange={(e) => setFormData({ ...formData, tools_used: e.target.value })}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Step 4 — Télémétrie */}
            {step === 4 && (
              <MachineMetricsForm formData={telemetryData} onChange={setTelemetryData} />
            )}

            {/* Step 5 — Preuves jointes */}
            {step === 5 && (
              <div className="space-y-4 pb-4">
                <Label className="font-semibold text-blue-100">Pièces jointes (Preuves visuelles)</Label>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => document.getElementById('file-upload-modal')?.click()}
                  className="w-full h-24 border-dashed bg-slate-800/50 hover:bg-blue-800/40 flex flex-col items-center justify-center gap-2"
                >
                  <Upload className="h-6 w-6 text-blue-400" />
                  <span className="text-sm text-blue-300">Ajouter des photos / vidéos</span>
                </Button>
                <Input
                  id="file-upload-modal"
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  className="hidden"
                  onChange={handleFileChange}
                />

                {attachments.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-auto pr-2">
                    {attachments.map((file, idx) => (
                      <div key={`${file.name}-${file.size}-${file.lastModified}`} className="flex items-center justify-between p-2 text-sm border rounded bg-slate-800 shadow-sm">
                        <span className="truncate flex-1 max-w-[280px]">{file.name}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeAttachment(idx)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {attachments.length === 0 && (
                  <p className="text-xs text-slate-500 text-center">Aucune pièce jointe — étape optionnelle.</p>
                )}
              </div>
            )}

          </div>
        </ScrollArea>

        <DialogFooter className="mt-4 border-t pt-4 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => step === 1 ? onOpenChange(false) : setStep(s => s - 1)}
            disabled={loading}
          >
            {step === 1 ? 'Annuler' : <><ChevronLeft className="h-4 w-4 mr-1" />Précédent</>}
          </Button>

          <span className="text-xs text-slate-500">{step} / {STEPS.length}</span>

          {step < STEPS.length ? (
            <Button onClick={() => setStep(s => s + 1)} disabled={!canProceed()}>
              Suivant <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={loading || !formData.rapport.trim() || directHasErrors(directRows)}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {loading ? 'Enregistrement...' : 'Valider et Clôturer'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
