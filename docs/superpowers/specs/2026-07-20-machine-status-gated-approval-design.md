# Machine Status — Technician-Proposed, CHEFTECH-Gated Approval (Design Spec)

**Date:** 2026-07-20
**Branch:** `Phase_2`
**Status:** Approved (brainstorming) → ready for implementation plan

## Goal

The machine card's status badge (`Machines.statut` — "Opérationnelle" etc.) is
today a manually-edited field with no connection to work-order outcomes, even
though technicians already record `machine_status_after` when completing a
work order. Wire that up: when a technician completes a WO and states the
machine's resulting status, that becomes a **proposal**. It only takes effect
on `Machines.statut` once a CHEFTECH approves it. ADMIN has no action here —
they observe the approvals/rejections through the existing `AuditLogViewer`.

## Decisions (locked)

| Question | Decision |
|---|---|
| New status value | Add `FONCTIONNEMENT_RESTREINT` ("Fonctionnement restreint") as a 5th machine status, alongside existing `OPERATIONNELLE` / `EN_MAINTENANCE` / `EN_PANNE` / `HORS_SERVICE`. |
| Vocabulary | **Single shared enum.** WO-completion forms and the machine status badge use the exact same 5 values — no separate vocab, no mapping table. |
| Is `EN_MAINTENANCE` a completion outcome? | Yes — included as one of the 5 options a technician can select when completing a WO. |
| Approval gate | New dedicated table (mirrors the existing `parts_drafts.py` guarded-draft pattern), not a same-row `pending_statut` column — this app keeps an audit trail for every gated action (procurement drafts, anomaly verdicts, shadow logs); a single-column "last pending wins" approach would be the odd one out. |
| Who approves | **CHEFTECH only.** Not `verify_cheftech` (that helper actually also allows ADMIN and CHETOP — see Backend Architecture) — a dedicated strict-CHEFTECH guard. |
| Admin visibility | None dedicated. Approve/reject write an `AuditLog` row (`entity_type=MACHINE`), which already surfaces in the existing `AuditLogViewer.tsx` page (routed for ADMIN + CHEFTECH already). No new admin UI. |
| Multiple pending requests per machine | Not allowed. A new WO completion auto-supersedes (REJECTS, with a note) any existing PENDING request for that machine before creating the new one — "last technician's call" semantics, nothing deleted. |
| Dead endpoints `PUT .../machines/{id}/status` (cheftech + chetop) | Left untouched — unreachable from any frontend button today, out of scope. |

## High-Level Flow

1. Technician completes a WO (either completion dialog) and picks the
   machine's resulting status from the shared 5-value list.
2. Backend persists `intervention.machine_status_after` (unchanged, already
   exists) **and** creates a `machine_status_change_requests` row, `PENDING`,
   after auto-superseding any prior pending request for that machine.
   Non-fatal — a failure here never blocks WO completion.
3. CHEFTECH sees the new request in a dedicated queue page, with the machine
   name, requesting technician, current vs. proposed status, and a link to
   the source WO.
4. CHEFTECH clicks Approve → `Machines.statut` is set to the proposed value,
   request → `APPROVED`, an `AuditLog` row is written.
5. CHEFTECH clicks Reject (optional note) → request → `REJECTED`,
   `Machines.statut` unchanged, `AuditLog` row written.
6. ADMIN sees both outcomes later in the existing `AuditLogViewer`. No action
   available to ADMIN on this flow.

## Backend Architecture

### New table — `machine_status_change_requests`

```
machine_status_change_requests(
  id                     SERIAL PK,
  machine_id             INTEGER NOT NULL,            -- FK machines.id
  from_status            VARCHAR(30) NOT NULL,         -- snapshot of Machines.statut at request time
  to_status              VARCHAR(30) NOT NULL,         -- one of the 5 shared values
  status                 VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED
  source_intervention_id INTEGER,                      -- FK ordres_intervention.id, nullable
  requested_by           INTEGER,                      -- FK utilisateurs.id, nullable
  requested_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_by            INTEGER,                      -- FK utilisateurs.id, nullable
  reviewed_at            TIMESTAMPTZ,
  review_note            TEXT
)
-- Index on (machine_id, status) for the "does this machine already have a
-- pending request" lookup and for the queue page's PENDING filter.
```

