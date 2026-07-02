# Dashboard Pie Charts — Design

## Goal
Add pie charts to the Admin dashboard and ChefTech dashboard main overview so users get an at-a-glance visual read on fleet/workload/intervention distribution, without navigating into a sub-tab.

## Scope
- Admin dashboard: `app/frontend/src/modules/shared/Dashboard.tsx`
- ChefTech dashboard: `app/frontend/src/modules/cheftech/CheftechDashboard.tsx`
- New shared component: `app/frontend/src/modules/shared/dashboard/DashboardPieChartCard.tsx`
- No backend changes. No new API calls — all charts use data the dashboards already fetch.

## Component: `DashboardPieChartCard`

Reusable donut-pie card used by both dashboards.

Props:
```ts
interface DashboardPieChartCardProps {
  title: string;
  data: { name: string; value: number; color?: string }[];
  emptyLabel?: string; // default: "No data"
}
```

Behavior:
- Renders a `Card` (existing `@/components/ui/card`) with `CardHeader`/`CardTitle` = `title`.
- Recharts `PieChart` → donut style: `innerRadius={60}`, `outerRadius={100}`, `paddingAngle={2}`, matching the existing pie in [SystemAnalytics.tsx](../../../app/frontend/src/modules/admin/SystemAnalytics.tsx).
- Slice labels: `${name} (${percent}%)`.
- Tooltip via recharts `Tooltip`.
- If every `value` in `data` is 0 (or `data` is empty), render a centered empty-state message (`emptyLabel`) instead of the chart — same pattern already used in `SystemAnalytics.tsx` / `AnalyticsTab.tsx`.
- Wrapped in a `framer-motion` fade/slide-in (`initial={{opacity:0,y:12}}`, `animate={{opacity:1,y:0}}`) matching [KpiTrendCard.tsx](../../../app/frontend/src/modules/shared/machines/components/KpiTrendCard.tsx) for visual consistency with the rest of the dashboard.
- Colors: caller passes `color` per data point when a semantic color is meaningful (see color mapping below); if omitted, falls back to a fixed default palette array indexed by position.

## Color mapping (semantic, not arbitrary rotation)

| Meaning | Color |
|---|---|
| Operational / Completed / Low priority | `#10b981` (emerald) |
| In progress / Medium / Neutral | `#3b82f6` (blue) |
| Pending / Elevated | `#f59e0b` (amber) |
| Urgent / Critical / Panne / Out of service | `#ef4444` (red) |
| Other / Unknown | `#94a3b8` (slate) |

This mirrors the existing badge color conventions already used in `Dashboard.tsx` (`getStatusBadge`, `getPriorityBadge`) and `CheftechDashboard.tsx`.

## Admin Dashboard changes

File: `Dashboard.tsx`

Insert a new row directly after the existing "Metrics Grid" section:

```tsx
<div className="grid grid-cols-1 gap-5 md:grid-cols-3">
  <DashboardPieChartCard title="Machines by Status" data={machinesByStatus} />
  <DashboardPieChartCard title="Work Orders by Priority" data={workOrdersByPriority} />
  <DashboardPieChartCard title="Work Orders by Status" data={workOrdersByStatus} />
</div>
```

Data grouping (client-side, derived from `machines` and `workOrders` state already populated by `fetchDashboardData()`):
- `machinesByStatus`: group by `machine.statut` (`OPERATIONNELLE`, `EN_MAINTENANCE`, `HORS_SERVICE`, etc. — whatever values are actually present; unmapped values bucket into "Other").
- `workOrdersByPriority`: group by `wo.priorite` (`BASSE`, `MOYENNE`, `ELEVEE`, `URGENTE`).
- `workOrdersByStatus`: group by `wo.statut` (`EN_ATTENTE`, `EN_COURS`, `TERMINE`, `ANNULE`).

Note: `Dashboard.tsx` currently discards the full `machines`/`workOrders` arrays after computing scalar `metrics` (see `fetchDashboardData`) — it keeps only `recentWorkOrders`/`upcomingMaintenance` slices. This design adds two new state slots (`allMachines`, `allWorkOrders`) to retain the full arrays for grouping, since 100-item arrays are cheap and already fetched.

## ChefTech Dashboard changes

File: `CheftechDashboard.tsx`

Insert a new row between the page header and `DashboardStatsCards`:

```tsx
<div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
  <DashboardPieChartCard title="Interventions by Status" data={interventionsByStatus} />
  <DashboardPieChartCard title="Preventive vs Corrective" data={interventionsByType} />
  <DashboardPieChartCard title="Root Cause Categories" data={interventionsByRootCause} />
  <DashboardPieChartCard title="Critical vs Non-Critical Load" data={interventionsByMachineCategory} />
</div>
```

Data grouping (client-side, derived from `interventions` state already provided by `useCheftechDashboardData()`):
- `interventionsByStatus`: group by `statut`.
- `interventionsByType`: group by `intervention_type` (values null/undefined bucket into "Non spécifié").
- `interventionsByRootCause`: group by `root_cause_category` (null/undefined → "Non spécifié").
- `interventionsByMachineCategory`: group by `machine_category` (null/undefined → "Non spécifié").

Note: `root_cause_category`/`intervention_type`/`machine_category` are optional fields (`?:` in `lib/types.ts`) and are typically only populated once an intervention reaches a later workflow stage (act/check phases). It's expected these pies will show a large "Non spécifié" slice for interventions still early in their lifecycle — this is accurate, not a bug.

## Grouping helper

Both dashboards need the same "count by field, bucket unknowns" logic. Add a small shared utility:

`app/frontend/src/modules/shared/dashboard/groupByField.ts`
```ts
export function groupByField<T>(
  items: T[],
  getKey: (item: T) => string | null | undefined,
  labelMap: Record<string, string> = {},
  otherLabel = 'Other'
): { name: string; value: number }[]
```
Groups `items` by `getKey`, maps raw enum values to display labels via `labelMap` (falls back to raw value if unmapped), and coalesces null/undefined keys into `otherLabel`. Returns array sorted descending by `value`.

## Testing
- Unit test `groupByField.ts` (empty array, all-null keys, mixed known/unknown keys, sort order).
- Manual verification via dev server: load Admin dashboard and ChefTech dashboard, confirm 3 and 4 pies render respectively with real data, confirm empty-state renders when a group has zero items (can force by filtering test data), confirm dark theme styling matches surrounding cards.

## Out of scope (explicitly deferred, per brainstorm)
- Maintenance cost distribution pie — no cost field exists on `machines`/`ordres_travail` yet.
- Users by role pie, Machines by type pie — deprioritized, not requested for this pass.
- Personal workload by technician — better suited to a table in the Techniciens tab, not a pie.
