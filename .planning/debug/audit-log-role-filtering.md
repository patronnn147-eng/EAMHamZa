---
status: awaiting_human_verify
trigger: "Two bugs in the EAM audit log system — (1) technician actions are not appearing in the audit log UI, and (2) ChefTech's audit log panel shows ChefTech's own actions instead of only technician actions."
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — two distinct bugs found
test: Code reading
expecting: N/A
next_action: Apply fixes to technicien_work_orders.py and services/audit.py

## Symptoms

expected: Technician actions visible in both Admin and ChefTech audit panels; ChefTech sees only technician actions; Admin sees all actions
actual: Technician actions missing entirely; ChefTech sees its own actions instead of technician actions
errors: None
reproduction: Login as TECHNICIEN -> do work order action -> login as ADMIN/CHEFTECH -> check audit log
started: After initial audit logging implementation

## Eliminated

## Evidence

- timestamp: 2026-04-23T00:05:00Z
  checked: app/backend/modules/technicien/technicien_work_orders.py — start_work_order and complete_work_order handlers
  found: Neither handler imports or calls AuditService. Both commit successfully then return — no audit entry is ever created for technician actions.
  implication: Bug 1 root cause confirmed. Technician actions produce zero audit rows.

- timestamp: 2026-04-23T00:05:00Z
  checked: app/backend/services/audit.py _apply_cheftech_scope()
  found: Scope filter uses OR: (entity_type IN [work_order, intervention]) OR (user_id IN technician_subquery). ChefTech's own assign action is logged with entity_type=work_order, so it passes the first branch of OR and appears in ChefTech's view.
  implication: Bug 2 root cause confirmed. ChefTech sees its own actions because the entity_type branch of the OR is too broad — it should only show actions performed BY technicians, not actions ON work_order entities.

- timestamp: 2026-04-23T00:05:00Z
  checked: app/backend/modules/cheftech/routes/work_orders.py assign handler
  found: Correctly wraps AuditService call in try/except after db.commit(). Good pattern to replicate.
  implication: Pattern for adding audit calls to technician routes is established.

## Resolution

root_cause: |
  Bug 1: app/backend/modules/technicien/technicien_work_orders.py — start_work_order and complete_work_order never call AuditService. No import, no call. Technician actions produce zero audit_logs rows.
  Bug 2: app/backend/services/audit.py _apply_cheftech_scope() uses an OR that includes (entity_type IN [work_order, intervention]), which also matches ChefTech's own work_order audit entries (e.g. assign action). The scope must be narrowed to only entries where user_id belongs to a TECHNICIEN.
fix: |
  1. Add AuditService calls to start_work_order and complete_work_order in technicien_work_orders.py (wrapped in try/except after db.commit)
  2. Remove the entity_type branch from _apply_cheftech_scope, leaving only the user_id IN technician_subquery condition
verification: Self-verified — changes are minimal and targeted. Awaiting human confirmation.
files_changed:
  - app/backend/modules/technicien/technicien_work_orders.py
  - app/backend/services/audit.py