- **Model:** `app/backend/models/machine_status_change_request.py`
  (`MachineStatusChangeRequest`, `RequestStatus` str-enum: `PENDING` /
  `APPROVED` / `REJECTED` — mirrors `OrdreStatut` style already used
  elsewhere).
- **Migration:** new Alembic revision under `app/backend/alembic/versions/`,
  `down_revision` = current head (resolve via `alembic heads` at
  implementation time). Table-exists guard mirrors the existing pattern used
  by prior additive migrations in this repo (e.g. `p7_parts_demand_col`).

### Shared status vocabulary — `app/backend/models/machine_status.py`

```python
MACHINE_STATUSES = [
    "OPERATIONNELLE",
    "FONCTIONNEMENT_RESTREINT",
    "EN_MAINTENANCE",
    "EN_PANNE",
    "HORS_SERVICE",
]
```

Plain list, not a DB-level enum/constraint — `Machines.statut` and
`OrdresIntervention.machine_status_after` are both unconstrained `String`
columns today (confirmed in `models/machines.py` and
`models/ordres_intervention.py`); no migration needed to add the new value,
only to validate against it in the new Pydantic payload and in `to_status`
before creating a request. Used by the request-creation service and by the
WO-completion payload schemas (`WorkOrderCompletePayload.machine_status_after`
etc.) for a simple membership check — `400` if the technician-submitted value
isn't one of the 5.

### New service — `app/backend/modules/shared/services/machine_status_requests.py`

Mirrors `modules/ml/services/parts_drafts.py`'s shape:

```python
async def create_status_change_request(
    machine_id: int,
    to_status: str,
    requested_by: Optional[int],
    source_intervention_id: Optional[int],
    db: AsyncSession,
) -> Optional[int]:
    """
    No-op (returns None) if to_status equals the machine's current statut —
    nothing to propose. Otherwise: supersede any existing PENDING request for
    this machine (→ REJECTED, review_note="Superseded by newer request"),
    then insert a new PENDING row with from_status = machine.statut (current,
    pre-change). Caller commits.
    """

async def approve_status_change_request(
    request_id: int, approved_by: int, db: AsyncSession,
) -> Dict[str, Any]:
    """PENDING → APPROVED. Sets Machines.statut = to_status. Writes AuditLog
    (entity_type=MACHINE, old={'statut': from_status}, new={'statut': to_status}).
    404 if not found, 400 if not PENDING (mirrors parts_drafts.py's guard style)."""

async def reject_status_change_request(
    request_id: int, rejected_by: int, note: Optional[str], db: AsyncSession,
) -> Dict[str, Any]:
    """PENDING → REJECTED. Machines.statut untouched. Writes AuditLog
    (action=UPDATE, entity_type=MACHINE, entity_id=machine_id,
    old_values={'request_status': 'PENDING', 'proposed_statut': to_status},
    new_values={'request_status': 'REJECTED', 'proposed_statut': to_status,
    'review_note': note or ''}) — `statut` itself is deliberately NOT in
    old/new here (it doesn't change on reject; log_update() only records a
    diff for keys whose value differs, so passing identical 'statut' on both
    sides would produce an empty, useless changes entry). 404 / 400 as above."""

async def list_pending_requests(db: AsyncSession) -> List[Dict[str, Any]]:
    """Joined with Machines (name) and Utilisateurs (requester name) for the
    CHEFTECH queue page. Ordered oldest-first."""
```

### WO-completion wiring (both paths, same call)

