import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Paperclip, Loader2, AlertCircle, Zap, Activity, History, Brain, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Machine {
  id: number;
  nom: string;
}

interface MachineMLHealth {
  predicted_priority: string;
  health_score: number;
  failure_probability: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  rul_days: number;
  suggested_cause?: string;
}

const ML_PRIORITY_MAP: Record<string, string> = {
  Critical: 'URGENTE',
  High: 'ÉLEVÉE',
  Medium: 'MOYENNE',
  Low: 'BASSE',
};

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  initialOrdreTravailId?: number | null;
  initialMachineId?: number | null;
  initialPlanningTacheId?: number | null;
}

const STEPS = [
  { id: 1, label: 'Machine' },
  { id: 2, label: 'Problème' },
  { id: 3, label: 'Contexte' },
];

function StepIndicator({ current }: Readonly<{ current: number }>) {
  return (
    <div className="flex items-center w-full mb-2 px-6">
      {STEPS.map((s, i) => {
        let circleClass: string;
        if (current > s.id) {
          circleClass = 'bg-green-600 border-green-600 text-white';
        } else if (current === s.id) {
          circleClass = 'bg-violet-600 border-violet-600 text-white';
        } else {
          circleClass = 'bg-transparent border-slate-600 text-slate-400';
        }

        let connectorClass = 'bg-slate-700';
        if (current > s.id + 1) {
          connectorClass = 'bg-green-600';
        } else if (current > s.id) {
          connectorClass = 'bg-violet-600';
        }

        return (
          <React.Fragment key={s.id}>
            <div className="flex flex-col items-center gap-1 shrink-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors ${circleClass}`}>
                {current > s.id ? <Check className="h-3.5 w-3.5" /> : s.id}
              </div>
              <span className={`text-[10px] whitespace-nowrap ${current === s.id ? 'text-violet-400 font-medium' : 'text-slate-500'}`}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 mb-4 transition-colors ${connectorClass}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export const TechnicianNewInterventionModal: React.FC<Props> = ({
  open,
  onOpenChange,
  onSuccess,
  initialMachineId = null,
  initialPlanningTacheId = null,
}) => {
  const { toast } = useToast();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loadingMachines, setLoadingMachines] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingField, setUploadingField] = useState<'description' | 'required_materials' | null>(null);
  const [machineHealth, setMachineHealth] = useState<MachineMLHealth | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [priorityAISuggested, setPriorityAISuggested] = useState(false);
  const [step, setStep] = useState(1);

  const [formData, setFormData] = useState({
    machine_id: '',
    description: '',
    priority: 'MOYENNE',
    estimated_duration_minutes: '',
    required_materials: '',
    machine_category: 'Non-critique',
    symptoms: [] as string[],
    problem_start_time: '',
    frequency: 'Première fois',
    operating_state: 'En marche',
    temperature: '',
    impact: 'Aucun impact pour le moment',
    estimated_loss: '',
    similar_issue_before: false,
  });

  const fetchMachines = async () => {
    setLoadingMachines(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/technicien/machines`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMachines(data);
      }
    } catch (error) {
      console.error('Error fetching machines:', error);
    } finally {
      setLoadingMachines(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchMachines();
      setMachineHealth(null);
      setPriorityAISuggested(false);
      setStep(1);
      setFormData({
        machine_id: initialMachineId != null ? initialMachineId.toString() : '',
        description: '',
        priority: 'MOYENNE',
        estimated_duration_minutes: '',
        required_materials: '',
        machine_category: 'Non-critique',
        symptoms: [],
        problem_start_time: '',
        frequency: 'Première fois',
        operating_state: 'En marche',
        temperature: '',
        impact: 'Aucun impact pour le moment',
        estimated_loss: '',
        similar_issue_before: false,
      });
    }
  }, [open]);

  const fetchMachineHealth = async (machineId: string) => {
    if (!machineId) { setMachineHealth(null); setPriorityAISuggested(false); return; }
    setLoadingHealth(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const res = await fetch(`${apiBase}/api/v1/ml/machines/${machineId}/prediction`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: MachineMLHealth = await res.json();
        setMachineHealth(data);
        const mapped = ML_PRIORITY_MAP[data.predicted_priority];
        if (mapped) {
          setFormData(prev => ({ ...prev, priority: mapped }));
          setPriorityAISuggested(true);
        }
      } else {
        setMachineHealth(null);
        setPriorityAISuggested(false);
      }
    } catch {
      setMachineHealth(null);
      setPriorityAISuggested(false);
    } finally {
      setLoadingHealth(false);
    }
  };

  const handleFileUpload = async (field: 'description' | 'required_materials') => {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setUploadingField(field);
      try {
        const token = localStorage.getItem('access_token');
        const apiBase = import.meta.env.VITE_API_BASE_URL || '';
        const fileName = `${Date.now()}_${file.name}`;
        const uploadRes = await fetch(`${apiBase}/api/v1/storage/upload-url`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ bucket_name: 'interventions', object_key: fileName })
        });
        if (!uploadRes.ok) throw new Error('Failed to get upload URL');
        const { upload_url } = await uploadRes.json();
        await fetch(upload_url, { method: 'PUT', body: file });
        const fileMarker = `\n[FILE:${fileName}|${file.name}]`;
        setFormData(prev => ({ ...prev, [field]: prev[field] ? `${prev[field]}${fileMarker}` : fileMarker }));
        toast({ title: 'Fichier joint', description: file.name });
      } catch (err) {
        console.error('Upload error:', err);
        toast({ title: 'Erreur upload', variant: 'destructive' });
      } finally {
        setUploadingField(null);
      }
    };
    input.click();
  };

  const canProceed = () => {
    if (step === 1) return !!formData.machine_id;
    if (step === 2) return !!formData.description.trim();
    return true;
  };

  const handleSubmit = async () => {
    if (!formData.machine_id || !formData.description) {
      toast({ title: 'Erreur', description: 'Veuillez remplir les champs obligatoires (Machine et Description)', variant: 'destructive' });
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const payload = {
        machine_id: parseInt(formData.machine_id),
        ...(initialPlanningTacheId != null && { planning_tache_id: initialPlanningTacheId }),
        problem_description: formData.description,
        priority: formData.priority,
        estimated_duration_minutes: formData.estimated_duration_minutes ? parseInt(formData.estimated_duration_minutes) : null,
        required_materials: formData.required_materials || null,
        machine_category: formData.machine_category,
        symptoms: formData.symptoms.join(', '),
        problem_start_time: formData.problem_start_time ? new Date(formData.problem_start_time).toISOString() : null,
        frequency: formData.frequency,
        operating_state: formData.operating_state,
        temperature: formData.temperature || null,
        impact: formData.impact,
        estimated_loss: formData.estimated_loss,
        similar_issue_before: formData.similar_issue_before,
      };
      const response = await fetch(`${apiBase}/api/v1/technicien/interventions/request`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        onSuccess();
        onOpenChange(false);
        toast({ title: 'Succès', description: 'Demande créée avec succès' });
      } else {
        const error = await response.json();
        toast({ title: 'Erreur', description: error.detail || 'Échec de la demande', variant: 'destructive' });
      }
    } catch (error) {
      console.error('Error submitting request:', error);
      toast({ title: 'Erreur', description: 'Une erreur est survenue', variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] bg-slate-800 dark:bg-slate-900 border-none shadow-2xl rounded-3xl overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-2">
          <DialogTitle className="text-2xl font-black tracking-tight flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-primary" />
            Nouvelle Demande d'Intervention (DI)
          </DialogTitle>
          <DialogDescription className="text-blue-300 font-medium">
            Standard Officiel - Technicien
          </DialogDescription>
        </DialogHeader>

        <StepIndicator current={step} />

        <ScrollArea className="px-6 max-h-[55vh]">
          <div className="space-y-5 py-2">

            {/* Step 1 — Machine */}
            {step === 1 && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Machine *</Label>
                    <Select
                      value={formData.machine_id}
                      onValueChange={(v) => { setFormData({ ...formData, machine_id: v }); fetchMachineHealth(v); }}
                      disabled={loadingMachines}
                    >
                      <SelectTrigger className="rounded-xl border-blue-700/50 py-6">
                        <SelectValue placeholder={loadingMachines ? "Chargement..." : "Choisir une machine"} />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-blue-700/50">
                        {machines.map(m => (
                          <SelectItem key={m.id} value={m.id.toString()} className="rounded-lg mb-1">{m.nom}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Catégorie Machine</Label>
                    <Select onValueChange={(val) => setFormData({ ...formData, machine_category: val })} value={formData.machine_category}>
                      <SelectTrigger className="rounded-xl border-blue-700/50 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-blue-700/50">
                        <SelectItem value="Critique" className="rounded-lg">Critique</SelectItem>
                        <SelectItem value="Non-critique" className="rounded-lg">Non-critique</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {loadingHealth && (
                  <div className="flex items-center gap-2 text-xs text-violet-400 pl-1">
                    <Loader2 className="w-3 h-3 animate-spin" /> Analyse IA en cours...
                  </div>
                )}
                {!loadingHealth && machineHealth && (() => {
                  let healthScoreClass: string;
                  if (machineHealth.health_score >= 70) {
                    healthScoreClass = 'text-emerald-400';
                  } else if (machineHealth.health_score >= 40) {
                    healthScoreClass = 'text-orange-400';
                  } else {
                    healthScoreClass = 'text-red-400';
                  }

                  let riskLevelClass: string;
                  if (machineHealth.risk_level === 'CRITICAL') {
                    riskLevelClass = 'text-red-400';
                  } else if (machineHealth.risk_level === 'HIGH') {
                    riskLevelClass = 'text-orange-400';
                  } else if (machineHealth.risk_level === 'MEDIUM') {
                    riskLevelClass = 'text-yellow-400';
                  } else {
                    riskLevelClass = 'text-emerald-400';
                  }

                  return (
                  <div className="rounded-xl border border-violet-700/40 bg-violet-950/30 px-4 py-3 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-violet-300 uppercase tracking-wide">
                      <Brain className="w-3.5 h-3.5" /> Santé IA — Machine sélectionnée
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                      <span>Score santé:{' '}
                        <span className={`font-bold ${healthScoreClass}`}>
                          {machineHealth.health_score.toFixed(0)}%
                        </span>
                      </span>
                      <span>Prob. panne:{' '}
                        <span className="font-bold text-orange-300">{machineHealth.failure_probability.toFixed(0)}%</span>
                      </span>
                      <span>Risque:{' '}
                        <span className={`font-bold ${riskLevelClass}`}>
                          {machineHealth.risk_level}
                        </span>
                      </span>
                      <span>RUL: <span className="font-bold text-blue-300">{machineHealth.rul_days}j</span></span>
                    </div>
                    <div className="text-xs font-semibold text-violet-300">
                      Priorité IA suggérée: <span className="text-violet-100">{ML_PRIORITY_MAP[machineHealth.predicted_priority] ?? machineHealth.predicted_priority}</span>
                    </div>
                    {machineHealth.suggested_cause && (
                      <div className="text-xs italic text-slate-400">Cause probable: {machineHealth.suggested_cause}</div>
                    )}
                  </div>
                  );
                })()}
              </>
            )}

            {/* Step 2 — Problème */}
            {step === 2 && (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between ml-1">
                    <Label className="font-bold text-sm">Description détaillée *</Label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFileUpload('description')}
                      disabled={!!uploadingField}
                      className="text-violet-600 hover:text-violet-700 font-bold gap-1"
                    >
                      {uploadingField === 'description' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
                      Joindre
                    </Button>
                  </div>
                  <Textarea
                    placeholder="Expliquez ce qu'il se passe..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="rounded-2xl border-blue-700/50 min-h-[80px]"
                    autoFocus
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Début de l'incident</Label>
                    <Input
                      type="datetime-local"
                      value={formData.problem_start_time}
                      onChange={(e) => setFormData({ ...formData, problem_start_time: e.target.value })}
                      className="rounded-xl border-blue-700/50 py-6"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Fréquence du problème</Label>
                    <Select onValueChange={(val) => setFormData({ ...formData, frequency: val })} value={formData.frequency}>
                      <SelectTrigger className="rounded-xl border-blue-700/50 py-6"><SelectValue /></SelectTrigger>
                      <SelectContent className="rounded-xl border-blue-700/50">
                        <SelectItem value="Première fois">Première fois</SelectItem>
                        <SelectItem value="Occasionnel">Occasionnel</SelectItem>
                        <SelectItem value="Récurrent">Récurrent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            {/* Step 3 — Contexte */}
            {step === 3 && (
              <>
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Activity className="h-3.5 w-3.5" /> État de la Machine
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="font-bold text-sm ml-1">État opérationnel</Label>
                      <Select onValueChange={(val) => setFormData({ ...formData, operating_state: val })} value={formData.operating_state}>
                        <SelectTrigger className="rounded-xl border-blue-700/50 py-6"><SelectValue /></SelectTrigger>
                        <SelectContent className="rounded-xl border-blue-700/50">
                          <SelectItem value="En marche">En marche</SelectItem>
                          <SelectItem value="Au repos (Idle)">Au repos (Idle)</SelectItem>
                          <SelectItem value="Démarrage">Démarrage</SelectItem>
                          <SelectItem value="Arrêt">Arrêt</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="font-bold text-sm ml-1">Température (si connue)</Label>
                      <Input
                        placeholder="ex: 45°C"
                        value={formData.temperature}
                        onChange={(e) => setFormData({ ...formData, temperature: e.target.value })}
                        className="rounded-xl border-blue-700/50 py-6"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Estimation de l'arrêt (Downtime) en minutes</Label>
                    <Input
                      type="number"
                      placeholder="ex: 60"
                      value={formData.estimated_duration_minutes}
                      onChange={(e) => setFormData(prev => ({ ...prev, estimated_duration_minutes: e.target.value }))}
                      className="rounded-xl border-blue-700/50 py-6"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <AlertCircle className="h-3.5 w-3.5 text-orange-500" /> Priorité & Impact
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 ml-1">
                        <Label className="font-bold text-sm">Priorité d'intervention</Label>
                        {priorityAISuggested && <span className="text-xs text-violet-400 font-medium">(suggérée par IA)</span>}
                      </div>
                      <Select onValueChange={(val) => { setFormData({ ...formData, priority: val }); setPriorityAISuggested(false); }} value={formData.priority}>
                        <SelectTrigger className="rounded-xl border-blue-700/50 py-6"><SelectValue /></SelectTrigger>
                        <SelectContent className="rounded-xl border-blue-700/50">
                          <SelectItem value="BASSE">BASSE</SelectItem>
                          <SelectItem value="MOYENNE">MOYENNE</SelectItem>
                          <SelectItem value="ÉLEVÉE">ÉLEVÉE</SelectItem>
                          <SelectItem value="URGENTE" className="text-red-600 font-bold">URGENTE</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="font-bold text-sm ml-1">Impact sur la production</Label>
                      <Select onValueChange={(val) => setFormData({ ...formData, impact: val })} value={formData.impact}>
                        <SelectTrigger className="rounded-xl border-blue-700/50 py-6"><SelectValue /></SelectTrigger>
                        <SelectContent className="rounded-xl border-blue-700/50">
                          <SelectItem value="Arrêt de production">Arrêt de production</SelectItem>
                          <SelectItem value="Performance réduite">Performance réduite</SelectItem>
                          <SelectItem value="Aucun impact pour le moment">Aucun impact pour le moment</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <History className="h-3.5 w-3.5" /> Historique
                  </h4>
                  <div className="flex items-center space-x-2 bg-blue-50/10 p-4 rounded-2xl border border-blue-800/50">
                    <Checkbox
                      id="similar"
                      checked={formData.similar_issue_before}
                      onCheckedChange={(checked) => setFormData({ ...formData, similar_issue_before: !!checked })}
                    />
                    <label htmlFor="similar" className="text-sm font-bold leading-none cursor-pointer text-blue-300">
                      Problème déjà rencontré auparavant ?
                    </label>
                  </div>
                </div>

                <div className="p-4 bg-emerald-950/40 border border-emerald-800/50 rounded-2xl space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                    <Zap className="h-4 w-4" /> IA - Aide au diagnostic automatique
                  </div>
                  <p className="text-xs text-emerald-500 italic">
                    L'IA analysera vos symptômes après la soumission pour suggérer une cause racine à l'équipe maintenance.
                  </p>
                </div>
              </>
            )}

          </div>
        </ScrollArea>

        <DialogFooter className="px-6 py-4 bg-slate-800/50 mt-auto border-t flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={() => step === 1 ? onOpenChange(false) : setStep(s => s - 1)}
            className="rounded-xl font-bold px-6"
          >
            {step === 1 ? 'Annuler' : <><ChevronLeft className="h-4 w-4 mr-1" />Précédent</>}
          </Button>

          <span className="text-xs text-slate-500">{step} / {STEPS.length}</span>

          {step < STEPS.length ? (
            <Button
              onClick={() => setStep(s => s + 1)}
              disabled={!canProceed()}
              className="rounded-xl font-bold px-6"
            >
              Suivant <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={submitting || !formData.machine_id || !formData.description}
              className="bg-gradient-premium hover:opacity-90 rounded-xl font-bold px-8 shadow-lg shadow-violet-500/25 min-w-[160px]"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Envoyer la Demande
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
