# KPI Trend Cards — Design Spec

Date: 2026-07-02
Scope: Fleet-level KPI row on the "Fiabilité" tab (`ReliabilityDashboardTab`), reachable from `/admin/dashboard` and `/cheftech/dashboard`.

## Problem

The four fleet KPI cards (Disponibilité moyenne, MTTR moyen, MTBF moyen, Arrêt total cumulé) currently show a single static number each. Users can't see whether a metric is improving or degrading without cross-referencing other data. Redesign these into compact BI-style trend cards.

## Visual design

Chosen from 3 mocked-up alternatives (sparkline-minimal, mini-area-chart, weekly-bars) — **mini area chart** selected.

Each card:
- Small icon + label, top-left (unchanged from today: Activity/Zap/Clock/TrendingDown from lucide-react)
- Current value, large, bold — still the primary focal point
- % change delta badge, top-right: arrow (▲/▼ matches actual direction) + percentage, pill-shaped
  - Color is direction-aware per metric, not literal arrow-up-is-green: for MTTR and Arrêt total (lower is better) a decrease is green/favorable; for Disponibilité and MTBF (higher is better) an increase is green/favorable. Unfavorable moves are red regardless of arrow direction.
- Gradient-filled mini area chart below the value, ~65px tall, `ResponsiveContainer` width 100%
  - X-axis: date labels, small font (~10-11px), `axisLine={false}` `tickLine={false}`, `interval="preserveStartEnd"` to avoid crowding on the narrow card, formatted `dd/MM` (fr-FR), matching the existing pattern in `HealthTrendChart.tsx`
  - No Y-axis, no gridlines (keep it minimal)
  - Dashed horizontal `ReferenceLine` for the target, where applicable
- Caption below chart: window + target text (e.g. "Cible 95% · 90j")

Card shell keeps existing glassmorphism: `bg-slate-800/50`, `border-blue-700/50`, `backdrop-blur`, rounded corners — no change to the outer `Card` styling, only the content.

## Data & calculation (client-side, no backend changes)

`ReliabilityDashboardTab` already fetches machines + interventions (`ordres_intervention`, sorted `-date_intervention`, `limit: 500`). Bump `limit` to `800` to safely cover 180 days of history (needed for the previous-period comparison) without a backend change.

New function in `app/frontend/src/modules/shared/machines/utils/reliabilityMetrics.ts`:

```
computeFleetKpiTrends(
  machines: Array<{ id: number; nom: string }>,
  interventionsByMachineId: Record<number, Intervention[]>,
  windowDays = 180,
  buckets = 13
): {
  availability: KpiTrend;
  mttr: KpiTrend;
  mtbf: KpiTrend;
  downtime: KpiTrend;
}
```

`KpiTrend` shape:
```
{
  series: { date: string; value: number }[];  // one point per weekly bucket, oldest -> newest
  current: number;       // aggregate over most recent 90 days
  previous: number | null; // aggregate over the 90 days before that (91-180 days ago)
  pctChange: number | null; // (current - previous) / previous * 100; null if previous is null or 0
  goodDirection: 'up' | 'down'; // which direction is favorable for this metric
  target: number | null; // fixed benchmark; null for downtime (no target line)
}
```

Calculation is **fleet-wide pooled**, not an average of per-machine scores (different from the existing `computeFleetReliability`, which stays untouched and keeps powering the fleet-overview panel and per-machine table below):

1. Pool all downtime events from all machines together (reuse the same event-derivation logic as `computeReliabilityMetrics`: interventions with both `date_debut` and `date_fin`).
2. **Weekly buckets** (13 x 7-day windows covering the most recent 91 days, oldest to newest):
   - `bucketDowntimeMinutes` = sum of durations of pooled events starting in that week
   - `bucketFailureCount` = count of those events
   - `bucketWindowMinutes` = `machines.length * 7 * 24 * 60`
   - `bucketUptimePct` = clamp(0, 100, `(bucketWindowMinutes - bucketDowntimeMinutes) / bucketWindowMinutes * 100`)
   - `bucketMttrMinutes` = `bucketFailureCount > 0 ? bucketDowntimeMinutes / bucketFailureCount : null` (chart: skip/interpolate null points)
   - `bucketMtbfHours` = `bucketFailureCount > 0 ? (bucketWindowMinutes/60 - bucketDowntimeMinutes/60) / bucketFailureCount : null`
3. **Period comparison**: same pooled-fleet formulas applied to two flat 90-day windows (0-90 days ago = current, 91-180 days ago = previous) instead of buckets, to get `current`/`previous`/`pctChange`.

Fixed targets and `goodDirection`:
- Disponibilité: target 95%, `goodDirection: 'up'`
- MTTR: target 24h (1440 min), `goodDirection: 'down'`
- MTBF: target 30j (720h), `goodDirection: 'up'`
- Arrêt total cumulé: `target: null` (cumulative downtime, a fixed target doesn't make sense) — trend only, no `ReferenceLine`; `goodDirection: 'down'` still drives the delta badge color.

## Components

New file: `app/frontend/src/modules/shared/machines/components/KpiTrendCard.tsx`

Props:
```
{
  label: string;
  icon: React.ElementType;
  valueFormatted: string;      // e.g. "97.2%", "39h 38m"
  valueColorClass?: string;    // existing color logic (emerald/blue/red) preserved
  trend: KpiTrend;
  targetLabel?: string;        // e.g. "Cible 95%"
  captionSuffix: string;       // e.g. "Flotte complète · 90j"
}
```
Renders the glass `Card` shell (same as today's local `StatCard`) with the value/badge header, then a recharts `AreaChart` (gradient `Area`, `XAxis` with date ticks, optional `ReferenceLine` for target), then the caption line.

`ReliabilityDashboardTab.tsx` changes:
- Remove the local `StatCard` component (replaced) — `SimpleBar` and everything else in the file stays as-is.
- Add `computeFleetKpiTrends` call in the existing `useMemo` (alongside `computeFleetReliability`, using the same `byMachine` grouping already built).
- Bump intervention fetch `limit` from 500 to 800.
- Replace the 4 `<StatCard ... />` usages in the KPI row with `<KpiTrendCard ... />`, wiring in the corresponding `trend` object.

## Animation & responsive

- framer-motion: staggered fade + slight translate-Y on the 4 cards when data finishes loading (children stagger ~80ms apart).
- recharts default area-draw-in animation on mount (`isAnimationActive` default true) — no custom animation code needed for the chart itself.
- Grid layout unchanged: `grid-cols-2 lg:grid-cols-4 gap-4`. Chart uses `ResponsiveContainer` so it scales down cleanly at 2-column mobile width.

## Out of scope

- No backend changes.
- Fleet-overview panel and per-machine reliability table (rest of the Fiabilité tab) — untouched.
- Per-card loading skeletons — the existing page-level spinner covers initial load; only the mount-in animation applies once data is ready.
- Configurable/user-editable targets — hardcoded for now, per user decision.
