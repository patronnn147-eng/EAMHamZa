# PDCA Implementation Plan - All Modules

This plan outlines how the Plan-Do-Check-Act (PDCA) cycle will be integrated into the EAMSagemCom Asset Management System across all layers.

## Proposed Changes

### 1. Plan Phase (Maintenance Strategy)
- **Objective**: Define targets and success metrics.
- **Backend Changes**:
  - [MODIFY] `app/backend/models/machines.py`: Add `target_mtbf` (float) and `target_mttr` (float) columns.
  - [MODIFY] `app/backend/schemas/machines.py`: Update Pydantic schemas to include new target fields.
- **Frontend Changes**:
  - [MODIFY] `app/frontend/src/modules/cheftech/machines/components/MachineFormDialog.tsx`: Add input fields for Target MTBF and MTTR.
  - [MODIFY] `app/frontend/src/lib/types.ts`: Update `Machine` interface.

### 2. Do Phase (Execution & Data Capture)
- **Objective**: Capture precise intervention data to allow for "Check" analysis.
- **Backend Changes**:
  - [MODIFY] `app/backend/models/ordres_travail.py`: Add `actual_duration` (int) and `completion_notes` (text).
  - [MODIFY] `app/backend/models/ordres_intervention.py`: Add `parts_replaced` (JSON/Text).
- **Frontend Changes**:
  - [MODIFY] `app/frontend/src/modules/technicien/TechnicianWorkOrderDetail.tsx`: Add fields to enter actual duration and parts used upon completion.

### 3. Check Phase (Analysis & Audit)
- **Objective**: Compare Planned vs Actual and visualize gaps.
- **Backend Changes**:
  - [NEW] `app/backend/modules/shared/pdca_service.py`: Logic to calculate MTBF/MTTR and compare with targets.
  - [NEW] `app/backend/routers/pdca.py`: API endpoints for PDCA analytics.
- **Frontend Changes**:
  - [NEW] `app/frontend/src/modules/cheftech/dashboard/components/PDCADashboard.tsx`: A new dashboard tab showing "Plan vs Actual" for MTBF, MTTR, and Maintenance Compliance.

### 4. Act Phase (Continuous Improvement)
- **Objective**: Trigger adjustments based on "Check" findings.
- **Features**:
  - [NEW] **Recommendation Engine**: In the PDCA Dashboard, if MTBF is < Target, show a "Suggested Action" (e.g., "Increase Preventive Maintenance Frequency").
  - [NEW] **Auto-Tasking**: Option to automatically create a "Strategy Review" Work Order when targets are consistently missed.

## Verification Plan

### Automated Tests
- `pytest app/backend/tests/test_pdca_logic.py`: Verify MTBF/MTTR calculations.
- `pnpm test PDCADashboard`: Ensure charts render correctly with gap analysis data.

### Manual Verification
1. Edit a Machine to set MTBF Target = 100 hours.
2. Complete a Work Order with actual data.
3. Open the new PDCA Dashboard and verify the "Actual vs Target" bar chart shows the correct delta.
