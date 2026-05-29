import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, ArrowLeft, Send, Calendar } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate, useParams } from 'react-router-dom';

interface User {
  id: number;
  nom: string;
  email: string;
  role: string;
}

interface Machine {
  id: number;
  nom: string;
  reference?: string;
}

interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  assigned_users: User[];
  machines: Machine[];
  planning_statut?: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
}

interface Task {
  id?: number;
  titre: string;
  description: string;
  technician_id: number | null;
  machine_id: number | null;
  task_type: 'DIAGNOSTIC' | 'CORRECTION' | '';
  date_debut: string;
  date_fin: string;
}

const TASK_TYPE_OPTIONS = [
  { value: 'DIAGNOSTIC', label: 'Diagnostic' },
  { value: 'CORRECTION', label: 'Correction' },
];

export default function PlanningTaskForm() {
  const { planningId } = useParams<{ planningId: string }>();
  const [planning, setPlanning] = useState<Planning | null>(null);
  const [tasks, setTasks] = useState<Task[]>([
    { titre: '', description: '', technician_id: null, machine_id: null, task_type: '', date_debut: '', date_fin: '' }
  ]);
  const [dateErrors, setDateErrors] = useState<Record<number, { start?: string; end?: string }>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    if (planningId) {
      fetchPlanning();
    }
  }, [planningId]);

  const fetchPlanning = async () => {
    try {
      const response = await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}`,
        method: 'GET',
      });
      const data = response?.data || response;
      
      const [machinesResponse, usersResponse] = await Promise.all([
        client.apiCall.invoke({
          url: `/api/v1/plannings/${planningId}/machines`,
          method: 'GET',
        }),
        client.apiCall.invoke({
          url: `/api/v1/plannings/${planningId}/users`,
          method: 'GET',
        }),
      ]);
      let machines = (machinesResponse?.data || machinesResponse) || [];
      const users = (usersResponse?.data || usersResponse) || [];

      // Fallback: when planning has no machines assigned, surface ALL machines
      // so cheftech can still create tasks (admin should later assign machines
      // explicitly to the planning).
      let isFallback = false;
      if (!machines || machines.length === 0) {
        try {
          const allMachinesResp = await client.apiCall.invoke({
            url: '/api/v1/entities/machines?size=500',
            method: 'GET',
          });
          const all = (allMachinesResp?.data || allMachinesResp)?.items
                    || (allMachinesResp?.data || allMachinesResp)
                    || [];
          if (Array.isArray(all) && all.length > 0) {
            machines = all;
            isFallback = true;
          }
        } catch (fallbackErr) {
          console.warn('Fallback machine fetch failed', fallbackErr);
        }
      }

      setPlanning({ ...data, machines, assigned_users: users, _machinesFallback: isFallback });
      
      const tasksResponse = await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/taches`,
        method: 'GET',
      });
      const existingTasks = (tasksResponse?.data || tasksResponse)?.items || [];
      
      if (existingTasks.length > 0) {
        setTasks(existingTasks.map((t: any) => ({
          id: t.id,
          titre: t.titre,
          description: t.description,
          technician_id: t.technician_id,
          machine_id: t.machine_id,
          task_type: t.task_type,
          date_debut: t.date_debut?.slice(0, 16),
          date_fin: t.date_fin?.slice(0, 16),
        })));
      }
    } catch (error: any) {
      toast({ title: 'Error', description: 'Failed to load planning', variant: 'destructive' });
      navigate('/cheftech/planning');
    } finally {
      setLoading(false);
    }
  };

  const addTask = () => {
    setTasks([...tasks, { titre: '', description: '', technician_id: null, machine_id: null, task_type: '', date_debut: '', date_fin: '' }]);
  };

  const removeTask = (index: number) => {
    if (tasks.length > 1) {
      setTasks(tasks.filter((_, i) => i !== index));
    }
  };

  const updateTask = (index: number, field: keyof Task, value: any) => {
    const newTasks = [...tasks];
    (newTasks[index] as any)[field] = value;
    setTasks(newTasks);
    
    const task = newTasks[index];
    if ((field === 'date_debut' || field === 'date_fin') && task.date_debut && task.date_fin && planning) {
      const newErrors = { ...dateErrors };
      const taskStart = new Date(task.date_debut);
      const taskEnd = new Date(task.date_fin);
      const planStart = new Date(planning.date_debut);
      const planEnd = new Date(planning.date_fin);
      
      if (taskStart < planStart) {
        newErrors[index] = { ...newErrors[index], start: 'Must be >= planning start' };
      } else {
        const err = newErrors[index] || {};
        delete err.start;
        newErrors[index] = err;
      }
      
      if (taskEnd > planEnd) {
        newErrors[index] = { ...newErrors[index], end: 'Must be <= planning end' };
      } else {
        const err = newErrors[index] || {};
        delete err.end;
        newErrors[index] = err;
      }
      setDateErrors(newErrors);
    }
  };

  const validateDates = (task: Task): string | null => {
    if (!planning) return null;
    if (!task.date_debut || !task.date_fin) return null;
    
    const taskStart = new Date(task.date_debut);
    const taskEnd = new Date(task.date_fin);
    const planStart = new Date(planning.date_debut);
    const planEnd = new Date(planning.date_fin);
    
    if (taskStart < planStart) {
      return `Start date must be >= ${planning.date_debut.slice(0, 16)}`;
    }
    if (taskEnd > planEnd) {
      return `End date must be <= ${planning.date_fin.slice(0, 16)}`;
    }
    return null;
  };

  const handleSubmit = async () => {
    for (let i = 0; i < tasks.length; i++) {
      const task = tasks[i];
      const error = validateDates(task);
      if (error) {
        toast({ title: 'Validation Error', description: `Task ${i + 1}: ${error}`, variant: 'destructive' });
        return;
      }
      if (!task.titre || !task.description || !task.technician_id || !task.machine_id || !task.task_type || !task.date_debut || !task.date_fin) {
        toast({ title: 'Validation Error', description: `Task ${i + 1}: All fields are required`, variant: 'destructive' });
        return;
      }
    }
    
    if (tasks.length === 0) {
      toast({ title: 'Error', description: 'At least one task is required', variant: 'destructive' });
      return;
    }

    try {
      setSubmitting(true);
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/taches`,
        method: 'POST',
        data: {
          tasks: tasks.map(t => ({
            titre: t.titre,
            description: t.description,
            technician_id: t.technician_id,
            machine_id: t.machine_id,
            task_type: t.task_type,
            date_debut: new Date(t.date_debut).toISOString(),
            date_fin: new Date(t.date_fin).toISOString(),
          }))
        }
      });
      toast({ title: 'Success', description: 'Tasks saved and planning submitted for approval' });
      navigate('/cheftech/planning');
    } catch (error: any) {
      const detail = error?.data?.detail || error?.response?.data?.detail || 'Failed to submit';
      toast({ title: 'Error', description: detail, variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!planning) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/cheftech/planning')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div>
          <h2 className="text-3xl font-bold text-white">{planning.identifiant_planning}</h2>
          <div className="flex items-center gap-2 mt-1 text-sm text-blue-300">
            <Calendar className="h-4 w-4" />
            {new Date(planning.date_debut).toLocaleString('fr-FR')} - {new Date(planning.date_fin).toLocaleString('fr-FR')}
          </div>
        </div>
      </div>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Tâches d'Exécution</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {tasks.map((task, index) => (
            <Card key={index} className="bg-slate-700 border-slate-600 p-4">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-white font-medium">Task {index + 1}</h4>
                {tasks.length > 1 && (
                  <Button variant="ghost" size="sm" onClick={() => removeTask(index)}>
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-slate-300">Task Title *</Label>
                  <Input
                    value={task.titre}
                    onChange={(e) => updateTask(index, 'titre', e.target.value)}
                    placeholder="Enter task title"
                    className="bg-slate-800 border-slate-600 text-white"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300">Task Type *</Label>
                  <Select value={task.task_type} onValueChange={(v) => updateTask(index, 'task_type', v)}>
                    <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                      <SelectValue placeholder="Select task type" />
                    </SelectTrigger>
                    <SelectContent>
                      {TASK_TYPE_OPTIONS.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2 md:col-span-2">
                  <Label className="text-slate-300">Description *</Label>
                  <Textarea
                    value={task.description}
                    onChange={(e) => updateTask(index, 'description', e.target.value)}
                    placeholder="Detailed instructions for this task"
                    className="bg-slate-800 border-slate-600 text-white"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300">Technician *</Label>
                  <Select value={task.technician_id?.toString() || ''} onValueChange={(v) => updateTask(index, 'technician_id', parseInt(v))}>
                    <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                      <SelectValue placeholder="Select technician" />
                    </SelectTrigger>
                    <SelectContent>
                      {planning.assigned_users?.filter((u: User) => u.role === 'TECHNICIEN').map((tech: User) => (
                        <SelectItem key={tech.id} value={tech.id.toString()}>{tech.nom}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300 flex items-center gap-2">
                    Machine *
                    {planning?._machinesFallback && (
                      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-amber-400/40 bg-amber-500/10 text-amber-300 font-mono">
                        ⚠ catalogue complet (planning sans machines)
                      </span>
                    )}
                  </Label>
                  {planning?._machinesFallback && (
                    <p className="text-[11px] text-amber-300/70 leading-relaxed">
                      Ce planning n'a aucune machine assignée — la liste affiche toutes les machines du parc.
                      Demandez à l'admin de pré-assigner les machines au planning pour filtrer cette liste.
                    </p>
                  )}
                  <Select value={task.machine_id?.toString() || ''} onValueChange={(v) => updateTask(index, 'machine_id', parseInt(v))}>
                    <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                      <SelectValue placeholder={(planning.machines || []).length === 0 ? "Aucune machine disponible" : "Sélectionner une machine"} />
                    </SelectTrigger>
                    <SelectContent>
                      {(planning.machines || []).length === 0 ? (
                        <div className="px-3 py-4 text-center text-xs text-slate-400">
                          Aucune machine — contactez l'admin
                        </div>
                      ) : (planning.machines || []).map((mach: Machine) => (
                        <SelectItem key={mach.id} value={mach.id.toString()}>
                          {mach.nom}{mach.reference ? ` (${mach.reference})` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300">Start Date/Time *</Label>
                  <Input
                    type="datetime-local"
                    value={task.date_debut}
                    onChange={(e) => updateTask(index, 'date_debut', e.target.value)}
                    className={`bg-slate-800 border-slate-600 text-white ${dateErrors[index]?.start ? 'border-red-500' : ''}`}
                  />
                  {dateErrors[index]?.start && (
                    <p className="text-red-400 text-xs">{dateErrors[index].start}</p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300">End Date/Time *</Label>
                  <Input
                    type="datetime-local"
                    value={task.date_fin}
                    onChange={(e) => updateTask(index, 'date_fin', e.target.value)}
                    className={`bg-slate-800 border-slate-600 text-white ${dateErrors[index]?.end ? 'border-red-500' : ''}`}
                  />
                  {dateErrors[index]?.end && (
                    <p className="text-red-400 text-xs">{dateErrors[index].end}</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
          
          <Button variant="outline" onClick={addTask} className="w-full">
            <Plus className="mr-2 h-4 w-4" />
            Ajouter une tâche
          </Button>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-4">
        <Button variant="outline" onClick={() => navigate('/cheftech/planning')}>
          Annuler
        </Button>
        <Button onClick={handleSubmit} disabled={submitting}>
          <Send className="mr-2 h-4 w-4" />
          {submitting ? 'Soumission...' : 'Soumettre pour approbation'}
        </Button>
      </div>
    </div>
  );
}