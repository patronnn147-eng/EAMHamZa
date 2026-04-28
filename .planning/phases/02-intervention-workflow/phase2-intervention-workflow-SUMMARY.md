---
phase: 2
plan: intervention-workflow
subsystem: intervention-work-order
tags: [intervention, work-order, planning, approval, workflow]
dependency_graph:
  requires:
    - phase-1-planning-workflow
    - phase-1-permissions
  provides:
    - intervention-api
    - work-order-from-intervention
  affects:
    - Ordres_intervention model
    - Ordres_travail creation
tech_stack:
  added:
    - planning_id field
    - Intervention workflow endpoints
    - Alembic migration
  patterns:
    - REST API with role-based permissions
    - Validation workflow (PENDING → APPROVED/REJECTED)
    - Work order generation from approved intervention
key_files:
  created:
    - app/backend/alembic/versions/phase2_intervention_planning.py
    - app/backend/modules/shared/routes/intervention_workflow.py
  modified:
    - app/backend/models/ordres_intervention.py
    - app/backend/modules/shared/routes/ordres_travail/schemas.py
    - app/backend/modules/shared/routes/__init__.py
decisions:
  - Used /api/v1/entities/intervention-workflow prefix to avoid route conflicts
  - PENDING status for new interventions requiring validation
  - CONVERTED_TO_WORKORDER status after work order created
metrics:
  duration: "~1 hour"
  completed_date: "2026-04-28"
  tasks: 4
---

# Phase 2: Intervention → Work Order Workflow Summary

## Overview
Implemented the Phase 2 workflow that connects plannings to work orders through interventions with approval flow.

## What Was Built

### 1. Database Model Enhancement
- Added `planning_id` field to `Ordres_intervention` model to link interventions to planning tasks
- This enables tracing interventions back to their source plannings

### 2. New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/entities/intervention-workflow/create` | POST | Create intervention from a planning |
| `/api/v1/entities/intervention-workflow` | GET | List interventions with filtering |
| `/api/v1/entities/intervention-workflow/{id}` | GET | Get single intervention |
| `/api/v1/entities/intervention-workflow/{id}/validate` | POST | Validate or reject (APPROVE/REJECT) |
| `/api/v1/entities/intervention-workflow/{id}/create-work-order` | POST | Generate work order from approved intervention |
| `/api/v1/entities/intervention-workflow/pending` | GET | Get all pending validations |

### 3. Work Order Integration
- Added optional `intervention_id` field to work order creation schema
- When work order is created, intervention status changes to `CONVERTED_TO_WORKORDER`
- Work order inherits machine_id, description, priority from intervention

### 4. Role-Based Permissions

| Action | ADMIN | CHEFTECH | CHETOP | TECH |
|-------|-------|----------|--------|------|
| Create Intervention from Planning | ✓ | ✓ | ✓ | ✓ |
| Validate Intervention | | ✓ | | ✓ |
| Create Work Order from Intervention | | ✓ | | ✓ |

### 5. Database Migration
- Created Alembic migration `phase2_intervention_planning.py`
- Adds `planning_id` column with index to `ordres_intervention` table

## Workflow States

```
PENDING → (validate with APPROVE) → APPROVED → (create-work-order) → CONVERTED_TO_WORKORDER
         → (validate with REJECT) → REJECTED
```

## Files Modified/Created

| File | Change |
|------|--------|
| `app/backend/models/ordres_intervention.py` | Added planning_id field |
| `app/backend/modules/shared/routes/intervention_workflow.py` | **NEW** - All endpoint implementations |
| `app/backend/modules/shared/routes/__init__.py` | Added router export |
| `app/backend/modules/shared/routes/ordres_travail/schemas.py` | Added intervention_id field |
| `app/backend/alembic/versions/phase2_intervention_planning.py` | **NEW** - Database migration |

## Verification

The endpoints can be tested with:

```bash
# Create intervention from planning (requires APPROVED planning)
POST /api/v1/entities/intervention-workflow/create?planning_id=1&machine_id=2&problem_description="Belt worn"

# Validate as CHEFTECH
POST /api/v1/entities/intervention-workflow/1/validate {"action": "APPROVE"}

# Create work order from validated intervention  
POST /api/v1/entities/intervention-workflow/1/create-work-order

# Get pending validations (CHEFTECH/ADMIN only)
GET /api/v1/entities/intervention-workflow/pending
```

## Success Criteria Status

| Criterion | Status |
|-----------|--------|
| Intervention API endpoints working | ✅ Implemented |
| Validation workflow functional | ✅ Implemented |
| Work order generation from intervention | ✅ Implemented |
| Role permissions enforced | ✅ Implemented |

## Deviations from Plan

None - plan executed exactly as written.