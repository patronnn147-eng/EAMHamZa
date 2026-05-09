import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { client } from '@/lib/api';
import { Alert, Technician, severityConfig, getRelativeTime } from '@/lib/alertUtils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { ToastAction } from '@/components/ui/toast';
import {
  Bell,
  CheckCircle2,
  ArrowLeft,
  TrendingDown,
  Activity,
  Cpu,
  Clock,
  Pencil,
  CalendarIcon,
  AlertTriangle as TriangleWarning,
} from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

// ─── Alert Card ───────────────────────────────────────────────────────────────

interface AlertCardProps {
  alert: Alert;
  machineName: string;
  onClick: () => void;
  showEditButton?: boolean;
  onEditClick?: () => void;
}

const AlertCard: React.FC<AlertCardProps> = ({
  alert,
  machineName,
  onClick,
  showEditButton = false,
  onEditClick,
}) => {
  const config = severityConfig[alert.severity] || severityConfig.LOW;
  const failurePct =
    alert.failure_probability != null
      ? Math.round(alert.failure_probability * 100)
      : null;

  return (
    <div
      onClick={onClick}
      className={`
        relative flex flex-col gap-0 rounded-xl border border-white/[0.06]
        border-l-4 ${config.border}
        bg-[#0f1623] cursor-pointer
        hover:bg-[#131c2e] hover:border-white/[0.1]
        transition-all duration-200
      `}
    >
      <div className="flex items-start justify-between px-4 pt-3 pb-2 gap-2">
        {/* Left: icon + content */}
        <div className="flex items-start gap-2 min-w-0">
          <div
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${config.iconBg}`}
          >
            {config.icon}
          </div>
          <div className="flex flex-col gap-1 min-w-0">
            {/* Severity badge */}
            <span
              className={`inline-flex self-start items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${config.badgeClass}`}
            >
              {config.label}
            </span>
            {/* Machine name */}
            <div className="flex items-center gap-1 text-xs font-semibold text-white">
              <Cpu className="h-3 w-3 opacity-60 shrink-0" />
              <span className="truncate">
                {machineName} (#{alert.machine_id})
              </span>
            </div>
            {/* Message */}
            <p className="text-[12px] text-white/60 leading-snug line-clamp-2">
              {alert.message}
            </p>
          </div>
        </div>

        {/* Edit button (technician lane only) */}
        {showEditButton && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEditClick?.();
            }}
            className="shrink-0 flex h-7 w-7 items-center justify-center rounded-lg text-white/30 hover:bg-white/5 hover:text-white/70 transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Bottom metrics */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.05] px-4 py-2">
        {/* Timestamp */}
        <div className="flex items-center gap-1 text-[10px] text-white/40">
          <Clock className="h-2.5 w-2.5" />
          {getRelativeTime(alert.created_at)}
        </div>

        {/* RUL */}
        {alert.rul_days != null && (
          <div className="flex items-center gap-1 text-[10px] text-white/40">
            <TrendingDown className="h-2.5 w-2.5" />
            RUL:{' '}
            <span className="font-semibold text-white/70">
              {alert.rul_days.toFixed(1)}j
            </span>
          </div>
        )}

        {/* Failure probability */}
        {failurePct != null && (
          <div className="flex items-center gap-1.5">
            <Activity className="h-2.5 w-2.5 text-white/40" />
            <span
              className={`text-[10px] font-bold ${
                failurePct >= 80
                  ? 'text-red-400'
                  : failurePct >= 60
                  ? 'text-orange-400'
                  : 'text-yellow-400'
              }`}
            >
              {failurePct}%
            </span>
            <div className="w-14 h-1 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full rounded-full ${config.barColor}`}
                style={{ width: `${Math.min(failurePct, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Lane Header ──────────────────────────────────────────────────────────────

const LaneHeader: React.FC<{
  label: string;
  count: number;
  color?: string;
}> = ({ label, count, color = 'text-white/50' }) => (
  <div className="flex items-center justify-between mb-3">
    <span
      className={`text-[11px] font-semibold uppercase tracking-wider ${color}`}
    >
      {label}
    </span>
    <Badge
      variant="outline"
      className="text-[10px] border-white/10 text-white/40 h-5 px-2"
    >
      {count}
    </Badge>
  </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ChefTechAlertWorkflow() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [machinesMap, setMachinesMap] = useState<Map<number, string>>(
    new Map()
  );
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [editMode, setEditMode] = useState(false);

  // ── Triage form state ──

  const [triageForm, setTriageForm] = useState({
    technicienId: '',
    priority: '',
    dueDate: undefined as Date | undefined,
    createWO: true,
  });
  const [techOpenWOs, setTechOpenWOs] = useState<number>(0);
  const [techLoadingCheck, setTechLoadingCheck] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // ── Data fetching ──

  const loadData = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;

      const [alertsRes, machinesRes, techRes] = await Promise.all([
        fetch(`${API}/api/v1/alerts`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        client.entities.machines.query({ query: {}, limit: 500 }),
        fetch(`${API}/api/v1/cheftech/techniciens?page=1&size=100`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(Array.isArray(data) ? data : []);
      }

      const map = new Map<number, string>();
      for (const m of (machinesRes as any)?.data?.items || []) {
        map.set(m.id, m.nom || `Machine #${m.id}`);
      }
      setMachinesMap(map);

      if (techRes.ok) {
        const techData = await techRes.json();
        setTechnicians(techData.items || []);
      }
    } catch (err) {
      console.error('Failed to load alert workflow data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // ── Swimlane split ──

  const systemLane = alerts.filter(
    (a) => ['MEDIUM', 'LOW'].includes(a.severity) && !a.is_linked_to_wo
  );
  const cheftechLane = alerts.filter(
    (a) => ['CRITICAL', 'HIGH'].includes(a.severity) && !a.is_linked_to_wo
  );
  const technicianLane = alerts.filter((a) => a.is_linked_to_wo);
  const allEmpty = !loading && alerts.length === 0;

  // ── Technician availability check ──

  const checkTechAvailability = async (techId: string) => {
    if (!techId) {
      setTechOpenWOs(0);
      return;
    }
    setTechLoadingCheck(true);
    try {
      const res = await fetch(
        `${API}/api/v1/entities/ordres_travail?query=${encodeURIComponent(
          JSON.stringify({ assigned_to: parseInt(techId) })
        )}&limit=100`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      const data = await res.json();
      const open = (data.items || []).filter(
        (wo: any) => !['TERMINE', 'ANNULE'].includes(wo.statut)
      ).length;
      setTechOpenWOs(open);
    } catch {
      setTechOpenWOs(0);
    } finally {
      setTechLoadingCheck(false);
    }
  };

  // ── Close panel helper ──

  const closePanel = () => {
    setSelectedAlert(null);
    setEditMode(false);
    setTriageForm({ technicienId: '', priority: '', dueDate: undefined, createWO: true });
    setTechOpenWOs(0);
  };

  // ── handleCardClick ──

  const handleCardClick = (alert: Alert, edit = false) => {
    setSelectedAlert(alert);
    setEditMode(edit);
    if (edit) {
      setTriageForm({ technicienId: '', priority: '', dueDate: undefined, createWO: false });
    }
    setTechOpenWOs(0);
  };

  // ── handleAssign ──

  const handleAssign = async (alert: Alert) => {
    setAssigning(true);
    try {
      // Optimistic update — move to technician lane
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alert.id ? { ...a, is_linked_to_wo: true } : a
        )
      );

      // Close panel immediately
      closePanel();

      // API call
      const res = await fetch(
        `${API}/api/v1/alerts/${alert.id}/create-work-order`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            created_by: parseInt(user?.id || '0'),
            assigned_to: parseInt(triageForm.technicienId),
            priority: triageForm.priority || undefined,
            due_date: triageForm.dueDate?.toISOString() || undefined,
          }),
        }
      );

      if (!res.ok) {
        throw new Error('API error');
      }
    } catch {
      // Rollback on error
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alert.id ? { ...a, is_linked_to_wo: false } : a
        )
      );
      toast({
        title: 'Erreur',
        description: "Impossible d'assigner l'alerte",
        variant: 'destructive',
      });
    } finally {
      setAssigning(false);
    }
  };

  // ── handleDismiss (3s undo) ──

  const handleDismiss = (alert: Alert) => {
    // Optimistic remove
    setAlerts((prev) => prev.filter((a) => a.id !== alert.id));

    // Close panel
    closePanel();

    // Track undo state
    let undone = false;

    // Toast with undo action
    const { dismiss: dismissToast } = toast({
      title: 'Alerte ignorée',
      action: (
        <ToastAction
          altText="Annuler"
          onClick={() => {
            undone = true;
            setAlerts((prev) => [...prev, alert]);
            dismissToast();
          }}
        >
          Annuler
        </ToastAction>
      ),
    });

    // After 3s, if not undone, call API
    setTimeout(async () => {
      if (!undone) {
        try {
          await fetch(`${API}/api/v1/alerts/${alert.id}/dismiss`, {
            method: 'PATCH',
            headers: {
              Authorization: `Bearer ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: parseInt(user?.id || '0') }),
          });
        } catch {
          // Silent fail — alert already removed from UI
        }
      }
    }, 3000);
  };

  // ── Loading ──

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  // ── Render ──

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="h-6 w-6 text-white/70" />
          <h1 className="text-2xl font-bold text-white">Centre des Alertes</h1>
          {alerts.filter((a) => !a.is_linked_to_wo).length > 0 && (
            <Badge
              variant="outline"
              className="border-white/10 text-white/50 text-xs"
            >
              {alerts.filter((a) => !a.is_linked_to_wo).length} actives
            </Badge>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadData}
          className="border-white/10 bg-white/5 text-white/60 hover:bg-white/10 text-xs"
        >
          Actualiser
        </Button>
      </div>

      {/* All-empty banner */}
      {allEmpty && (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="font-medium text-sm">
            Système sain — Aucune alerte active
          </span>
        </div>
      )}

      {/* 3-column swimlane grid */}
      <div className="grid grid-cols-3 gap-4 min-h-[500px]">
        {/* ── System (Auto) Lane ── */}
        <div className="flex flex-col">
          <LaneHeader label="Système (Auto)" count={systemLane.length} />
          <div className="flex flex-col gap-2 flex-1">
            {systemLane.length === 0 ? (
              <div className="flex items-center justify-center rounded-xl border border-dashed border-white/[0.06] px-4 py-8 text-center">
                <span className="text-xs text-white/25">
                  Aucune alerte en attente
                </span>
              </div>
            ) : (
              systemLane.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  machineName={
                    machinesMap.get(alert.machine_id) ??
                    `Machine #${alert.machine_id}`
                  }
                  onClick={() => handleCardClick(alert)}
                />
              ))
            )}
          </div>
        </div>

        {/* ── ChefTech Triage Lane ── */}
        <div className="flex flex-col">
          <LaneHeader
            label="Triage ChefTech"
            count={cheftechLane.length}
            color="text-orange-400/70"
          />
          <div className="flex flex-col gap-2 flex-1">
            {cheftechLane.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-emerald-500/20 bg-emerald-500/5 px-4 py-8 text-center">
                <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                <span className="text-xs text-emerald-400/80 font-medium">
                  Aucune alerte critique
                </span>
              </div>
            ) : (
              cheftechLane.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  machineName={
                    machinesMap.get(alert.machine_id) ??
                    `Machine #${alert.machine_id}`
                  }
                  onClick={() => handleCardClick(alert)}
                />
              ))
            )}
          </div>
        </div>

        {/* ── Technician Execution Lane ── */}
        <div className="flex flex-col">
          <LaneHeader
            label="Technicien (Exécution)"
            count={technicianLane.length}
            color="text-blue-400/70"
          />
          <div className="flex flex-col gap-2 flex-1">
            {technicianLane.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/[0.06] px-4 py-8 text-center">
                <ArrowLeft className="h-5 w-5 text-white/20" />
                <span className="text-xs text-white/25">
                  Assignez depuis le triage
                </span>
              </div>
            ) : (
              technicianLane.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  machineName={
                    machinesMap.get(alert.machine_id) ??
                    `Machine #${alert.machine_id}`
                  }
                  onClick={() => handleCardClick(alert)}
                  showEditButton
                  onEditClick={() => handleCardClick(alert, true)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Triage Panel (Sheet) ── */}
      <Sheet
        open={!!selectedAlert}
        onOpenChange={(open) => {
          if (!open) closePanel();
        }}
      >
        <SheetContent
          side="right"
          className="w-[360px] bg-[#0f1623] border-l border-white/[0.06] overflow-y-auto p-6"
        >
          <SheetHeader className="mb-5">
            <SheetTitle className="text-white text-base">
              {editMode ? "Modifier l'assignation" : 'Triage Alerte'}
            </SheetTitle>
          </SheetHeader>

          {selectedAlert && (
            <div className="space-y-5">
              {/* Section 1: Alert Summary */}
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">
                  Résumé
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase ${
                      severityConfig[selectedAlert.severity]?.badgeClass || ''
                    }`}
                  >
                    {selectedAlert.severity}
                  </span>
                  <span className="text-xs text-white/50">
                    {selectedAlert.alert_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-sm font-semibold text-white">
                  {machinesMap.get(selectedAlert.machine_id) ??
                    `Machine #${selectedAlert.machine_id}`}{' '}
                  (#{selectedAlert.machine_id})
                </p>
                <p className="text-sm text-white/60 leading-relaxed">
                  {selectedAlert.message}
                </p>
                <p className="text-xs text-white/30">
                  {new Date(selectedAlert.created_at).toLocaleString('fr-FR')}
                </p>
              </div>

              <Separator className="bg-white/[0.06]" />

              {/* Section 2: Assign */}
              <div className="space-y-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">
                  Assigner
                </p>

                {/* Technician dropdown */}
                <div className="space-y-1.5">
                  <Label className="text-xs text-white/60">Technicien</Label>
                  <Select
                    value={triageForm.technicienId}
                    onValueChange={(val) => {
                      setTriageForm((f) => ({ ...f, technicienId: val }));
                      checkTechAvailability(val);
                    }}
                  >
                    <SelectTrigger className="bg-[#131c2e] border-white/[0.08] text-white text-sm">
                      <SelectValue placeholder="Sélectionner un technicien" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#131c2e] border-white/[0.08]">
                      {technicians.map((tech) => (
                        <SelectItem
                          key={tech.id}
                          value={String(tech.id)}
                          className="text-white"
                        >
                          {tech.nom}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Availability warning */}
                  {triageForm.technicienId && techOpenWOs > 0 && (
                    <div className="flex items-center gap-1.5 text-xs text-orange-400 mt-1">
                      <TriangleWarning className="h-3.5 w-3.5 shrink-0" />
                      <span>
                        Technicien occupé ({techOpenWOs} OT en cours)
                      </span>
                    </div>
                  )}
                  {techLoadingCheck && (
                    <p className="text-xs text-white/30 mt-1">
                      Vérification disponibilité...
                    </p>
                  )}
                </div>

                {/* Priority dropdown */}
                <div className="space-y-1.5">
                  <Label className="text-xs text-white/60">Priorité</Label>
                  <Select
                    value={triageForm.priority}
                    onValueChange={(val) =>
                      setTriageForm((f) => ({ ...f, priority: val }))
                    }
                  >
                    <SelectTrigger className="bg-[#131c2e] border-white/[0.08] text-white text-sm">
                      <SelectValue placeholder="Sélectionner une priorité" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#131c2e] border-white/[0.08]">
                      <SelectItem value="CRITIQUE" className="text-white">
                        Critique
                      </SelectItem>
                      <SelectItem value="HAUTE" className="text-white">
                        Haute
                      </SelectItem>
                      <SelectItem value="MOYENNE" className="text-white">
                        Moyenne
                      </SelectItem>
                      <SelectItem value="BASSE" className="text-white">
                        Basse
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Due date */}
                <div className="space-y-1.5">
                  <Label className="text-xs text-white/60">
                    Date d'échéance
                  </Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-start bg-[#131c2e] border-white/[0.08] text-white/70 hover:bg-[#1a2535] text-sm font-normal"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4 opacity-50" />
                        {triageForm.dueDate
                          ? triageForm.dueDate.toLocaleDateString('fr-FR')
                          : 'Sélectionner une date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 bg-[#131c2e] border-white/[0.08]">
                      <Calendar
                        mode="single"
                        selected={triageForm.dueDate}
                        onSelect={(date) =>
                          setTriageForm((f) => ({ ...f, dueDate: date }))
                        }
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Create WO checkbox */}
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="createWO"
                    checked={triageForm.createWO}
                    onCheckedChange={(checked) =>
                      setTriageForm((f) => ({ ...f, createWO: !!checked }))
                    }
                    className="border-white/20"
                  />
                  <Label
                    htmlFor="createWO"
                    className="text-sm text-white/70 cursor-pointer"
                  >
                    Créer un Ordre de Travail
                  </Label>
                </div>
              </div>

              <Separator className="bg-white/[0.06]" />

              {/* Section 3: Actions */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1 border-white/10 bg-white/5 text-white hover:bg-white/10 text-sm"
                  onClick={() => handleDismiss(selectedAlert)}
                >
                  Ignorer alerte
                </Button>
                <Button
                  className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-sm"
                  onClick={() => handleAssign(selectedAlert)}
                  disabled={assigning || !triageForm.technicienId}
                >
                  {assigning ? 'Assignation...' : 'Assigner & Notifier'}
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

// Export types for extension
export type { AlertCardProps };
export { API, getToken };
