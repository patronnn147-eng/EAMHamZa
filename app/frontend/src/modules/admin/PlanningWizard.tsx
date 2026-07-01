import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { toDateTimeLocalInputValue } from '@/lib/date';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { useToast } from '@/hooks/use-toast';
import type { Machine } from '@/lib/types';
import { ZONE_OPTIONS, SOUS_ZONE_OPTIONS_BY_ZONE, ORDRE_TEMPLATES } from '@/lib/constants';
import { Bell, Check, ChevronRight } from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface User {
  id: number;
  nom: string;
  email: string;
  role: string;
  shift_type?: string | null;
}

interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: string;
  shift_type?: string;
  chef_operation_id?: number;
  chef_technique_id?: number;
  zone_travail?: string;
  sous_zone?: string;
  ordre?: string;
  assigned_users: User[];
  machine_ids?: number[];
  planning_statut?: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
}

type PlanningType = 'MAINTENANCE' | 'SHIFT' | 'HEBDOMADAIRE' | 'MENSUEL' | 'JOURNALIER';
type ShiftType = 'MORNING' | 'NIGHT';

interface FormData {
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: PlanningType;
  shift_type: ShiftType | undefined;
  chef_operation_id: number | undefined;
  chef_technique_id: number | undefined;
  zone_travail: string;
  sous_zone: string;
  ordre: string;
  technicien_ids: number[];
  machine_ids: number[];
}

export interface PlanningWizardProps {
  open: boolean;
  onClose: () => void;
  planning?: Planning | null;
  onSuccess: () => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, title: 'Informations de base', description: 'Identifiant, type et dates' },
  { id: 2, title: 'Localisation', description: 'Zone et sous-zone de travail' },
  { id: 3, title: 'Machines', description: 'Sélection des machines' },
  { id: 4, title: 'Équipe', description: 'Attribution des rôles' },
  { id: 5, title: 'Récapitulatif', description: 'Vérification et création' },
];

const TYPE_DESCRIPTIONS: Record<PlanningType, string> = {
  MAINTENANCE: 'Planification pour la maintenance des équipements',
  SHIFT: 'Planification des équipes jour/nuit',
  HEBDOMADAIRE: 'Planification hebdomadaire des tâches récurrentes',
  MENSUEL: "Vue d'ensemble mensuelle",
  JOURNALIER: 'Planification opérationnelle journalière',
};

