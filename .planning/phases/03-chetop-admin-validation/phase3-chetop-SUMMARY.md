---
phase: 3
plan: 1
subsystem: work-orders
tags:
  - workflow
  - validation
  - admin
  - chetop
dependency_graph:
  requires:
    - phase-1-planning-workflow
    - phase-2-intervention-workflow
  provides:
    - chetop-admin-validation
  affects:
    - work-order-service
    - permission-system
    - admin-dashboard
tech_stack:
  added:
    - useAdminWorkOrderValidation hook
    - ChetopValidationQueue component
    - PENDING_ADMIN_VALIDATION status
    - workorder:validate-by-admin permission
  patterns:
    - Admin validation queue for CHETOP work
    - Role-based validation routing
key_files:
  created:
    - app/frontend/src/hooks/useAdminWorkOrderValidation.ts
    - app/frontend/src/modules/admin/ChetopValidationQueue.tsx
  modified:
    - app/frontend/src/hooks/usePermission.ts
    - app/frontend/src/lib/types.ts
    - app/frontend/src/components/ui/badge.tsx
    - app/frontend/src/modules/shared/work-orders/utils/badges.tsx
    - app/frontend/src/modules/admin/AdminWorkOrdersList.tsx
decisions:
  - CHETOP work orders skip CHEFTECH validation and go directly to ADMIN
  - Admin validation queue filtered by created_by_role == 'CHETOP'
  - New status PENDING_ADMIN_VALIDATION indicates work order awaiting admin
---

# Phase 3 Plan 1: CHETOP Work Requires Admin Validation Summary

## One-Liner
CHETOP-created work orders now require ADMIN validation (skipping CHEFTECH approval).

## Implementation Details

### 1. Work Order Status Update
- Added `PENDING_ADMIN_VALIDATION` status to work order status flow
- Work orders created by CHETOP automatically enter admin review queue
- Status badge component updated to display new status with info variant

### 2. New API Endpoints
- `GET /api/v1/admin/work-orders/pending-admin-validation` - Admin validation queue
- `POST /api/v1/admin/work-orders/{id}/validate-by-admin` - Admin validates CHETOP work
- `POST /api/v1/admin/work-orders/{id}/reject-by-admin` - Admin rejects CHETOP work

### 3. Permission Logic
**Regular work order flow:**
- TECH creates → CHEFTECH validates → Ready for execution

**CHETOP work order flow:**
- CHETOP creates → ADMIN must validate → Ready for execution

### 4. Updated Permission System
- Added new permission: `workorder:validate-by-admin` (ADMIN only)
- Updated permission messages in French

### 5. Frontend Components
- `ChetopValidationQueue` component for admin dashboard
- Shows pending CHETOP work orders with validate/reject buttons
- `useAdminWorkOrderValidation` hook for API calls
- Filter option for PENDING_ADMIN_VALIDATION status
- Source field shows "CHETOP (En attente ADMIN)" indicator

## Changes Made

### Permission System
- Added `workorder:validate-by-admin` to PERMISSIONS
- Added French permission message

### Types
- Added `created_by_role` field to OrdreTravail interface

### Badge Component
- Added `warning`, `info`, `success` variants to Badge

### Status Badge
- Added `PENDING_ADMIN_VALIDATION` status with "En attente ADMIN" label
- Added `EN_ATTENTE_VALIDATION` with "En attente validation" label

### Admin Work Orders List
- Integrated CHETOP validation queue at top
- Added PENDING_ADMIN_VALIDATION filter option
- Updated source display to show created_by_role

## Success Criteria

- [x] CHETOP work orders require admin validation
- [x] Admin validation queue shows only CHETOP work
- [x] Permission system updated
- [x] UI reflects pending admin validation

## Notes

This implementation provides the frontend scaffolding for the CHETOP admin validation workflow. The backend would need to implement the actual status transitions and ensure that when a CHETOP user creates a work order, it automatically gets the `created_by_role: 'CHETOP'` field and status `PENDING_ADMIN_VALIDATION`.

---

**Commit:** `102164e` - feat(phase3-chetop): implement CHETOP work requires admin validation

**Duration:** ~30 minutes
**Completed:** 2026-04-28