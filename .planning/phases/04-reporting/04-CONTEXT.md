# Phase 4: Reporting & Analytics - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning
**Source:** Codebase analysis

---

<domain>
## Phase Boundary

Implement Reporting & Analytics:
- Role-specific dashboards with metrics
- Reports generation and export
- Reliability metrics display

**Existing codebase:** Dashboards exist for all roles, Reports module exists

</domain>

<decisions>
## Implementation Decisions

### Dashboards
- **Admin Dashboard:** Overview with stats
- **ChefTech Dashboard:** Team metrics, intervention stats
- **Chetop Dashboard:** Work orders, machines overview
- **Technician Dashboard:** Assignments, personal stats
- **Reliability Dashboard:** MTTR, MTBF, uptime metrics

### Reports
- **Backend:** API in `modules/shared/rapports.py`
- **Frontend:** Reports page in `modules/shared/Reports.tsx`

### Analytics
- **Reliability metrics:** MTTR, MTBF, uptime calculations
- **Health scores:** Machine health display
- **Statistics:** Dashboard stats cards

</decisions>

<specifics>
## Specific Ideas

**From existing code:**
- `app/frontend/src/modules/shared/Dashboard.tsx` - Main dashboard
- `app/frontend/src/modules/shared/Reports.tsx` - Reports page
- `app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx` - Reliability metrics
- `app/backend/modules/shared/rapports.py` - Reports API

**Dashboard types:**
- Admin overview
- ChefTech team metrics
- ChetOp work orders
- Technician personal stats

</specifics>

<deferred>
## Deferred Ideas

- PDF export (future phase)
- Scheduled reports (future phase)
- Advanced analytics (future phase)

</deferred>

---

*Phase: 04-reporting*
*Context gathered: 2026-03-04*