function defaultFormData(): FormData {
  const now = new Date();
  const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  return {
    identifiant_planning: `PLAN-${Date.now()}`,
    date_debut: toDateTimeLocalInputValue(now.toISOString()),
    date_fin: toDateTimeLocalInputValue(nextWeek.toISOString()),
    type: 'MAINTENANCE',
    shift_type: undefined,
    chef_operation_id: undefined,
    chef_technique_id: undefined,
    zone_travail: '',
    sous_zone: '',
    ordre: '',
    technicien_ids: [],
    machine_ids: [],
  };
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function StepSidebar({
  currentStep,
  completedSteps,
  onJump,
}: {
  currentStep: number;
  completedSteps: Set<number>;
  onJump: (step: number) => void;
}) {
  return (
    <div className="w-60 flex-shrink-0 border-r border-slate-700 bg-slate-900 flex flex-col py-8 px-4 gap-1">
      <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-4 px-2">
        Étapes
      </p>
      {STEPS.map((step) => {
        const isCompleted = completedSteps.has(step.id);
        const isCurrent = currentStep === step.id;
        const isClickable = isCompleted || step.id < currentStep;
        return (
          <button
            key={step.id}
            type="button"
            disabled={!isClickable}
            onClick={() => isClickable && onJump(step.id)}
            className={`flex items-start gap-3 rounded-lg px-3 py-3 text-left transition-colors ${
              isCurrent
                ? 'bg-blue-600/20 border border-blue-500/40'
                : isCompleted
                ? 'hover:bg-slate-800 cursor-pointer'
                : 'opacity-40 cursor-not-allowed'
            }`}
          >
            <div
              className={`mt-0.5 h-5 w-5 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold border-2 ${
                isCompleted
                  ? 'bg-green-500 border-green-500 text-white'
                  : isCurrent
                  ? 'border-blue-400 text-blue-400'
                  : 'border-slate-600 text-slate-500'
              }`}
            >
              {isCompleted ? <Check className="h-3 w-3" /> : step.id}
            </div>
            <div>
              <p
                className={`text-sm font-medium ${
                  isCurrent
                    ? 'text-white'
                    : isCompleted
                    ? 'text-slate-200'
                    : 'text-slate-500'
                }`}
              >
                {step.title}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{step.description}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PlanningWizard({
  open,
  onClose,
  planning,
  onSuccess,
}: PlanningWizardProps) {
  const { toast } = useToast();

  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [stepError, setStepError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>(defaultFormData);
  const [dataLoading, setDataLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [chefOperations, setChefOperations] = useState<User[]>([]);
  const [chefTechniques, setChefTechniques] = useState<User[]>([]);
  const [techniciens, setTechniciens] = useState<User[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);

  useEffect(() => {
    if (!open) return;
    setCurrentStep(1);
    setCompletedSteps(new Set());
    setStepError(null);
    loadData();
  }, [open]);

  const loadData = async () => {
    setDataLoading(true);
    try {
      const [chefOps, chefTechs, techs, machinesResp] = await Promise.all([
        fetchUsersByRole('CHETOP'),
        fetchUsersByRole('CHEFTECH'),
        fetchUsersByRole('TECHNICIEN'),
        client.entities.machines.query({ query: {}, sort: '-created_at', limit: 200 }),
      ]);
      setChefOperations(chefOps);
      setChefTechniques(chefTechs);
      setTechniciens(techs);
      setMachines(machinesResp.data.items || []);
    } finally {
      setDataLoading(false);
    }

    if (planning) {
      let freshPlanning = planning;
      try {
        const detailResp = await client.apiCall.invoke({
          url: `/api/v1/plannings/${planning.id}`,
          method: 'GET',
        });
        const raw = (detailResp as any)?.data ?? detailResp;
        const candidate = (raw?.identifiant_planning ? raw : raw?.data ?? raw) as Planning;
        if (candidate?.id) freshPlanning = candidate;
      } catch {
        /* fall back to list data */
      }
      setFormData({
        identifiant_planning: freshPlanning.identifiant_planning,
        date_debut: toDateTimeLocalInputValue(freshPlanning.date_debut),
        date_fin: toDateTimeLocalInputValue(freshPlanning.date_fin),
        type: freshPlanning.type as PlanningType,
        shift_type: freshPlanning.shift_type as ShiftType | undefined,
        chef_operation_id: freshPlanning.chef_operation_id,
        chef_technique_id: freshPlanning.chef_technique_id,
        zone_travail: freshPlanning.zone_travail || '',
        sous_zone: (freshPlanning as any).sous_zone || '',
        ordre: (freshPlanning as any).ordre || '',
        technicien_ids: Array.from(
          new Set(
            (freshPlanning.assigned_users || [])
              .filter((u) => u.role === 'TECHNICIEN')
              .map((u) => u.id)
          )
        ),
        machine_ids: Array.from(new Set(freshPlanning.machine_ids || [])),
      });
    } else {
      setFormData(defaultFormData());
    }
  };

  const fetchUsersByRole = async (role: string): Promise<User[]> => {
    try {
      const resp = await client.apiCall.invoke({
        url: `/api/v1/plannings/users/by-role/${role}`,
        method: 'GET',
      });
      return resp.data || [];
    } catch {
      return [];
    }
  };

  // ── Handlers ─────────────────────────────────────────────────────────────

  const filterUsersByPlanningShift = (users: User[]) => {
    if (formData.type !== 'SHIFT' || !formData.shift_type) return users;
    return users.filter((u) => (u.shift_type || 'MORNING') === formData.shift_type);
  };

  const handleTypeChange = (type: PlanningType) => {
    setFormData((prev) => ({
      ...prev,
      type,
      shift_type: type === 'SHIFT' ? 'MORNING' : undefined,
    }));
  };

  const handleShiftTypeChange = (shiftType: ShiftType) => {
    setFormData((prev) => {
      const next = { ...prev, shift_type: shiftType };
      const allowedChefOps = new Set(filterUsersByPlanningShift(chefOperations).map((u) => u.id));
      const allowedChefTechs = new Set(filterUsersByPlanningShift(chefTechniques).map((u) => u.id));
      const allowedTechs = new Set(filterUsersByPlanningShift(techniciens).map((u) => u.id));
      if (next.chef_operation_id && !allowedChefOps.has(next.chef_operation_id))
        next.chef_operation_id = undefined;
      if (next.chef_technique_id && !allowedChefTechs.has(next.chef_technique_id))
        next.chef_technique_id = undefined;
      next.technicien_ids = next.technicien_ids.filter((id) => allowedTechs.has(id));
      return next;
    });
  };

  const handleZoneChange = (zone: string) => {
    setFormData((prev) => ({ ...prev, zone_travail: zone, sous_zone: '', ordre: '', machine_ids: [] }));
  };

  const handleSubZoneChange = (sous_zone: string) => {
    setFormData((prev) => ({ ...prev, sous_zone, ordre: '', machine_ids: [] }));
  };

  const handleOrderChange = (ordre: string) => {
    setFormData((prev) => ({ ...prev, ordre, machine_ids: [] }));
  };

  const toggleMachine = (id: number) => {
    setFormData((prev) => ({
      ...prev,
      machine_ids: prev.machine_ids.includes(id)
        ? prev.machine_ids.filter((x) => x !== id)
        : [...prev.machine_ids, id],
    }));
  };

  const toggleTechnicien = (id: number) => {
    setFormData((prev) => ({
      ...prev,
      technicien_ids: prev.technicien_ids.includes(id)
        ? prev.technicien_ids.filter((x) => x !== id)
        : [...prev.technicien_ids, id],
    }));
  };

  const filteredMachines = machines.filter((m) => {
    const zoneMatch = !formData.zone_travail || m.zone === formData.zone_travail;
    const subZoneMatch =
      !formData.sous_zone || !m.sous_zone || m.sous_zone === formData.sous_zone;
    const status = (m.statut || '').toLowerCase();
    const isAvailable =
      !status ||
      ['disponible', 'available', 'operationnelle', 'en_marche'].includes(status);
    const isSelected = formData.machine_ids.includes(m.id);
    return (zoneMatch && subZoneMatch && isAvailable) || isSelected;
  });

  // ── Validation ────────────────────────────────────────────────────────────

  const validateStep = (step: number): string | null => {
    if (step === 1) {
      if (!formData.identifiant_planning.trim())
        return "L'identifiant du planning est requis.";
      if (!formData.date_debut) return 'La date de début est requise.';
      if (!formData.date_fin) return 'La date de fin est requise.';
      if (new Date(formData.date_fin) <= new Date(formData.date_debut))
        return 'La date de fin doit être postérieure à la date de début.';
      if (formData.type === 'SHIFT' && !formData.shift_type)
        return 'Le type de shift est requis pour un planning de type SHIFT.';
    }
    if (step === 4) {
      if (formData.type === 'SHIFT' && !formData.chef_operation_id)
        return "Un Chef Opération est requis pour un planning de type SHIFT.";
    }
    return null;
  };

  // ── Navigation ────────────────────────────────────────────────────────────

  const handleNext = () => {
    const err = validateStep(currentStep);
    if (err) { setStepError(err); return; }
    setStepError(null);
    setCompletedSteps((prev) => new Set([...prev, currentStep]));
    setCurrentStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setStepError(null);
    setCurrentStep((prev) => prev - 1);
  };

  const handleJumpTo = (step: number) => {
    setStepError(null);
    setCurrentStep(step);
  };

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    const err = validateStep(4);
    if (err) { setStepError(err); return; }
    setSubmitting(true);
    try {
      const payload = {
        identifiant_planning: formData.identifiant_planning,
        date_debut: new Date(formData.date_debut).toISOString(),
        date_fin: new Date(formData.date_fin).toISOString(),
        type: formData.type,
        shift_type: formData.shift_type || null,
        chef_operation_id: formData.chef_operation_id || null,
        chef_technique_id: formData.chef_technique_id || null,
        zone_travail: formData.zone_travail?.trim() || null,
        sous_zone: formData.sous_zone?.trim() || null,
        ordre: formData.ordre?.trim() || null,
        technicien_ids: Array.from(new Set(formData.technicien_ids)),
        machine_ids: Array.from(new Set(formData.machine_ids)),
      };
      if (planning) {
        await client.apiCall.invoke({
          url: `/api/v1/plannings/${planning.id}`,
          method: 'PUT',
          data: payload,
        });
        toast({ title: 'Succès', description: 'Planning mis à jour. Notifications envoyées.' });
      } else {
        await client.apiCall.invoke({
          url: '/api/v1/plannings',
          method: 'POST',
          data: payload,
        });
        toast({ title: 'Succès', description: 'Planning créé. Notifications envoyées.' });
      }
      onClose();
      onSuccess();
    } catch (error: unknown) {
      const detail =
        (error as any)?.data?.detail ||
        (error as any)?.response?.data?.detail ||
        (error as any)?.message ||
        'Échec de la sauvegarde du planning';
      setStepError(detail);
      toast({ title: 'Erreur', description: detail, variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  // ── Helpers ───────────────────────────────────────────────────────────────

  const getUserShiftBadge = (shiftType?: string | null) => {
    if (!shiftType) return null;
    const config = {
      MORNING: { label: 'Morning', className: 'bg-yellow-100 text-yellow-800' },
      NIGHT: { label: 'Night', className: 'bg-indigo-100 text-indigo-800' },
    };
    const c = config[shiftType as keyof typeof config];
    return c ? <Badge className={c.className}>{c.label}</Badge> : null;
  };

  // ── Step renderers ────────────────────────────────────────────────────────

  const renderStep1 = () => (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="identifiant_planning">Identifiant du planning *</Label>
        <Input
          id="identifiant_planning"
          value={formData.identifiant_planning}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, identifiant_planning: e.target.value }))
          }
          placeholder="ex. PLAN-2026-07"
        />
      </div>
      <div className="space-y-2">
        <Label>Type de planning *</Label>
        <Select
          value={formData.type}
          onValueChange={(v) => handleTypeChange(v as PlanningType)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
            <SelectItem value="SHIFT">Shift (Jour/Nuit)</SelectItem>
            <SelectItem value="HEBDOMADAIRE">Hebdomadaire</SelectItem>
            <SelectItem value="MENSUEL">Mensuel</SelectItem>
            <SelectItem value="JOURNALIER">Journalier</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-blue-300">{TYPE_DESCRIPTIONS[formData.type]}</p>
      </div>
      {formData.type === 'SHIFT' && (
        <div className="space-y-2">
          <Label>Type de shift *</Label>
          <Select
            value={formData.shift_type}
            onValueChange={(v) => handleShiftTypeChange(v as ShiftType)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Sélectionner le type de shift" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="MORNING">Shift Matin</SelectItem>
              <SelectItem value="NIGHT">Shift Nuit</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="date_debut">Date de début *</Label>
          <Input
            id="date_debut"
            type="datetime-local"
            value={formData.date_debut}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, date_debut: e.target.value }))
            }
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="date_fin">Date de fin *</Label>
          <Input
            id="date_fin"
            type="datetime-local"
            value={formData.date_fin}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, date_fin: e.target.value }))
            }
          />
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label>Zone de Travail</Label>
        <Select value={formData.zone_travail} onValueChange={handleZoneChange}>
          <SelectTrigger>
            <SelectValue placeholder="Sélectionner une zone de travail" />
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
      {formData.zone_travail &&
        (SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone_travail]?.length ?? 0) > 0 && (
          <div className="space-y-2">
            <Label>Sous-Zone</Label>
            <Select value={formData.sous_zone} onValueChange={handleSubZoneChange}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner une sous-zone" />
              </SelectTrigger>
              <SelectContent>
                {SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone_travail].map((sz) => (
                  <SelectItem key={sz} value={sz}>
                    {sz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      {formData.zone_travail &&
        formData.sous_zone &&
        ORDRE_TEMPLATES[formData.zone_travail]?.[formData.sous_zone] && (
          <div className="space-y-2">
            <Label>Ordre (position dans la ligne)</Label>
            <Select value={formData.ordre} onValueChange={handleOrderChange}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un ordre/position" />
              </SelectTrigger>
              <SelectContent>
                {ORDRE_TEMPLATES[formData.zone_travail][formData.sous_zone].map((t) => (
                  <SelectItem key={t.ordre} value={String(t.ordre)}>
                    {t.ordre} - {t.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      {!formData.zone_travail && (
        <p className="text-sm text-blue-300 mt-2">
          La sélection d'une zone filtrera automatiquement les machines à l'étape suivante.
        </p>
      )}
    </div>
  );

  const renderStep3 = () => (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-blue-300">
          {formData.machine_ids.length} sélectionnée(s) / {filteredMachines.length} affichée(s)
        </p>
        {filteredMachines.length > 0 && (
          <div className="flex gap-2">
            <button
              type="button"
              className="text-[11px] font-mono uppercase tracking-wider px-2 py-1 rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 transition-colors"
              onClick={() =>
                setFormData((prev) => ({
                  ...prev,
                  machine_ids: Array.from(
                    new Set([...prev.machine_ids, ...filteredMachines.map((m) => m.id)])
                  ),
                }))
              }
            >
              Tout cocher
            </button>
            <button
              type="button"
              className="text-[11px] font-mono uppercase tracking-wider px-2 py-1 rounded border border-slate-500/30 bg-slate-700/30 text-slate-300 hover:bg-slate-700/50 transition-colors"
              onClick={() => {
                const vis = new Set(filteredMachines.map((m) => m.id));
                setFormData((prev) => ({
                  ...prev,
                  machine_ids: prev.machine_ids.filter((id) => !vis.has(id)),
                }));
              }}
            >
              Tout décocher
            </button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto border rounded-md bg-slate-800/50 space-y-1 p-2">
        {filteredMachines.length === 0 ? (
          <p className="text-sm text-blue-300 p-2">
            {formData.zone_travail
              ? 'Aucune machine disponible dans cette zone.'
              : "Sélectionnez une zone à l'étape précédente pour filtrer les machines."}
          </p>
        ) : (
          filteredMachines.map((m) => (
            <div
              key={m.id}
              className="flex items-center space-x-2 p-2 hover:bg-slate-800 rounded"
            >
              <Checkbox
                id={`machine-${m.id}`}
                checked={formData.machine_ids.includes(m.id)}
                onCheckedChange={() => toggleMachine(m.id)}
              />
              <label
                htmlFor={`machine-${m.id}`}
                className="text-sm font-medium cursor-pointer flex-1"
              >
                {m.nom} (#{m.id}) - {m.statut}
              </label>
            </div>
          ))
        )}
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>
          Chef Opération (CHETOP){' '}
          {formData.type === 'SHIFT' && <span className="text-red-400">*</span>}
        </Label>
        <Select
          value={formData.chef_operation_id?.toString()}
          onValueChange={(v) =>
            setFormData((prev) => ({ ...prev, chef_operation_id: parseInt(v) }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Sélectionner un Chef Opération" />
          </SelectTrigger>
          <SelectContent>
            {filterUsersByPlanningShift(chefOperations).length === 0 ? (
              <SelectItem value="none" disabled>
                Aucun CHETOP disponible
              </SelectItem>
            ) : (
              filterUsersByPlanningShift(chefOperations).map((u) => (
                <SelectItem key={u.id} value={u.id.toString()}>
                  <span className="flex items-center gap-2">
                    {u.nom} - {u.email} {getUserShiftBadge(u.shift_type)}
                  </span>
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Chef Technique (CHEFTECH)</Label>
        <Select
          value={formData.chef_technique_id?.toString()}
          onValueChange={(v) =>
            setFormData((prev) => ({ ...prev, chef_technique_id: parseInt(v) }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Sélectionner un Chef Technique" />
          </SelectTrigger>
          <SelectContent>
            {filterUsersByPlanningShift(chefTechniques).length === 0 ? (
              <SelectItem value="none" disabled>
                Aucun CHEFTECH disponible
              </SelectItem>
            ) : (
              filterUsersByPlanningShift(chefTechniques).map((u) => (
                <SelectItem key={u.id} value={u.id.toString()}>
                  <span className="flex items-center gap-2">
                    {u.nom} - {u.email} {getUserShiftBadge(u.shift_type)}
                  </span>
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Techniciens</Label>
        <p className="text-xs text-blue-300">
          {formData.technicien_ids.length} technicien(s) sélectionné(s)
        </p>
        <div className="border rounded-md p-2 max-h-64 overflow-y-auto space-y-1 bg-slate-800/50">
          {filterUsersByPlanningShift(techniciens).length === 0 ? (
            <p className="text-sm text-blue-300 p-2">Aucun technicien disponible</p>
          ) : (
            filterUsersByPlanningShift(techniciens).map((t) => (
              <div
                key={t.id}
                className="flex items-center space-x-2 p-2 hover:bg-slate-800 rounded"
              >
                <Checkbox
                  id={`tech-${t.id}`}
                  checked={formData.technicien_ids.includes(t.id)}
                  onCheckedChange={() => toggleTechnicien(t.id)}
                />
                <label
                  htmlFor={`tech-${t.id}`}
                  className="text-sm font-medium cursor-pointer flex-1 flex items-center gap-2"
                >
                  {t.nom} - {t.email} {getUserShiftBadge(t.shift_type)}
                </label>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );

  const renderStep5 = () => {
    const chefOp = chefOperations.find((u) => u.id === formData.chef_operation_id);
    const chefTech = chefTechniques.find((u) => u.id === formData.chef_technique_id);
    const selectedTechs = techniciens.filter((t) =>
      formData.technicien_ids.includes(t.id)
    );
    const selectedMachines = machines.filter((m) =>
      formData.machine_ids.includes(m.id)
    );
    const startDate = formData.date_debut
      ? new Date(formData.date_debut).toLocaleString('fr-FR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '—';
    const endDate = formData.date_fin
      ? new Date(formData.date_fin).toLocaleString('fr-FR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '—';
    const days =
      formData.date_debut && formData.date_fin
        ? Math.ceil(
            Math.abs(
              new Date(formData.date_fin).getTime() -
                new Date(formData.date_debut).getTime()
            ) /
              (1000 * 60 * 60 * 24)
          )
        : 0;

    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">
            Planning
          </p>
          <p className="font-semibold text-white">{formData.identifiant_planning}</p>
          <div className="flex gap-2 flex-wrap">
            <Badge className="bg-blue-100 text-blue-800">{formData.type}</Badge>
            {formData.shift_type && (
              <Badge
                className={
                  formData.shift_type === 'MORNING'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-indigo-100 text-indigo-800'
                }
              >
                {formData.shift_type}
              </Badge>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">
            Période
          </p>
          <p className="text-sm">
            <span className="text-slate-400">Début :</span> {startDate}
          </p>
          <p className="text-sm">
            <span className="text-slate-400">Fin :</span> {endDate}
          </p>
          <p className="text-sm">
            <span className="text-slate-400">Durée :</span> {days} jour
            {days > 1 ? 's' : ''}
          </p>
        </div>
        {formData.zone_travail && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">
              Localisation
            </p>
            <p className="text-sm">
              {formData.zone_travail}
              {formData.sous_zone && ` › ${formData.sous_zone}`}
              {formData.ordre && ` (Ordre ${formData.ordre})`}
            </p>
          </div>
        )}
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">
            Machines ({selectedMachines.length})
          </p>
          {selectedMachines.length === 0 ? (
            <p className="text-sm text-slate-400">Aucune machine sélectionnée</p>
          ) : (
            <p className="text-sm">
              {selectedMachines
                .slice(0, 5)
                .map((m) => m.nom)
                .join(', ')}
              {selectedMachines.length > 5 &&
                ` + ${selectedMachines.length - 5} autres`}
            </p>
          )}
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">
            Équipe
          </p>
          {chefOp && (
            <p className="text-sm">
              <span className="text-slate-400">Chef Op :</span> {chefOp.nom}
            </p>
          )}
          {chefTech && (
            <p className="text-sm">
              <span className="text-slate-400">Chef Tech :</span> {chefTech.nom}
            </p>
          )}
          <p className="text-sm">
            <span className="text-slate-400">Techniciens :</span>{' '}
            {selectedTechs.length === 0
              ? 'Aucun'
              : selectedTechs.map((t) => t.nom).join(', ')}
          </p>
        </div>
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const renderCurrentStep = () => {
    if (dataLoading) {
      return (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      );
    }
    switch (currentStep) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      case 4: return renderStep4();
      case 5: return renderStep5();
      default: return null;
    }
  };

  const isLastStep = currentStep === 5;

  return (
    <Sheet open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-[900px] p-0 flex flex-col h-full"
      >
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <StepSidebar
            currentStep={currentStep}
            completedSteps={completedSteps}
            onJump={handleJumpTo}
          />
          {/* Content area */}
          <div className="flex flex-col flex-1 overflow-hidden">
            {/* Header */}
            <div className="px-6 pt-8 pb-4 border-b border-slate-700">
              <h2 className="text-xl font-semibold text-white">
                {planning ? 'Modifier le planning' : 'Créer un planning'}
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                Étape {currentStep} sur {STEPS.length} —{' '}
                {STEPS[currentStep - 1].title}
              </p>
            </div>
            {/* Step content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {renderCurrentStep()}
            </div>
            {/* Inline error */}
            {stepError && (
              <div className="px-6 py-2">
                <p className="text-sm text-red-400">{stepError}</p>
              </div>
            )}
            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-700 flex justify-between">
              <Button
                variant="outline"
                onClick={currentStep === 1 ? onClose : handleBack}
              >
                {currentStep === 1 ? 'Annuler' : '← Retour'}
              </Button>
              {isLastStep ? (
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="gap-2 bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Bell className="h-4 w-4" />
                  {submitting
                    ? 'Enregistrement...'
                    : planning
                    ? 'Enregistrer & Notifier'
                    : 'Créer & Notifier'}
                </Button>
              ) : (
                <Button
                  onClick={handleNext}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Suivant <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
