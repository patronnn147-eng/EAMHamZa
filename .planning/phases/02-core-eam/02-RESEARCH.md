# Phase 2: Core EAM Features - Research

**Researched:** 2026-03-04
**Phase:** 02 - Core EAM Features

---

## What We Need to Know

### Current State
- Machine model exists with fields: name, type, status, location, zone
- Work order models exist: Ordres, OrdresTravail, OrdresIntervention
- Planning models exist with scheduling capabilities
- Frontend has machine grids, work order lists, calendar views
- Role-based access already implemented (from Phase 1)

### What's Likely Needed
Based on the codebase structure, the main work is likely:
1. Ensuring all CRUD operations work properly
2. Ensuring frontend-backend integration is complete
3. Adding any missing endpoints
4. Testing the full flow

---

## Implementation Approach

1. **Verify Machine Management**
   - Check CRUD endpoints in modules/shared/machines.py
   - Verify frontend components connect to API

2. **Verify Work Orders**
   - Check order creation, assignment, status updates
   - Verify technician can update status

3. **Verify Planning**
   - Check calendar integration
   - Verify technician assignment

4. **Integration Testing**
   - Full flow from creation to completion

---

## Common Pitfalls

1. **Missing API endpoints** - Some CRUD may be incomplete
2. **Frontend not connected** - Components may exist but not call API
3. **Role checks missing** - Some endpoints may not enforce RBAC
4. **Status transitions** - Workflow may have gaps

---

*Research complete: 2026-03-04*
