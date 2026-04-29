# CHEFTECH Task-Level Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow CHEFTECH to create detailed execution tasks for DRAFT plannings before submitting for ADMIN approval

**Architecture:** Backend API endpoints for task CRUD + Frontend pages with task planning form and task list view

**Tech Stack:** FastAPI (backend), React + TypeScript (frontend), PostgreSQL

---

## File Structure

### Backend (fasten API routes to existing planning routers)
- `modules/shared/routes/planning/taches.py` - NEW: Task CRUD endpoints
- `modules/shared/routes/planning/schemas.py` - MODIFY: Add task schemas
- `models/__init__.py` - MODIFY: Export Planning_taches

### Frontend
- `modules/cheftech/PlanningTaskForm.tsx` - NEW: Task planning form page
- `modules/cheftech/PlanningTachesList.tsx` - NEW: List all task plannings
- `app/routing/AppRoutes.tsx` - MODIFY: Add routes
- `components/layout/Sidebar.tsx` - MODIFY: Add sidebar entry

---

## Tasks

### Task 1: Backend - Add Planning_taches Model Export

**Files:**
- Modify: `models/__init__.py:17`

- [ ] **Step 1: Add planning_taches import**

```python
from . import planning_taches
```

- [ ] **Step 2: Commit**

```bash
git add models/__init__.py
git commit -m "feat: add Planning_taches model export"
```

---

### Task 2: Backend - Add Task Schemas

**Files:**
- Modify: `modules/shared/routes/planning/schemas.py`

- [ ] **Step 1: Add task schemas at end of file**

```python
class TaskType(str, enum.Enum):
    DIAGNOSTIC = "DIAGNOSTIC"
    CORRECTION = "CORRECTION"


class PlanningTacheCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    description: str
    technician_id: int
    machine_id: int
    task_type: TaskType
    date_debut: datetime
    date_fin: datetime


class PlanningTacheUpdate(BaseModel):
    titre: str | None = Field(None, max_length=255)
    description: str | None = None
    technician_id: int | None = None
    machine_id: int | None = None
    task_type: TaskType | None = None
    date_debut: datetime | None = None
    date_fin: datetime | None = None


class PlanningTacheResponse(BaseModel):
    id: int
    planning_id: int
    titre: str
    description: str
    technician_id: int
    machine_id: int
    task_type: TaskType
    date_debut: datetime
    date_fin: datetime
    created_by: int | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlanningTacheListResponse(BaseModel):
    items: list[PlanningTacheResponse]
    total: int


class PlanningTachesSubmitRequest(BaseModel):
    tasks: list[PlanningTacheCreate]
```

- [ ] **Step 2: Commit**

```bash
git add modules/shared/routes/planning/schemas.py
git commit -m "feat: add planning_taches schemas"
```

---

### Task 3: Backend - Create Task CRUD Endpoints

**Files:**
- Create: `modules/shared/routes/planning/taches.py`

- [ ] **Step 1: Write task CRUD endpoints**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from models.utilisateurs import Utilisateurs
from models.plannings import Plannings, PlanningStatut
from models.planning_taches import Planning_taches
from models.planning_utilisateurs import Planning_utilisateurs
from models.planning_machines import Planning_machines
from models.machines import Machines
from .schemas import (
    PlanningTacheCreate,
    PlanningTacheUpdate,
    PlanningTacheResponse,
    PlanningTacheListResponse,
    PlanningTachesSubmitRequest,
)

router = APIRouter(prefix="/api/v1/plannings/{planning_id}/taches", tags=["planning-taches"])


def get_planning_or_404(planning_id: int, db: Session) -> Plannings:
    planning = db.query(Plannings).filter(Plannings.id == planning_id).first()
    if not planning:
        raise HTTPException(status_code=404, detail="Planning not found")
    return planning


def validate_task_dates(planning: Plannings, date_debut: datetime, date_fin: datetime):
    if date_debut < planning.date_debut:
        raise HTTPException(
            status_code=400,
            detail=f"Task start date must be >= planning start date ({planning.date_debut})"
        )
    if date_fin > planning.date_fin:
        raise HTTPException(
            status_code=400,
            detail=f"Task end date must be <= planning end date ({planning.date_fin})"
        )


