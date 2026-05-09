# Phase 12: ChefTech Alert Response Workflow page - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a dedicated ChefTech alert triage page at `/cheftech/alerts` with a 3-swimlane layout implementing the D+A workflow: CRITICAL/HIGH alerts auto-escalate to ChefTech lane, MEDIUM/LOW sit in System review queue, assigned alerts move to Technician Execution lane. ChefTech can assign technicians, create work orders, and dismiss alerts from this page.

**NOT in scope:** Modifying existing `/alerts` flat list page, notification system, new alert types, mobile-specific layout.

</domain>

<decisions>
## Implementation Decisions

### Alert Card Content
- Full info on every card: severity badge (color-coded) + machine name with ID + 1-line message + RUL days (if available) + failure probability bar + timestamp (relative)
- Alert type pill (RUL ALERT / FAILURE PREDICTION / ANOMALY) — hidden on card, visible only in triage panel
- Machine shown as name: `Convoyeur B-72 (#42)` format — requires machines API call
- Failure probability shown as inline progress bar + % value on card

### Post-Assign Behavior
- After "Assign & Notify": card moves immediately (optimistic) from ChefTech Triage lane to Technician Execution lane
- After "Dismiss Alert": card fades out with 3-second undo window, then permanently removed
- Triage panel auto-closes after both actions
- Technician lane cards ARE clickable — edit button opens triage panel in edit mode
- Technician availability check: when ChefTech selects a tech in dropdown, check if tech has open work orders — show warning icon on tech option + inline error message if occupied. ChefTech can still force-assign or pick different tech.

### Page Access & Navigation
- New separate route: `/cheftech/alerts` — does NOT replace existing `/alerts`
- Access: CHEFTECH role only
- Sidebar: add new entry "Centre des alertes" (with Bell icon) alongside existing "Alertes Prédictives" entry in CHEFTECH nav block
- Existing "Alertes Prédictives" → `/alerts` remains unchanged

### Empty Lane States
- ChefTech Triage lane empty: green checkmark icon + "Aucune alerte critique" — positive all-clear signal
- System (Auto) lane empty: subtle minimal text "Aucune alerte en attente" — no celebratory treatment (lower urgency)
- Technician Execution lane empty: left-pointing arrow + "Assignez depuis le triage" — onboarding hint
- All 3 lanes empty simultaneously: green banner at top of page "Système sain — Aucune alerte active"

### Claude's Discretion
- Exact swimlane column widths and proportions
- Loading skeleton design
- Triage panel slide-in animation speed
- Error state when API fails to load alerts
- Exact warning icon used for occupied technician

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `severityConfig` object in `app/frontend/src/modules/shared/AlertsPanel.tsx` (lines 37-82): colors, icons, border classes, badge classes for CRITICAL/HIGH/MEDIUM/LOW — copy or extract to shared util
- `Sheet` component at `app/frontend/src/components/ui/sheet.tsx` — use for slide-in triage panel (SheetContent, SheetHeader, SheetTitle)
- `Select`, `Button`, `Badge`, `Card`, `Checkbox` from `app/frontend/src/components/ui/` — all available
- `useToast` from `app/frontend/src/hooks/use-toast.ts` — use for undo dismiss toast with action button
- `useAuth` from `app/frontend/src/contexts/AuthContext.tsx` — current user id for dismiss API call
- `useNavigate` from `react-router-dom` — machine name click → `/machines/{id}`

### Established Patterns
- Dark theme colors: `bg-[#0f1623]`, `bg-[#131c2e]`, `border-white/[0.06]` — match existing AlertsPanel
- Auth: `localStorage.getItem('access_token')` for fetch headers
- Fetch pattern: direct `fetch()` calls with Bearer token (same as AlertsPanel.tsx lines 93-115)
- Current user: `client.auth.me()` returns `{data: {id, role, ...}}`

### API Endpoints
- `GET /api/v1/alerts` — fetch all active alerts (severity, machine_id, message, rul_days, failure_probability, is_linked_to_wo)
- `PATCH /api/v1/alerts/{id}/dismiss` — body: `{user_id}`
- `POST /api/v1/alerts/{id}/create-work-order` — body: `{created_by, assigned_to, priority, due_date, title?, description?}`
- `GET /api/v1/plannings/users/by-role/TECHNICIEN` — fetch technician list for assignment dropdown
- `GET /api/v1/ordres_travail?assigned_to={id}&statut=EN_COURS` — check technician open WOs for availability warning
- Machines name: use `client.entities.machines.query()` or `GET /api/v1/machines/{id}` to resolve names

### Integration Points
- `app/frontend/src/app/routing/AppRoutes.tsx` — add route `/cheftech/alerts` with `allowedRoles={['CHEFTECH']}`
- `app/frontend/src/components/layout/Sidebar.tsx` — add "Centre des alertes" entry in CHEFTECH nav block (after "Alertes Prédictives" at line 82)
- New file: `app/frontend/src/modules/cheftech/ChefTechAlertWorkflow.tsx`

</code_context>

<specifics>
## Specific Ideas

- Swimlane logic is client-side from single `GET /api/v1/alerts` call:
  - System lane: severity MEDIUM or LOW + `is_linked_to_wo === false`
  - ChefTech Triage lane: severity CRITICAL or HIGH + `is_linked_to_wo === false`
  - Technician Execution lane: `is_linked_to_wo === true` (any severity)
- Technician availability: check open WOs when dropdown opens, not on every render
- "Assign & Notify" button calls `POST /api/v1/alerts/{id}/create-work-order` — the `assigned_to` field carries the technician assignment
- Undo dismiss: use `useToast` with an action button ("Annuler") that calls re-activate or just locally restores the alert before API dismiss fires

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-cheftech-alert-response-workflow-page*
*Context gathered: 2026-05-09*
