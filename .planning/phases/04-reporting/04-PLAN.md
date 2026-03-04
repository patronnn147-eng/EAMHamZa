---
phase: 04-reporting
plan: '01'
type: execute
wave: '1'
depends_on: []
files_modified:
  - app/frontend/src/modules/shared/Dashboard.tsx
  - app/frontend/src/modules/shared/Reports.tsx
  - app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx
  - app/frontend/src/modules/cheftech/CheftechDashboard.tsx
  - app/frontend/src/modules/chetop/ChetopDashboard.tsx
  - app/frontend/src/modules/technicien/TechnicianDashboard.tsx
  - app/backend/modules/shared/rapports.py
autonomous: true
requirements:
  - RPT-01
  - RPT-02
user_setup: []

must_haves:
  truths:
    - Role-specific dashboards display metrics and stats
    - Reports page shows work order and machine reports
    - Reliability metrics (MTTR, MTBF, uptime) are calculated and displayed
  artifacts:
    - path: app/frontend/src/modules/shared/Dashboard.tsx
      provides: Main dashboard with overview
    - path: app/frontend/src/modules/shared/Reports.tsx
      provides: Reports page
    - path: app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx
      provides: Reliability metrics display
  key_links:
    - from: app/frontend/src/modules/shared/Dashboard.tsx
      to: app/backend/modules/shared/
      via: API calls for stats
---

<objective>
Verify Reporting & Analytics: dashboards, reports, and reliability metrics are all working correctly.
</objective>

<context>
@.planning/phases/04-reporting/04-CONTEXT.md
@.planning/phases/04-reporting/04-RESEARCH.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify Dashboards</name>
  <files>app/frontend/src/modules/shared/Dashboard.tsx, app/frontend/src/modules/cheftech/CheftechDashboard.tsx, app/frontend/src/modules/chetop/ChetopDashboard.tsx, app/frontend/src/modules/technicien/TechnicianDashboard.tsx</files>
  <action>
    Verify dashboards:
    1. Check all role dashboards exist and render
    2. Verify stats cards display data
    3. Check role-based content
    4. Ensure navigation works
    
    Fix any issues found.
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>All dashboards render correctly with proper role-based content</done>
</task>

<task type="auto">
  <name>Task 2: Verify Reports Page</name>
  <files>app/frontend/src/modules/shared/Reports.tsx, app/backend/modules/shared/rapports.py</files>
  <action>
    Verify reports:
    1. Check Reports.tsx exists and renders
    2. Verify backend API works
    3. Check data display
    4. Ensure export functionality if present
    
    Fix any issues found.
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>Reports page displays data correctly</done>
</task>

<task type="auto">
  <name>Task 3: Verify Reliability Metrics</name>
  <files>app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx</files>
  <action>
    Verify reliability:
    1. Check ReliabilityDashboardTab.tsx exists
    2. Verify MTTR/MTBF calculations work
    3. Check uptime/downtime display
    4. Ensure integration with machine data
    
    Fix any issues found.
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>Reliability metrics display correctly</done>
</task>

</tasks>

<verification>
- All dashboards render with role-specific content
- Reports page shows data
- Reliability metrics are calculated
- End-to-end flow works
</verification>

<success_criteria>
- Dashboards display for all roles
- Reports page works
- Reliability metrics show MTTR/MTBF
- No build errors
</success_criteria>

<output>
After completion, create `.planning/phases/04-reporting/04-01-SUMMARY.md`
</output>