- `app/backend/modules/technicien/technicien_work_orders.py`,
  `_update_intervention_fields()` — right after
  `intervention.machine_status_after = payload.machine_status_after`, if a
  value was provided:
  ```python
  try:
      await create_status_change_request(
          machine_id=wo.machine_id,
          to_status=payload.machine_status_after,
          requested_by=technician_id,
          source_intervention_id=intervention.id,
          db=db,
      )
  except Exception:
      logger.warning("Machine status change request failed for WO %s", order_id)
  ```
  Non-fatal — matches the existing `_try_audit_complete` / recovery-snapshot
  try/except style in the same file. Does not call `db.commit()` itself; rides
  the same transaction as the rest of WO completion.
- `app/backend/modules/chetop/routes/work_orders.py`, same call at the
  equivalent point (line ~183, right after
  `intervention.machine_status_after = payload.machine_status_after`).

### New router — `app/backend/modules/cheftech/routes/machine_status_requests.py`

```python
router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])
```

Auto-discovered by `include_routers_from_package(app, "modules")` in
`main.py` — no manual registration needed, same as every other
`modules/cheftech/routes/*.py` file.

- `GET /api/v1/cheftech/machine-status-requests?status=PENDING` — list, joined
  view from `list_pending_requests`.
- `PATCH /api/v1/cheftech/machine-status-requests/{id}/approve`
- `PATCH /api/v1/cheftech/machine-status-requests/{id}/reject` — optional
  `{"note": str}` body.

**Role guard — new, strict, not `verify_cheftech`:**
`modules/cheftech/dependencies.py`'s `verify_cheftech` actually delegates to
`verify_management_access`, which also allows `ADMIN` and `CHETOP` — wrong
for this feature, where ADMIN must have zero action. Add a new dependency in
the same file:

```python
def verify_cheftech_only(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role != UserRole.CHEFTECH:
        raise HTTPException(status_code=403, detail="Réservé au chef technicien.")
    return current_user
```

All three new endpoints depend on `verify_cheftech_only`.

## Frontend

### Shared vocabulary — `lib/constants.ts`

```ts
export const MACHINE_STATUS_OPTIONS = [
  { value: 'OPERATIONNELLE', label: 'Opérationnelle' },
  { value: 'FONCTIONNEMENT_RESTREINT', label: 'Fonctionnement restreint' },
  { value: 'EN_MAINTENANCE', label: 'En Maintenance' },
  { value: 'EN_PANNE', label: 'En Panne' },
  { value: 'HORS_SERVICE', label: 'Hors Service' },
];
```

### Unify the two completion dialogs

- `modules/technicien/components/WorkOrderCompleteDialog.tsx` — delete its
  local `MACHINE_STATUS_OPTIONS` (currently `OPERATIONAL/DEGRADED/STOPPED/
  SCRAP`), import the shared one from `lib/constants.ts`, update the default
  `useState` from `'OPERATIONAL'` to `'OPERATIONNELLE'`.
- `modules/shared/CompleteWorkOrderModal.tsx` — replace its inline
  `SelectItem`s (`EN_MARCHE/ARRETEE/FONCTIONNEMENT_RESTREINT`) with a map over
  the shared `MACHINE_STATUS_OPTIONS`, update the two `machine_status_after:
  'EN_MARCHE'` defaults to `'OPERATIONNELLE'`.

### Status badge maps — add the 5th entry

