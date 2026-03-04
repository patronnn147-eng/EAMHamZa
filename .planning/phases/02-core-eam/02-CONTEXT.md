# Phase 2: Core EAM Features - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning
**Source:** Codebase analysis

---

<domain>
## Phase Boundary

Implement core Enterprise Asset Management features:
- Machine CRUD and management
- Work orders creation and lifecycle
- Planning and scheduling
- Intervention management

**Existing codebase:** Models exist in `app/backend/models/`, modules in `app/backend/modules/shared/`, frontend in `app/frontend/src/modules/shared/`

</domain>

<decisions>
## Implementation Decisions

### Machine Management
- **Machine model:** Already exists in `models/machines.py`
- **API endpoints:** Use existing `modules/shared/machines.py`
- **Frontend:** Use existing `modules/shared/machines/` components

### Work Orders
- **Models:** Already exist - `ordres.py`, `ordres_travail.py`, `ordres_intervention.py`
- **API:** Use existing services in `modules/shared/`
- **Frontend:** Dashboard components already exist

### Planning System
- **Models:** Already exist - `plannings.py`, `planning_machines.py`, `planning_utilisateurs.py`
- **Calendar view:** Frontend has `PlanningCalendarView.tsx`
- **API:** Use existing modules

### Interventions
- **Intervention workflow:** ChetOp creates, Technician performs, ChefTech approves
- **Status flow:** PENDING → IN_PROGRESS → COMPLETED/REJECTED

</decisions>

<specifics>
## Specific Ideas

**From existing code:**
- `app/backend/models/machines.py` - Machine model
- `app/backend/models/ordres.py` - Order model
- `app/backend/models/ordres_intervention.py` - Intervention model
- `app/backend/models/plannings.py` - Planning model
- `app/backend/modules/shared/machines.py` - Machine API
- `app/backend/modules/shared/ordres.py` - Order API
- `app/backend/modules/shared/plannings.py` - Planning API
- `app/frontend/src/modules/shared/machines/` - Machine UI
- `app/frontend/src/modules/shared/work-orders/` - Work order UI
- `app/frontend/src/modules/shared/PlanningCalendarView.tsx` - Calendar

**User roles for EAM:**
- ADMIN: Full access
- CHEFTECH: Assign technicians, view all, approve interventions
- CHETOP: Create work orders, view plannings
- TECHNICIEN: Perform interventions, update status

</specifics>

<deferred>
## Deferred Ideas

- Advanced scheduling algorithms (future phase)
- Multi-machine maintenance planning (future phase)
- Resource optimization (future phase)

</deferred>

---

*Phase: 02-core-eam*
*Context gathered: 2026-03-04*
