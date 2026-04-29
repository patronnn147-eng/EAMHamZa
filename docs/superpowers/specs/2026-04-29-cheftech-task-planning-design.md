# CHEFTECH Task-Level Planning Design

## Overview
Allow CHEFTECH to create detailed execution plans (tasks) for DRAFT plannings before submitting for approval.

## User Flow
1. CHEFTECH views plannings at `/cheftech/planning`
2. Clicks "Soumettre pour approbation" on a DRAFT planning
3. Navigates to `/cheftech/planning/{planningId}/tasks`
4. Creates tasks with assigned technicians and machines
5. Submits → tasks saved + planning status changes DRAFT → SUBMITTED

## Backend

### Database
- `Planning_taches` model exists with fields: id, planning_id, titre, description, technician_id, machine_id, task_type, date_debut, date_fin, created_by, created_at
- `TaskType` enum: DIAGNOSTIC, CORRECTION

### API Endpoints
```
POST /api/v1/plannings/{id}/submit  (existing - updates status)
GET  /api/v1/plannings/{id}/taches (list tasks for planning)
POST /api/v1/plannings/{id}/taches (create tasks + submit planning)
PUT  /api/v1/plannings/{id}/taches/{taskId} (update task)
DELETE /api/v1/plannings/{id}/taches/{taskId} (delete task)
GET  /api/v1/plannings/taches (list all plannings with tasks for CHEFTECH)
```

### Validation
- Task date_debut >= planning.date_debut
- Task date_fin <= planning.date_fin
- At least 1 task required before submission

## Frontend

### New Pages
1. **Task Planning Form** - `/cheftech/planning/:planningId/tasks`
   - Shows planning info (read-only)
   - Dynamic task cards with add/remove
   - Dropdowns filtered to planning's assigned users + machines
   - Date validation: must be within planning date range

2. **Task Plannings List** - `/cheftech/plannings-taches`
   - Cards showing: Planning ID, task count, status, date range
   - View Details button → task details page

### Sidebar
- New entry for CHEFTECH: "Tâches de Planning" → `/cheftech/plannings-taches`

## Permissions
- CHEFTECH: create/edit tasks, submit planning
- ADMIN: view only (no task creation)

## Validation Rules
- Task title: required, 255 max chars
- Description: required
- Technician: required, must be in planning.assigned_users
- Machine: required, must be in planning.machines
- Task type: required (DIAGNOSTIC/CORRECTION)
- Start/End datetime: required, must be within original planning dates