@router.get("", response_model=PlanningTacheListResponse)
def list_tasks(
    planning_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """List all tasks for a planning."""
    tasks = db.query(Planning_taches).filter(
        Planning_taches.planning_id == planning_id
    ).all()
    return {"items": tasks, "total": len(tasks)}


@router.post("", response_model=list[PlanningTacheResponse])
def create_tasks(
    planning_id: int,
    request: PlanningTachesSubmitRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Create tasks and submit planning for approval."""
    planning = get_planning_or_404(planning_id, db)
    
    # Only CHEFTECH can create tasks
    if current_user.role != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Only CHEFTECH can create tasks")
    
    # Planning must be DRAFT
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add tasks to planning with status {planning.planning_statut.value}"
        )
    
    # Must have at least one task
    if not request.tasks:
        raise HTTPException(status_code=400, detail="At least one task is required")
    
    # Validate technician assignments
    assigned_user_ids = {pu.utilisateur_id for pu in planning.assigned_users} if planning.assigned_users else set()
    assigned_machine_ids = {pm.machine_id for pm in planning.machines} if planning.machines else set()
    
    created_tasks = []
    for task_data in request.tasks:
        # Validate dates are within planning range
        validate_task_dates(planning, task_data.date_debut, task_data.date_fin)
        
        # Validate technician is assigned to planning
        if task_data.technician_id not in assigned_user_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Technician {task_data.technician_id} is not assigned to this planning"
            )
        
        # Validate machine is assigned to planning
        if task_data.machine_id not in assigned_machine_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Machine {task_data.machine_id} is not assigned to this planning"
            )
        
        task = Planning_taches(
            planning_id=planning_id,
            titre=task_data.titre,
            description=task_data.description,
            technician_id=task_data.technician_id,
            machine_id=task_data.machine_id,
            task_type=task_data.task_type,
            date_debut=task_data.date_debut,
            date_fin=task_data.date_fin,
            created_by=current_user.id,
        )
        db.add(task)
        created_tasks.append(task)
    
    # Update planning status to SUBMITTED
    planning.planning_statut = PlanningStatut.SUBMITTED
    db.commit()
    
    for task in created_tasks:
        db.refresh(task)
    
    return created_tasks


@router.put("/{task_id}", response_model=PlanningTacheResponse)
def update_task(
    planning_id: int,
    task_id: int,
    request: PlanningTacheUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Update a task."""
    if current_user.role != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Only CHEFTECH can update tasks")
    
    task = db.query(Planning_taches).filter(
        Planning_taches.id == task_id,
        Planning_taches.planning_id == planning_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    planning = get_planning_or_404(planning_id, db)
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot edit tasks for non-DRAFT planning")
    
    if request.titre is not None:
        task.titre = request.titre
    if request.description is not None:
        task.description = request.description
    if request.technician_id is not None:
        task.technician_id = request.technician_id
    if request.machine_id is not None:
        task.machine_id = request.machine_id
    if request.task_type is not None:
        task.task_type = request.task_type
    if request.date_debut is not None or request.date_fin is not None:
        validate_task_dates(planning, request.date_debut or task.date_debut, request.date_fin or task.date_fin)
        if request.date_debut is not None:
            task.date_debut = request.date_debut
        if request.date_fin is not None:
            task.date_fin = request.date_fin
    
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    planning_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Delete a task."""
    if current_user.role != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Only CHEFTECH can delete tasks")
    
    task = db.query(Planning_taches).filter(
        Planning_taches.id == task_id,
        Planning_taches.planning_id == planning_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    planning = get_planning_or_404(planning_id, db)
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot delete tasks for non-DRAFT planning")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


@router.get("/all-with-taches")
def list_plannings_with_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """List all plannings that have tasks (for CHEFTECH task list view)."""
    # Get plannings that have at least one task
    planning_ids_with_tasks = db.query(Planning_taches.planning_id).distinct().all()
    planning_ids = [p[0] for p in planning_ids_with_tasks]
    
    plannings = db.query(Plannings).filter(Plannings.id.in_(planning_ids)).all()
    
    result = []
    for planning in plannings:
        task_count = db.query(Planning_taches).filter(
            Planning_taches.planning_id == planning.id
        ).count()
        
        result.append({
            "id": planning.id,
            "identifiant_planning": planning.identifiant_planning,
            "date_debut": planning.date_debut,
            "date_fin": planning.date_fin,
            "planning_statut": planning.planning_statut.value if planning.planning_statut else None,
            "task_count": task_count,
        })
    
    return {"items": result, "total": len(result)}
```

- [ ] **Step 2: Add router import to planning/__init__.py (create empty file if needed)**

```bash
echo "# planning routes" > modules/shared/routes/planning/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add modules/shared/routes/planning/taches.py modules/shared/routes/planning/__init__.py
git commit -m "feat: add planning_taches CRUD endpoints"
```

---

### Task 4: Backend - Include Router in Main App

**Files:**
- Modify: Need to find where routers are included

- [ ] **Step 1: Find how to include the router (check main.py)**

```bash
grep -r "include_router.*planning" app/backend/
```

- [ ] **Step 2: Add router - typically in modules/__init__.py or similar**

```python
# Add to the modules package that auto-includes routers
from modules.shared.routes.planning.taches import router as planning_taches_router
# Then include in app
```

Note: This depends on existing structure. May need to add to existing planning router file.

- [ ] **Step 3: Commit**

```bash
git add <modified files>
git commit -m "feat: include planning_taches router"
```

---

### Task 5: Frontend - Add PlanningTaskForm Component

**Files:**
- Create: `modules/cheftech/PlanningTaskForm.tsx`

- [ ] **Step 1: Create task planning form component**

```tsx
import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
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
  reference: string;
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
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [dateError, setDateError] = useState<string | null>(null);
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
      setPlanning(data);
      
      // Fetch existing tasks
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
    // Validate all tasks
    for (let i = 0; i < tasks.length; i++) {
      const task = tasks[i];
      const error = validateDates(task);
      if (error) {
        setDateError(error);
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
      {/* Header */}
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
                  <Label className="text-slate-300">Machine *</Label>
                  <Select value={task.machine_id?.toString() || ''} onValueChange={(v) => updateTask(index, 'machine_id', parseInt(v))}>
                    <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                      <SelectValue placeholder="Select machine" />
                    </SelectTrigger>
                    <SelectContent>
                      {planning.machines?.map((mach: Machine) => (
                        <SelectItem key={mach.id} value={mach.id.toString()}>{mach.nom} ({mach.reference})</SelectItem>
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
                    className="bg-slate-800 border-slate-600 text-white"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-slate-300">End Date/Time *</Label>
                  <Input
                    type="datetime-local"
                    value={task.date_fin}
                    onChange={(e) => updateTask(index, 'date_fin', e.target.value)}
                    className="bg-slate-800 border-slate-600 text-white"
                  />
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

      {/* Footer Actions */}
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
```

- [ ] **Step 2: Commit**

```bash
git add modules/cheftech/PlanningTaskForm.tsx
git commit -m "feat: add planning task form component"
```

---

### Task 6: Frontend - Add PlanningTachesList Component

**Files:**
- Create: `modules/cheftech/PlanningTachesList.tsx`

- [ ] **Step 1: Create task list component**

```tsx
import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Eye, List } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { AppPagination } from '@/components/shared/AppPagination';

interface PlanningWithTasks {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  planning_statut: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  task_count: number;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  DRAFT: { label: 'Brouillon', className: 'bg-gray-100 text-gray-800' },
  SUBMITTED: { label: 'Soumis', className: 'bg-yellow-100 text-yellow-800' },
  APPROVED: { label: 'Approuvé', className: 'bg-green-100 text-green-800' },
  REJECTED: { label: 'Rejeté', className: 'bg-red-100 text-red-800' },
};

export default function PlanningTachesList() {
  const [plannings, setPlannings] = useState<PlanningWithTasks[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlannings();
  }, []);

  const fetchPlannings = async () => {
    try {
      setLoading(true);
      const response = await client.apiCall.invoke({
        url: '/api/v1/plannings/all-with-taches',
        method: 'GET',
      });
      const data = response?.data || response;
      setPlannings(data?.items || []);
    } catch (error: any) {
      toast({ title: 'Error', description: 'Failed to load task plannings', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status?: string) => {
    if (!status) return null;
    const config = STATUS_CONFIG[status] || { label: status, className: 'bg-blue-100 text-blue-800' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getDuration = (dateDebut: string, dateFin: string) => {
    const diff = Math.abs(new Date(dateFin).getTime() - new Date(dateDebut).getTime());
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    return `${days} day${days !== 1 ? 's' : ''}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-4xl font-bold text-white">Tâches de Planning</h2>
        <p className="mt-1 text-sm text-blue-300">View all planning task executions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-blue-300">No task plannings found</p>
          </div>
        ) : (
          plannings.map((planning) => (
            <Card key={planning.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{planning.identifiant_planning}</CardTitle>
                    <p className="text-sm text-blue-300 mt-1">
                      {getDuration(planning.date_debut, planning.date_fin)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {getStatusBadge(planning.planning_statut)}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <List className="h-4 w-4 text-blue-400" />
                    <span className="text-blue-300">Tasks:</span>
                    <span className="font-medium">{planning.task_count}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-blue-400" />
                    <div>
                      <p className="text-blue-300">Period</p>
                      <p className="font-medium">
                        {new Date(planning.date_debut).toLocaleDateString('fr-FR')} - {new Date(planning.date_fin).toLocaleDateString('fr-FR')}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/cheftech/planning/${planning.id}/tasks`)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    View Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add modules/cheftech/PlanningTachesList.tsx
git commit -m "feat: add planningtaches list component"
```

---

### Task 7: Frontend - Add Routes

**Files:**
- Modify: `app/routing/AppRoutes.tsx`

- [ ] **Step 1: Add imports**

```tsx
import PlanningTaskForm from '@/modules/cheftech/PlanningTaskForm';
import PlanningTachesList from '@/modules/cheftech/PlanningTachesList';
```

- [ ] **Step 2: Add routes after CHEFTECH planning route**

```tsx
{/* Task Planning Form */}
<Route
  path="/cheftech/planning/:planningId/tasks"
  element={
    <ProtectedRoute allowedRoles={['CHEFTECH']}>
      <Layout>
        <PlanningTaskForm />
      </Layout>
    </ProtectedRoute>
  }
}
/>

{/* Task Plannings List */}
<Route
  path="/cheftech/plannings-taches"
  element={
    <ProtectedRoute allowedRoles={['CHEFTECH']}>
      <Layout>
        <PlanningTachesList />
      </Layout>
    </ProtectedRoute>
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add app/routing/AppRoutes.tsx
git commit -m "feat: add task planning routes"
```

---

### Task 8: Frontend - Add Sidebar Entry

**Files:**
- Modify: `components/layout/Sidebar.tsx`

- [ ] **Step 1: Find CHEFTECH section and add new entry**

In the CHEFTECH navigation items, add:

```tsx
{
  name: 'Tâches de Planning',
  path: '/cheftech/plannings-taches',
  icon: ListTodo,
}
```

- [ ] **Step 2: Add import if needed**

```tsx
import { ListTodo } from 'lucide-react';
```

- [ ] **Step 3: Commit**

```bash
git add components/layout/Sidebar.tsx
git commit -m "feat: add Tâches de Planning sidebar entry"
```

---

### Task 9: Frontend - Modify CheftechPlanning to Navigate to Task Form

**Files:**
- Modify: `modules/cheftech/CheftechPlanning.tsx`

- [ ] **Step 1: Find "Soumettre pour approbation" button and change onClick**

Change from:
```tsx
onClick={() => handleSubmitForApproval(planning.id)}
```

To navigate to task form:
```tsx
onClick={() => navigate(`/cheftech/planning/${planning.id}/tasks`)}
```

- [ ] **Step 2: Remove the API call handleSubmitForApproval function if no longer needed**

- [ ] **Step 3: Commit**

```bash
git add modules/cheftech/CheftechPlanning.tsx
git commit -m "feat: navigate to task form instead of direct submit"
```

---

### Task 10: Build and Test

- [ ] **Step 1: Build frontend**

```bash
docker compose build frontend
```

- [ ] **Step 2: Restart containers**

```bash
docker compose up -d
```

- [ ] **Step 3: Test manually**
- Login as CHEFTECH
- Navigate to Planning page
- Click "Soumettre" on a DRAFT planning
- Verify it navigates to task form
- Add tasks and submit
- Check sidebar shows "Tâches de Planning"
- Verify list shows plannings with tasks