Five files carry a local `{ label, dot/className }` map keyed by
`Machines.statut`, all needing one new `FONCTIONNEMENT_RESTREINT` entry
(amber, matching the existing amber used for `EN_MAINTENANCE` in most of
these — pick a visually distinct shade, e.g. amber-600 vs amber-500, so the
two aren't confusable):

- `modules/admin/machines/components/AdminMachinesGrid.tsx`
- `modules/technicien/TechnicianMachines.tsx`
- `modules/chetop/ChetopMachines.tsx`
- `modules/cheftech/machines/components/ChefTechMachinesGrid.tsx`
- `modules/shared/MachineDetailPage.tsx` (also add a matching
  `<SelectItem value="FONCTIONNEMENT_RESTREINT">` to its manual-edit status
  dropdown, next to the existing `OPERATIONNELLE` one at line 425)

### New page — CHEFTECH-only review queue

- `modules/cheftech/MachineStatusRequestsPage.tsx` (name to match sibling
  page components, e.g. `ChefTechAlertWorkflow.tsx`'s pattern) — table:
  Machine | Requested by | Current status | Proposed status | WO link |
  Approve / Reject buttons. Reject opens a small inline note field (optional)
  before confirming.
- Route: `/cheftech/machine-status-requests`, `ProtectedRoute
  allowedRoles={['CHEFTECH']}` — CHEFTECH only, matching the "admin has no
  action" decision (contrast with the existing `/audit-log` route, which is
  `['ADMIN', 'CHEFTECH']`).
- Sidebar: new entry under the existing CHEFTECH section in
  `components/layout/Sidebar.tsx` (alongside `Centre des alertes` etc.),
  e.g. `{ name: 'Changements de statut', href: '/cheftech/machine-status-requests', icon: RefreshCw }`.
- On Approve/Reject success, refetch the list (row disappears from the
  PENDING view) and toast confirmation.

## Error Handling

- Request creation during WO completion: non-fatal, logged and swallowed —
  WO completion is the critical path, the proposal is secondary.
- `to_status` not in `MACHINE_STATUSES`: `400` at the WO-completion payload
  validation layer, before any DB write.
- Approve/reject on a non-existent request: `404`.
- Approve/reject on an already-reviewed request: `400` (mirrors
  `parts_drafts.py`'s `"WO is not a draft (status: …)"` message style).
- Approve/reject by non-CHEFTECH: `403` via `verify_cheftech_only`.

## Testing

- **Backend unit (no DB):** `MACHINE_STATUSES` membership validation.
- **Backend integration:**
  - WO completion with `machine_status_after` set → PENDING request created,
    `from_status` correctly snapshots the pre-change `Machines.statut`.
  - Second WO completion for the same machine while a request is still
    PENDING → old request → REJECTED with supersede note, new PENDING
    request created.
  - Approve → `Machines.statut` updated, request → APPROVED, `AuditLog` row
    present with correct old/new values.
  - Reject → `Machines.statut` unchanged, request → REJECTED, `AuditLog` row
    present.
  - Approve/reject on already-reviewed request → `400`.
  - Approve/reject as non-CHEFTECH (ADMIN, CHETOP, TECHNICIEN) → `403`.
  - `to_status` equal to current `Machines.statut` → no request created
    (no-op).
- **Frontend (manual, via browser preview):** completion dialogs show the
  unified 5-option list; CHEFTECH queue page lists a pending request end to
  end; approve/reject updates the machine card status; ADMIN cannot reach
  `/cheftech/machine-status-requests` (redirected/blocked) and instead sees
  the event in `AuditLogViewer`.

## Assumptions

1. `Machines.statut` and `OrdresIntervention.machine_status_after` staying
   unconstrained `String` columns (no DB-level CHECK/enum) is acceptable —
   validation lives in the application layer via `MACHINE_STATUSES`.
2. One pending request per machine is sufficient; no need to queue multiple
   simultaneous proposals from different technicians.
3. `AuditLogViewer` (existing, already showing `entity_type=MACHINE` updates
   from other flows) is sufficient ADMIN-facing visibility — no new admin
   page.
4. CHEFTECH is a single flat role for this feature — no per-zone or
   per-machine CHEFTECH assignment/routing.

## Out of Scope

- Fixing the two dead `PUT /machines/{id}/status` endpoints
  (`cheftech/routes/resources.py`, `chetop/routes/machines.py`) — left as-is,
  confirmed unreachable from any frontend button.
- Notifications (push/email) to CHEFTECH when a new request lands — the queue
  page is pull-based for now, same as the existing procurement queue.
- Bulk approve/reject.
