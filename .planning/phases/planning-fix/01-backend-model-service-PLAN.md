# 01-backend-model-service-PLAN.md
---
phase: planning-fix
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/backend/models/plannings.py
  - app/backend/services/plannings.py
autonomous: true
must_haves:
  truths:
    - "API returns technician users in `assigned_users`"
    - "API returns machine IDs in `machine_ids`"
  artifacts:
    - path: "app/backend/models/plannings.py"
      provides: "relationship definitions"
    - path: "app/backend/services/plannings.py"
      provides: "eager-loaded get_by_id"
  key_links:
    - from: "PlanningsService.get_by_id"
      to: "Plannings.planning_utilisateurs"
      via: "selectinload"
    - from: "PlanningsService.get_by_id"
      to: "Plannings.planning_machines"
      via: "selectinload"
---
<objective>
Add eager‑loading of the bridge tables so that the ORM returns full assignment data.
Purpose: Technicians and machines are currently omitted because the query does not load related tables.
Output: `PlanningsService.get_by_id` returns populated `planning_utilisateurs` and `planning_machines` collections.
</objective>
<tasks>
<task type="auto">
  <name>Task 1: Add eager‑loading to `get_by_id`</name>
  <files>app/backend/services/plannings.py</files>
  <action>
    Replace the simple `select(Plannings).where(Plannings.id == obj_id)` query with:
    ```python
    query = select(Plannings).options(
        selectinload(Plannings.planning_utilisateurs).selectinload(Planning_utilisateurs.utilisateur),
        selectinload(Plannings.planning_machines)
    ).where(Plannings.id == obj_id)
    ```
    Keep surrounding try/except unchanged.
  </action>
  <verify>
    <automated>pytest tests/backend/test_plannings_service.py::test_get_by_id_eager -q</automated>
  </verify>
  <done>`get_by_id` returns a `Plannings` instance where `planning_utilisateurs` and `planning_machines` are populated.</done>
</task>
<task type="auto">
  <name>Task 2: Ensure relationships are defined</name>
  <files>app/backend/models/plannings.py</files>
  <action>
    Verify that the two relationships (`planning_utilisateurs` and `planning_machines`) already exist (they do) and that `lazy="noload"` is kept – the eager‑load is performed in the service, not the model.
    No code change required; just confirm the model file is present.
  </action>
  <verify>
    <automated>grep -n "planning_utilisateurs" -R app/backend/models/plannings.py</automated>
  </verify>
  <done>Model defines the two relationships and they are usable by the service.</done>
</task>
</tasks>
<verification>
Run the unit test suite; all tests must pass and the log must show the eager‑loaded collections.
</verification>
<success_criteria>
`GET /api/v1/entities/plannings/{id}` now includes full technician entries and an array of machine IDs.
</success_criteria>
<output>
Create `.planning/phases/planning-fix/01-backend-model-service/SUMMARY.md` summarising the changes.
</output>