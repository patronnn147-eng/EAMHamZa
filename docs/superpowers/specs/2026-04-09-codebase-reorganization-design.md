# Codebase Reorganization Design

**Date:** 2026-04-09
**Goal:** Split all files exceeding 350 lines into focused sub-files. Consolidate the top-level `routers/` package into `modules/` for domain-driven ownership. Every resulting file stays under 350 lines.

---

## Constraints

- `components/ui/` (shadcn/ui auto-generated) — **untouched**
- `main.py` — **zero changes required** (auto-discovery already walks `modules/` recursively)
- All existing import paths used by other files must remain valid (re-exports where needed)
- Max 350 lines per file (strict upper bound)

---

## Backend

### Routing Consolidation

The top-level `routers/` package is eliminated. Every file moves into the relevant `modules/` sub-folder. Since `main.py` calls `include_routers_from_package(app, "modules")` which uses `pkgutil.walk_packages` recursively, any new file exposing a `router = APIRouter(...)` inside `modules/` is auto-discovered with no changes to `main.py`.

| From `routers/` | To `modules/` |
|---|---|
| `plannings.py` (922 lines) | `modules/shared/routes/planning/` (split into 2 files) |
| `notifications.py` (330 lines) | `modules/shared/routes/notifications.py` |
| `admin_users.py` (174 lines) | `modules/admin/routes/users.py` |
| `admin_analytics.py` (171 lines) | `modules/admin/routes/analytics.py` |
| `user_approvals.py` (236 lines) | `modules/admin/routes/approvals.py` |

### Module Splits

Each oversized module file is replaced by a `routes/` subfolder. Every sub-file declares its own `router = APIRouter(prefix="...", tags=[...])`.

#### `modules/cheftech/` (cheftech.py: 945 lines)
```
modules/cheftech/routes/
├── __init__.py
├── interventions.py    # /dashboard + /interventions endpoints (~280 lines)
├── work_orders.py      # /ordres-travail + /assign + /completed + /feedback (~310 lines)
└── analytics.py        # /techniciens + /machines + /kpi + /analytics/dashboard (~200 lines)
```
Original `cheftech_work_orders.py` (226 lines) stays as-is.

#### `modules/chetop/` (chetop.py: 534 lines)
```
modules/chetop/routes/
├── __init__.py
├── dashboard.py        # /dashboard endpoint
├── work_orders.py      # /work-orders CRUD + start/complete
├── interventions.py    # /intervention-requests
└── machines.py         # /machines GET + PUT status
```

#### `modules/technicien/` (technicien.py: 476 lines)
```
modules/technicien/routes/
├── __init__.py
├── machines.py         # /machines GET list
└── interventions.py    # /interventions GET/PUT status + POST request
```
Original `technicien_work_orders.py` (248 lines) stays as-is.

#### `modules/shared/` — machines (machines.py: 589 lines)
```
modules/shared/routes/machines/
├── __init__.py
├── crud.py             # GET list/all/by-id + POST + PUT + DELETE (~280 lines)
└── import_.py          # /import/template + /import/preview + /import/execute (~220 lines)
```

#### `modules/shared/` — planning (routers/plannings.py: 922 lines)
```
modules/shared/routes/planning/
├── __init__.py
├── planning_crud.py    # GET list + POST create + PUT update + DELETE (~280 lines)
└── planning_detail.py  # GET by id + GET machines + POST resend-emails (~220 lines)
```

#### `modules/shared/` — other oversized files
```
modules/shared/routes/
├── ordres_intervention_read.py   (split from ordres_intervention.py: 441 lines)
├── ordres_intervention_write.py
├── ordres_travail_read.py        (split from ordres_travail.py: 397 lines)
├── ordres_travail_write.py
├── planning_ordres_read.py       (split from planning_ordres_travail.py: 367 lines)
└── planning_ordres_write.py
```

#### `modules/ml/` (ml_predictive.py: 428 lines)
```
modules/ml/services/
├── prediction_engine.py    # core prediction logic
└── prediction_features.py  # feature extraction / preprocessing
```

#### Legacy cleanup
- `modules/shared/cheftech_old.py` (423 lines) — check imports; delete if unreferenced.

### Services Splits

| Original | Split into |
|---|---|
| `services/payment.py` (419 lines) | `services/payment/core.py` + `services/payment/stripe_service.py` |
| `services/inventory.py` (350 lines) | `services/inventory/read.py` + `services/inventory/write.py` |

Each split folder gets an `__init__.py` that re-exports the public API so existing `from services.payment import X` imports continue to work.

