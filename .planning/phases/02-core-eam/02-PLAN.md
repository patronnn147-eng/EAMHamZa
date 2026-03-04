---
phase: 02-core-eam
plan: '01'
type: execute
wave: '1'
depends_on: []
files_modified:
  - app/backend/modules/shared/machines.py
  - app/backend/modules/shared/ordres.py
  - app/backend/modules/shared/plannings.py
  - app/backend/modules/shared/ordres_intervention.py
  - app/frontend/src/modules/shared/machines/
  - app/frontend/src/modules/shared/work-orders/
  - app/frontend/src/modules/shared/PlanningCalendarView.tsx
autonomous: true
requirements:
  - EAM-01
  - EAM-02
  - EAM-03
user_setup: []

must_haves:
  truths:
    - Admins can create, read, update, delete machines
    - Work orders can be created and assigned to technicians
    - Plannings can be created and linked to machines/work orders
    - Interventions can be tracked through their lifecycle
    - Role-based access controls access appropriately
  artifacts:
    - path: app/backend/modules/shared/machines.py
      provides: Machine CRUD endpoints
    - path: app/backend/modules/shared/ordres.py
      provides: Order management endpoints
    - path: app/backend/modules/shared/plannings.py
      provides: Planning and scheduling endpoints
    - path: app/frontend/src/modules/shared/machines/
      provides: Machine management UI
    - path: app/frontend/src/modules/shared/work-orders/
      provides: Work order management UI
  key_links:
    - from: app/frontend/src/modules/shared/machines/
      to: app/backend/modules/shared/machines.py
      via: API calls
      pattern: client.entities.machines
    - from: app/frontend/src/modules/shared/work-orders/
      to: app/backend/modules/shared/ordres.py
      via: API calls
      pattern: client.entities.ordres
---

<objective>
Verify and enhance Core EAM Features: machines, work orders, planning, and interventions. Ensure all CRUD operations work, frontend-backend integration is complete, and role-based access is properly enforced.
</objective>

<context>
@.planning/phases/02-core-eam/02-CONTEXT.md
@.planning/phases/02-core-eam/02-RESEARCH.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify Machine Management</name>
  <files>app/backend/modules/shared/machines.py, app/frontend/src/modules/shared/machines/</files>
  <action>
    Verify machine CRUD:
    1. List all machines (GET)
    2. Create new machine (POST)
    3. Update machine (PUT)
    4. Delete machine (DELETE)
    5. Check frontend components call correct endpoints
    6. Ensure role-based access is enforced
    
    Fix any missing endpoints or integrations.
  </action>
  <verify>
    <automated>Test API endpoints:
    curl http://localhost:8000/api/v1/machines
    (Should return machine list with auth)</automated>
  </verify>
  <done>Machine CRUD fully functional with role-based access</done>
</task>

<task type="auto">
  <name>Task 2: Verify Work Order Management</name>
  <files>app/backend/modules/shared/ordres.py, app/frontend/src/modules/shared/work-orders/</files>
  <action>
    Verify work order functionality:
    1. Create work order
    2. Assign to technician
    3. Update status (PENDING → IN_PROGRESS → COMPLETED)
    4. Link to machine
    5. Check frontend integration
    6. Ensure ChetOp can create, ChefTech can assign, Technician can update
    
    Fix any missing endpoints or integrations.
  </action>
  <verify>
    <automated>Test work order endpoints:
    curl http://localhost:8000/api/v1/ordres
    (Should return order list with auth)</automated>
  </verify>
  <done>Work order lifecycle fully functional with proper role access</done>
</task>

<task type="auto">
  <name>Task 3: Verify Planning System</name>
  <files>app/backend/modules/shared/plannings.py, app/frontend/src/modules/shared/PlanningCalendarView.tsx</files>
  <action>
    Verify planning functionality:
    1. Create planning with date range
    2. Link to machines
    3. Link to technicians
    4. View calendar with assignments
    5. Check frontend integration
    6. Ensure role-based access
    
    Fix any missing endpoints or integrations.
  </action>
  <verify>
    <automated>Test planning endpoints:
    curl http://localhost:8000/api/v1/plannings
    (Should return planning list with auth)</automated>
  </verify>
  <done>Planning system fully functional with calendar view</done>
</task>

<task type="auto">
  <name>Task 4: Verify Intervention Workflow</name>
  <files>app/backend/modules/shared/ordres_intervention.py</files>
  <action>
    Verify intervention workflow:
    1. ChetOp creates intervention request
    2. ChefTech approves/assigns
    3. Technician performs and updates status
    4. Completion reports
    5. Status notifications
    
    Fix any missing endpoints or workflow gaps.
  </action>
  <verify>
    <automated>Test intervention endpoints:
    curl http://localhost:8000/api/v1/interventions
    (Should return with proper role access)</automated>
  </verify>
  <done>Intervention workflow complete from request to completion</done>
</task>

</tasks>

<verification>
- All CRUD endpoints functional
- Frontend-backend integration complete
- Role-based access enforced on all endpoints
- Full user flow works (create → assign → complete)
</verification>

<success_criteria>
- Machines can be managed (CRUD)
- Work orders can be created, assigned, tracked
- Planning system works with calendar
- Interventions flow through lifecycle
- Role-based access properly enforced
</success_criteria>

<output>
After completion, create `.planning/phases/02-core-eam/02-01-SUMMARY.md`
</output>
