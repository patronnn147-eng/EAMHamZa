import React, { useState, useEffect, useCallback } from 'react';
import { X, Eye, Wrench, Calendar, ChevronRight } from 'lucide-react';
import { client } from '@/lib/api';
import { TechnicianNewInterventionModal } from './components/TechnicianNewInterventionModal';

type TaskType = 'DIAGNOSTIC' | 'CORRECTION';
type PlanningStatut = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
type TaskStatut = 'DRAFT' | 'IN_PROGRESS' | 'COMPLETED';

interface PlanningTask {
  id: number;
  titre: string;
  description: string;
  task_type: TaskType;
  technician_id: number;
  machine_id: number;
  machine_nom: string | null;
  planning_id: number;
  planning_identifiant: string | null;
  planning_statut: PlanningStatut | null;
  statut: TaskStatut;
  date_debut: string;
  date_fin: string;
  created_at: string;
}

const TASK_TYPE_STYLE: Record<TaskType, { bg: string; text: string; label: string }> = {
  DIAGNOSTIC: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'DIAGNOSTIC' },
  CORRECTION: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'CORRECTION' },
};

const PLANNING_STATUT_STYLE: Record<PlanningStatut, { bg: string; text: string }> = {
  DRAFT:     { bg: 'bg-slate-500/20',  text: 'text-slate-400' },
  SUBMITTED: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  APPROVED:  { bg: 'bg-green-500/20',  text: 'text-green-400' },
  REJECTED:  { bg: 'bg-red-500/20',    text: 'text-red-400' },
};

const TASK_STATUT_STYLE: Record<TaskStatut, { bg: string; text: string; label: string }> = {
  DRAFT:       { bg: 'bg-slate-500/20',   text: 'text-slate-400',   label: 'À faire' },
  IN_PROGRESS: { bg: 'bg-blue-500/20',    text: 'text-blue-400',    label: 'En cours' },
  COMPLETED:   { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Terminé' },
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

export default function TechnicianPlanningTaches() {
  const [tasks, setTasks] = useState<PlanningTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<PlanningTask | null>(null);
  const [interventionOpen, setInterventionOpen] = useState(false);
  const [interventionTask, setInterventionTask] = useState<PlanningTask | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.apiCall.invoke({ url: '/api/v1/technicien/planning-taches', method: 'GET' });
      const data = res?.data ?? res;
      setTasks(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const handleOpenIntervention = (task: PlanningTask) => {
    setInterventionTask(task);
    setInterventionOpen(true);
  };

  const handleInterventionSuccess = () => {
    setInterventionOpen(false);
    setInterventionTask(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Tâches de Planning</h1>
        <p className="text-slate-400 text-sm mt-1">Vos tâches assignées dans les plannings</p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 text-slate-400">Chargement…</div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && tasks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Calendar className="h-12 w-12 mb-3 opacity-30" />
          <p>Aucune tâche assignée pour le moment.</p>
        </div>
      )}

      {!loading && !error && tasks.length > 0 && (
        <div className="flex gap-6">
          {/* Card list */}
          <div className="flex-1 min-w-0 space-y-3">
            {tasks.map((task) => {
              const typeStyle = TASK_TYPE_STYLE[task.task_type] ?? TASK_TYPE_STYLE.CORRECTION;
              const taskStatutStyle = TASK_STATUT_STYLE[task.statut] ?? TASK_STATUT_STYLE.DRAFT;
              const isSelected = selectedTask?.id === task.id;
              return (
                <div
                  key={task.id}
                  className={`bg-slate-800 rounded-xl p-4 border transition-colors ${
                    isSelected ? 'border-amber-500/60' : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span className={`inline-block text-[11px] font-semibold px-2 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text} uppercase tracking-wide mb-2`}>
                        {typeStyle.label}
                      </span>
                      <h3 className="text-slate-100 font-semibold text-[15px] leading-tight">{task.titre}</h3>
                      <p className="text-slate-400 text-xs mt-1">
                        {task.machine_nom ?? `Machine #${task.machine_id}`}
                        {task.planning_identifiant && (
                          <> &nbsp;·&nbsp; {task.planning_identifiant}</>
                        )}
                      </p>
                    </div>
                    <span className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded ${taskStatutStyle.bg} ${taskStatutStyle.text}`}>
                      {taskStatutStyle.label}
                    </span>
                  </div>

                  <div className="flex gap-4 mt-3 text-xs text-slate-400">
                    <span>📅 {formatDate(task.date_debut)}</span>
                    <ChevronRight className="h-3 w-3 mt-0.5 text-slate-600" />
                    <span>{formatDate(task.date_fin)}</span>
                  </div>

                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => setSelectedTask(isSelected ? null : task)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-500 transition-colors"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Voir détails
                    </button>
                    <button
                      onClick={() => handleOpenIntervention(task)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-amber-500 text-amber-400 text-xs font-medium hover:bg-amber-500/10 transition-colors"
                    >
                      <Wrench className="h-3.5 w-3.5" />
                      Demander intervention
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Side drawer */}
          {selectedTask && (
            <div className="w-80 shrink-0 bg-slate-900 border border-amber-500/30 rounded-xl p-5 self-start sticky top-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-slate-100 font-semibold text-[15px]">Détails de la tâche</h3>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider">Titre</span>
                  <p className="text-slate-100 mt-0.5">{selectedTask.titre}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider">Description</span>
                  <p className="text-slate-300 mt-0.5 text-xs leading-relaxed">{selectedTask.description}</p>
                </div>
                <div className="flex gap-4">
                  <div>
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider">Type</span>
                    <p className={`mt-0.5 font-semibold ${TASK_TYPE_STYLE[selectedTask.task_type]?.text ?? 'text-slate-300'}`}>
                      {selectedTask.task_type}
                    </p>
                  </div>
                  {selectedTask.planning_statut && (
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase tracking-wider">Statut planning</span>
                      <p className={`mt-0.5 font-semibold ${PLANNING_STATUT_STYLE[selectedTask.planning_statut]?.text ?? 'text-slate-300'}`}>
                        {selectedTask.planning_statut}
                      </p>
                    </div>
                  )}
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider">Machine</span>
                  <p className="text-slate-100 mt-0.5">{selectedTask.machine_nom ?? `Machine #${selectedTask.machine_id}`}</p>
                </div>
                {selectedTask.planning_identifiant && (
                  <div>
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider">Planning</span>
                    <p className="text-slate-100 mt-0.5">{selectedTask.planning_identifiant}</p>
                  </div>
                )}
                <div>
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider">Fenêtre d'intervention</span>
                  <p className="text-slate-100 mt-0.5 text-xs">
                    {formatDate(selectedTask.date_debut)} → {formatDate(selectedTask.date_fin)}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleOpenIntervention(selectedTask)}
                className="w-full mt-5 py-2.5 rounded-lg bg-amber-500 text-slate-900 font-bold text-sm hover:bg-amber-400 transition-colors flex items-center justify-center gap-2"
              >
                <Wrench className="h-4 w-4" />
                Demander une intervention
              </button>
            </div>
          )}
        </div>
      )}

      {interventionTask && (
        <TechnicianNewInterventionModal
          open={interventionOpen}
          onOpenChange={setInterventionOpen}
          onSuccess={handleInterventionSuccess}
          initialMachineId={interventionTask.machine_id}
          initialPlanningTacheId={interventionTask.id}
        />
      )}
    </div>
  );
}