---

## Frontend

**Strategy:** Large page/component files become thin orchestrators. Logic is extracted into:
- `hooks/` — data fetching, state, business logic
- `components/` — presentational sub-components

`components/ui/` is untouched throughout.

### Routing (`app/routing/`)

`AppRoutes.tsx` (564 lines) → combiner + 5 role-based files:
```
app/routing/
├── AppRoutes.tsx           (~80 lines, imports and combines role routes)
└── routes/
    ├── AdminRoutes.tsx
    ├── CheftechRoutes.tsx
    ├── TechnicienRoutes.tsx
    ├── ChetopRoutes.tsx
    └── SharedRoutes.tsx
```

### Module Splits

#### `admin/PlanningManagement.tsx` (955 lines)
```
admin/
├── PlanningManagement.tsx          (~180 lines, orchestrator)
├── components/PlanningCalendar.tsx
├── components/PlanningFormModal.tsx
└── hooks/usePlanningManagement.ts
```

#### `shared/InventoryPage.tsx` (848 lines)
```
shared/
├── InventoryPage.tsx               (~180 lines)
├── components/InventoryTable.tsx
├── components/StockMovementDialog.tsx
└── hooks/useInventory.ts
```

#### `shared/machines/components/PDCACanbanBoard.tsx` (702 lines)
```
machines/components/
├── PDCACanbanBoard.tsx             (~200 lines, board container)
├── PDCAColumn.tsx
├── PDCACard.tsx
└── hooks/usePDCABoard.ts
```

#### `technicien/TechnicianInterventions.tsx` (589 lines)
```
technicien/
├── TechnicianInterventions.tsx     (~200 lines)
├── components/InterventionFilters.tsx
└── components/InterventionTable.tsx
```

#### `shared/MachineDetailPage.tsx` (513 lines)
```
shared/
├── MachineDetailPage.tsx           (~200 lines)
└── components/MachineDetailTabs.tsx
```

#### `cheftech/dashboard/hooks/useCheftechDashboardData.ts` (511 lines)
```
hooks/
├── useInterventionsData.ts
├── useWorkOrdersData.ts
└── useDashboardStats.ts
```

#### `shared/work-orders/hooks/useWorkOrders.ts` (457 lines)
```
hooks/
├── useWorkOrdersList.ts
├── useWorkOrderActions.ts
└── useWorkOrderFilters.ts
```

#### Remaining files (same extract pattern)

| File | Lines | Extracted files |
|---|---|---|
| `chetop/components/CreateItvRequestModal.tsx` | 476 | + `ItvRequestForm.tsx` + `useItvRequestForm.ts` |
| `technicien/components/TechnicianNewInterventionModal.tsx` | 473 | + `InterventionFormFields.tsx` |
| `shared/PlanningDetailPage.tsx` | 458 | + `PlanningTechnicianList.tsx` + `PlanningWorkOrdersSection.tsx` |
| `cheftech/dashboard/components/InterventionsTab.tsx` | 458 | + `InterventionFilters.tsx` + `InterventionTable.tsx` |
| `shared/CompleteWorkOrderModal.tsx` | 445 | + `WorkOrderCompletionForm.tsx` |
| `shared/WorkOrderDetailPage.tsx` | 434 | + `WorkOrderInfoPanel.tsx` + `WorkOrderActionsPanel.tsx` |
| `technicien/TechnicianDashboard.tsx` | 391 | + `TechnicianStatsCards.tsx` + `TechnicianAlerts.tsx` |
| `shared/Reports.tsx` | 381 | + `ReportFilters.tsx` + `ReportTable.tsx` |
| `auth/Login.tsx` | 377 | + `LoginForm.tsx` + `useLoginForm.ts` |
| `technicien/components/InterventionRequestDialog.tsx` | 365 | + `InterventionRequestFormSection.tsx` |
| `cheftech/dashboard/components/CompletedWorkOrdersTab.tsx` | 358 | + `CompletedWorkOrderFilters.tsx` |
| `shared/work-orders/components/WorkOrderFormDialog.tsx` | 355 | + `WorkOrderFormFields.tsx` |
| `shared/WorkOrders.tsx` | 354 | + `WorkOrdersFilters.tsx` |

---

## Impact Summary

| | Count |
|---|---|
| Backend files created/moved | ~33 |
| Frontend files created | ~40 |
| Files deleted | `routers/` package (5 files) + `cheftech_old.py` if unreferenced |
| `main.py` changes | None |
| Breaking import changes | None (re-exports preserve public APIs) |
