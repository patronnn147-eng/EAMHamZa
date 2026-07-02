# KPI Trend Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 4 static fleet KPI cards on the "Fiabilité" tab (Disponibilité/MTTR/MTBF/Arrêt total) with mini area-chart trend cards showing weekly history, period-over-period % change, and fixed benchmark targets.

**Architecture:** Pure client-side calculation (new `computeFleetKpiTrends` function pools fleet-wide downtime events into weekly buckets + a current-vs-previous-90-day comparison) feeds a new presentational `KpiTrendCard` component (recharts `AreaChart` + framer-motion entrance), which replaces the local `StatCard` used in `ReliabilityDashboardTab`. No backend changes.

**Tech Stack:** React 19 + TypeScript, recharts 2.15 (already a dependency, already used elsewhere e.g. `HealthTrendChart.tsx`), framer-motion 11 (already used elsewhere e.g. `PDCA/*Column.tsx`), Tailwind (existing glass card classes).

## Global Constraints

- No backend/API changes — all new logic is client-side, working off data already fetched by `ReliabilityDashboardTab`.
- Fixed targets: Disponibilité ≥95%, MTTR ≤24h (1440 min), MTBF ≥30j (720h), Arrêt total cumulé has no target.
- Fleet-wide pooled calculation (not average-of-per-machine) for the new trend cards — the existing `computeFleetReliability`/`avgUptimePct` etc. used by the rest of the tab (fleet overview panel, per-machine table) must NOT be touched or change behavior.
- X-axis on each mini chart shows dates (`dd/MM`, fr-FR), sparse ticks (`interval="preserveStartEnd"`), no Y-axis, no gridlines.
- **No frontend test runner exists in this repo** (checked: no jest/vitest/testing-library in `app/frontend/package.json`, no test script, only `node_modules` contain vendored test files). Verification for this plan uses TypeScript type-checking (`tsc --noEmit`), ESLint, and manual browser verification via the preview tool — not unit tests. Do not introduce a new test framework as part of this plan; that's out of scope.
- All commands below run from `app/frontend/` (the frontend package root).

---

### Task 1: Add `computeFleetKpiTrends` to `reliabilityMetrics.ts`

**Files:**
- Modify: `app/frontend/src/modules/shared/machines/utils/reliabilityMetrics.ts`

**Interfaces:**
- Consumes: existing `DowntimeEvent` interface (already defined in this file, lines 9-16), existing `Intervention` type from `@/lib/types`.
- Produces (used by Task 2 and Task 3):
  - `interface TrendPoint { date: string; value: number | null }`
  - `interface KpiTrend { series: TrendPoint[]; current: number; previous: number | null; pctChange: number | null; goodDirection: 'up' | 'down'; target: number | null }`
  - `interface FleetKpiTrends { availability: KpiTrend; mttr: KpiTrend; mtbf: KpiTrend; downtime: KpiTrend }`
  - `function computeFleetKpiTrends(machines: Array<{ id: number; nom: string }>, interventionsByMachineId: Record<number, Intervention[]>, windowDays?: number, buckets?: number): FleetKpiTrends`

- [ ] **Step 1: Append the new types and function to the end of the file**

Add this to the end of `app/frontend/src/modules/shared/machines/utils/reliabilityMetrics.ts` (after the closing brace of `computeFleetReliability`, i.e. after line 213):

```ts
/**
 * Fleet-wide KPI trend data for the top-of-tab summary cards.
 * Unlike computeFleetReliability (average of per-machine scores), this pools
 * ALL machines' downtime events together to produce fleet-wide totals per
 * time bucket, which is what a trend chart should show.
 */
export interface TrendPoint {
    /** ISO date (yyyy-mm-dd) of the bucket's start */
    date: string;
    value: number | null;
}

export interface KpiTrend {
    /** Oldest -> newest, one point per weekly bucket */
    series: TrendPoint[];
    /** Aggregate over the most recent 90 days */
    current: number;
    /** Aggregate over the 90 days before that (91-180 days ago) */
    previous: number | null;
    /** (current - previous) / previous * 100 */
    pctChange: number | null;
    /** Which direction is favorable for this metric */
    goodDirection: 'up' | 'down';
    /** Fixed benchmark line; null if no target applies */
    target: number | null;
}

export interface FleetKpiTrends {
    availability: KpiTrend;
    mttr: KpiTrend;
    mtbf: KpiTrend;
    downtime: KpiTrend;
}

function pctChange(curr: number, prev: number | null): number | null {
    if (prev === null || prev === 0) return null;
    return ((curr - prev) / prev) * 100;
}

export function computeFleetKpiTrends(
    machines: Array<{ id: number; nom: string }>,
    interventionsByMachineId: Record<number, Intervention[]>,
    windowDays = 180,
    buckets = 13
): FleetKpiTrends {
    const now = Date.now();
    const cutoff = new Date(now - windowDays * 24 * 60 * 60 * 1000);
    const fleetSize = machines.length || 1;

    // Pool all downtime events across the fleet within the full window
    const allEvents: DowntimeEvent[] = [];
    for (const m of machines) {
        const interventions = interventionsByMachineId[m.id] ?? [];
        for (const i of interventions) {
            if (!i.date_debut || !i.date_fin) continue;
            const start = new Date(i.date_debut);
            if (start < cutoff) continue;
            const end = new Date(i.date_fin);
            const durationMinutes = Math.max(0, (end.getTime() - start.getTime()) / 60000);
            if (durationMinutes <= 0) continue;
            allEvents.push({
                id: i.id,
                start,
                end,
                durationMinutes,
                technicienId: i.technicien_id,
                rapport: i.rapport,
            });
        }
    }

    // --- Weekly buckets over the most recent `buckets` x 7 days ---
    const bucketDays = 7;
    const bucketWindowMinutes = fleetSize * bucketDays * 24 * 60;

    const availabilitySeries: TrendPoint[] = [];
    const mttrSeries: TrendPoint[] = [];
    const mtbfSeries: TrendPoint[] = [];
    const downtimeSeries: TrendPoint[] = [];

    for (let b = buckets - 1; b >= 0; b--) {
        const bucketEnd = new Date(now - b * bucketDays * 24 * 60 * 60 * 1000);
        const bucketStart = new Date(bucketEnd.getTime() - bucketDays * 24 * 60 * 60 * 1000);
        const eventsInBucket = allEvents.filter((e) => e.start >= bucketStart && e.start < bucketEnd);
        const downtimeMinutes = eventsInBucket.reduce((s, e) => s + e.durationMinutes, 0);
        const failureCount = eventsInBucket.length;
        const uptimePct = Math.max(0, Math.min(100, ((bucketWindowMinutes - downtimeMinutes) / bucketWindowMinutes) * 100));
        const dateLabel = bucketStart.toISOString().slice(0, 10);

        availabilitySeries.push({ date: dateLabel, value: Math.round(uptimePct * 10) / 10 });
        downtimeSeries.push({ date: dateLabel, value: Math.round(downtimeMinutes) });
        mttrSeries.push({
            date: dateLabel,
            value: failureCount > 0 ? Math.round(downtimeMinutes / failureCount) : null,
        });
        mtbfSeries.push({
            date: dateLabel,
            value: failureCount > 0
                ? Math.round((bucketWindowMinutes / 60 - downtimeMinutes / 60) / failureCount)
                : null,
        });
    }

    // --- Current (0-90d) vs previous (91-180d) period aggregates ---
    const periodMinutes = 90 * 24 * 60 * fleetSize;
    const currentCutoff = new Date(now - 90 * 24 * 60 * 60 * 1000);
    const previousCutoff = new Date(now - 180 * 24 * 60 * 60 * 1000);

    const currentEvents = allEvents.filter((e) => e.start >= currentCutoff);
    const previousEvents = allEvents.filter((e) => e.start >= previousCutoff && e.start < currentCutoff);

    const aggregate = (events: DowntimeEvent[]) => {
        const downtimeMinutes = events.reduce((s, e) => s + e.durationMinutes, 0);
        const failureCount = events.length;
        const uptimePct = Math.max(0, Math.min(100, ((periodMinutes - downtimeMinutes) / periodMinutes) * 100));
        const mttrMinutes = failureCount > 0 ? downtimeMinutes / failureCount : null;
        const mtbfHours = failureCount > 0 ? (periodMinutes / 60 - downtimeMinutes / 60) / failureCount : null;
        return { downtimeMinutes, uptimePct, mttrMinutes, mtbfHours };
    };

    const current = aggregate(currentEvents);
    const previous = aggregate(previousEvents);

    return {
        availability: {
            series: availabilitySeries,
            current: Math.round(current.uptimePct * 10) / 10,
            previous: Math.round(previous.uptimePct * 10) / 10,
            pctChange: pctChange(current.uptimePct, previous.uptimePct),
            goodDirection: 'up',
            target: 95,
        },
        mttr: {
            series: mttrSeries,
            current: current.mttrMinutes !== null ? Math.round(current.mttrMinutes) : 0,
            previous: previous.mttrMinutes !== null ? Math.round(previous.mttrMinutes) : null,
            pctChange: pctChange(current.mttrMinutes ?? 0, previous.mttrMinutes),
            goodDirection: 'down',
            target: 1440,
        },
        mtbf: {
            series: mtbfSeries,
            current: current.mtbfHours !== null ? Math.round(current.mtbfHours) : 0,
            previous: previous.mtbfHours !== null ? Math.round(previous.mtbfHours) : null,
            pctChange: pctChange(current.mtbfHours ?? 0, previous.mtbfHours),
            goodDirection: 'up',
            target: 720,
        },
        downtime: {
            series: downtimeSeries,
            current: Math.round(current.downtimeMinutes),
            previous: Math.round(previous.downtimeMinutes),
            pctChange: pctChange(current.downtimeMinutes, previous.downtimeMinutes),
            goodDirection: 'down',
            target: null,
        },
    };
}
```

- [ ] **Step 2: Type-check**

Run (from `app/frontend/`): `pnpm exec tsc -p tsconfig.app.json --noEmit`
Expected: no errors.

- [ ] **Step 3: Lint**

Run (from `app/frontend/`): `pnpm run lint`
Expected: no errors (warnings pre-existing elsewhere in the repo are fine, but this file must be clean).

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/modules/shared/machines/utils/reliabilityMetrics.ts
git commit -m "feat(reliability): add fleet-wide KPI trend calculation"
```

---

### Task 2: Create `KpiTrendCard` component

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/KpiTrendCard.tsx`

**Interfaces:**
- Consumes: `KpiTrend` type from Task 1 (`app/frontend/src/modules/shared/machines/utils/reliabilityMetrics.ts`).
- Produces (used by Task 3): `KpiTrendCard` React component with props:
  ```ts
  interface KpiTrendCardProps {
    label: string;
    icon: React.ElementType;
    valueFormatted: string;
    valueColorClass?: string;
    trend: KpiTrend;
    targetLabel?: string;
    captionSuffix: string;
    index?: number;
  }
  ```

- [ ] **Step 1: Write the component**

Create `app/frontend/src/modules/shared/machines/components/KpiTrendCard.tsx`:

```tsx
import React, { useId } from 'react';
import { motion } from 'framer-motion';
import {
    AreaChart,
    Area,
    XAxis,
    ReferenceLine,
    Tooltip as RechartsTooltip,
    ResponsiveContainer,
} from 'recharts';
import { Card, CardContent } from '@/components/ui/card';
import type { KpiTrend } from '../utils/reliabilityMetrics';

interface KpiTrendCardProps {
    label: string;
    icon: React.ElementType;
    valueFormatted: string;
    valueColorClass?: string;
    trend: KpiTrend;
    targetLabel?: string;
    captionSuffix: string;
    index?: number;
}

function formatDateTick(value: string): string {
    const d = new Date(value);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
}

export const KpiTrendCard: React.FC<KpiTrendCardProps> = ({
    label,
    icon: Icon,
    valueFormatted,
    valueColorClass = 'text-blue-50',
    trend,
    targetLabel,
    captionSuffix,
    index = 0,
}) => {
    const gradientId = useId();

    const isFavorable =
        trend.pctChange === null
            ? null
            : trend.goodDirection === 'up'
                ? trend.pctChange > 0
                : trend.pctChange < 0;

    const chartColor = isFavorable === null ? '#60a5fa' : isFavorable ? '#34d399' : '#f87171';
    const badgeColorClass =
        isFavorable === null
            ? 'bg-blue-500/15 text-blue-300'
            : isFavorable
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-red-500/15 text-red-400';
    const arrow = trend.pctChange === null ? '—' : trend.pctChange > 0 ? '▲' : trend.pctChange < 0 ? '▼' : '—';

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: index * 0.08 }}
        >
            <Card>
                <CardContent className="pt-5 pb-3">
                    <div className="flex items-start justify-between mb-1">
                        <div className="flex items-center gap-1.5">
                            <Icon className="h-3.5 w-3.5 text-blue-400" />
                            <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">{label}</p>
                        </div>
                        {trend.pctChange !== null && (
                            <span
                                className={`inline-flex items-center gap-0.5 text-[11px] font-bold rounded-full px-2 py-0.5 shrink-0 ${badgeColorClass}`}
                            >
                                {arrow} {Math.abs(trend.pctChange).toFixed(1)}%
                            </span>
                        )}
                    </div>

                    <p className={`text-2xl font-black ${valueColorClass}`}>{valueFormatted}</p>

                    <div className="h-[65px] -ml-2 mt-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={trend.series} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                                <defs>
                                    <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={chartColor} stopOpacity={0.4} />
                                        <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="date"
                                    tick={{ fontSize: 10, fill: '#93c5fd' }}
                                    axisLine={false}
                                    tickLine={false}
                                    interval="preserveStartEnd"
                                    tickFormatter={formatDateTick}
                                />
                                {trend.target !== null && (
                                    <ReferenceLine
                                        y={trend.target}
                                        stroke="#93c5fd"
                                        strokeDasharray="3 3"
                                        strokeOpacity={0.6}
                                    />
                                )}
                                <RechartsTooltip
                                    contentStyle={{ borderRadius: 8, border: 'none', fontSize: 12 }}
                                    labelFormatter={(value: string) => new Date(value).toLocaleDateString('fr-FR')}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={chartColor}
                                    strokeWidth={2}
                                    fill={`url(#${gradientId})`}
                                    connectNulls={false}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    <p className="text-xs text-blue-400 mt-0.5">
                        {targetLabel ? `${targetLabel} · ` : ''}
                        {captionSuffix}
                    </p>
                </CardContent>
            </Card>
        </motion.div>
    );
};

export default KpiTrendCard;
```

- [ ] **Step 2: Type-check**

Run (from `app/frontend/`): `pnpm exec tsc -p tsconfig.app.json --noEmit`
Expected: no errors.

- [ ] **Step 3: Lint**

Run (from `app/frontend/`): `pnpm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/KpiTrendCard.tsx
git commit -m "feat(reliability): add KpiTrendCard component"
```

---

### Task 3: Wire `KpiTrendCard` into `ReliabilityDashboardTab`

**Files:**
- Modify: `app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx`

**Interfaces:**
- Consumes: `KpiTrendCard` (Task 2), `computeFleetKpiTrends`/`FleetKpiTrends` (Task 1), existing `computeFleetReliability`/`formatDuration`/`formatHours` (unchanged).

- [ ] **Step 1: Remove the local `StatCard` component and update imports**

In `app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx`, replace lines 1-46 (everything from the top of the file through the end of the `StatCard` function) with:

```tsx
import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock,
    TrendingDown,
    TrendingUp,
    Zap,
    ChevronRight,
} from 'lucide-react';
import type { Machine, Intervention } from '@/lib/types';
import {
    computeFleetReliability,
    computeFleetKpiTrends,
    formatDuration,
    formatHours,
    type FleetReliabilitySummary,
    type FleetKpiTrends,
} from './machines/utils/reliabilityMetrics';
import { KpiTrendCard } from './machines/components/KpiTrendCard';

function SimpleBar({ pct, colorClass }: { pct: number; colorClass: string }) {
    return (
        <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
                className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-700`}
                style={{ width: `${Math.min(100, pct)}%` }}
            />
        </div>
    );
}
```

- [ ] **Step 2: Bump the intervention fetch limit to cover 180 days**

Find this line (originally around line 78):

```ts
                    client.entities.ordres_intervention.queryAll({ query: {}, sort: '-date_intervention', limit: 500 }),
```

Replace with:

```ts
                    client.entities.ordres_intervention.queryAll({ query: {}, sort: '-date_intervention', limit: 800 }),
```

- [ ] **Step 3: Split the `byMachine` grouping out of `summary` and add `kpiTrends`**

Find the `summary` useMemo block (originally lines 91-101):

```ts
    const summary: FleetReliabilitySummary = useMemo(() => {
        // Group interventions by machine_id
        const byMachine: Record<number, Intervention[]> = {};
        for (const i of interventions) {
            if (i.machine_id) {
                if (!byMachine[i.machine_id]) byMachine[i.machine_id] = [];
                byMachine[i.machine_id].push(i);
            }
        }
        return computeFleetReliability(machines, byMachine, 90);
    }, [machines, interventions]);
```

Replace with:

```ts
    const byMachine: Record<number, Intervention[]> = useMemo(() => {
        const grouped: Record<number, Intervention[]> = {};
        for (const i of interventions) {
            if (i.machine_id) {
                if (!grouped[i.machine_id]) grouped[i.machine_id] = [];
                grouped[i.machine_id].push(i);
            }
        }
        return grouped;
    }, [interventions]);

    const summary: FleetReliabilitySummary = useMemo(
        () => computeFleetReliability(machines, byMachine, 90),
        [machines, byMachine]
    );

    const kpiTrends: FleetKpiTrends = useMemo(
        () => computeFleetKpiTrends(machines, byMachine, 180, 13),
        [machines, byMachine]
    );
```

- [ ] **Step 4: Replace the 4 `StatCard` usages with `KpiTrendCard`**

Find the KPI row block (originally lines 121-150):

```tsx
            {/* Fleet KPI row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    label="Disponibilité moyenne"
                    value={`${avgUptimePct.toFixed(1)}%`}
                    sublabel="Flotte complète · 90j"
                    icon={Activity}
                    color={avgUptimePct >= 95 ? 'text-emerald-600' : avgUptimePct >= 85 ? 'text-blue-600' : 'text-red-600'}
                />
                <StatCard
                    label="MTTR moyen"
                    value={avgMttr !== null ? formatDuration(avgMttr) : 'N/A'}
                    sublabel="Temps moyen de réparation"
                    icon={Zap}
                    color="text-blue-50"
                />
                <StatCard
                    label="MTBF moyen"
                    value={avgMtbf !== null ? formatHours(avgMtbf) : 'N/A'}
                    sublabel="Temps entre pannes"
                    icon={Clock}
                    color="text-blue-50"
                />
                <StatCard
                    label="Arrêt total cumulé"
                    value={formatDuration(totalDowntimeMinutes)}
                    sublabel="Toutes machines · 90j"
                    icon={TrendingDown}
                    color={totalDowntimeMinutes > 0 ? 'text-red-600' : 'text-emerald-600'}
                />
            </div>
```

Replace with:

```tsx
            {/* Fleet KPI row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiTrendCard
                    index={0}
                    label="Disponibilité moyenne"
                    icon={Activity}
                    valueFormatted={`${avgUptimePct.toFixed(1)}%`}
                    valueColorClass={avgUptimePct >= 95 ? 'text-emerald-600' : avgUptimePct >= 85 ? 'text-blue-600' : 'text-red-600'}
                    trend={kpiTrends.availability}
                    targetLabel="Cible 95%"
                    captionSuffix="Flotte complète · 90j"
                />
                <KpiTrendCard
                    index={1}
                    label="MTTR moyen"
                    icon={Zap}
                    valueFormatted={avgMttr !== null ? formatDuration(avgMttr) : 'N/A'}
                    trend={kpiTrends.mttr}
                    targetLabel="Cible 24h"
                    captionSuffix="Temps moyen de réparation"
                />
                <KpiTrendCard
                    index={2}
                    label="MTBF moyen"
                    icon={Clock}
                    valueFormatted={avgMtbf !== null ? formatHours(avgMtbf) : 'N/A'}
                    trend={kpiTrends.mtbf}
                    targetLabel="Cible 30j"
                    captionSuffix="Temps entre pannes"
                />
                <KpiTrendCard
                    index={3}
                    label="Arrêt total cumulé"
                    icon={TrendingDown}
                    valueFormatted={formatDuration(totalDowntimeMinutes)}
                    valueColorClass={totalDowntimeMinutes > 0 ? 'text-red-600' : 'text-emerald-600'}
                    trend={kpiTrends.downtime}
                    captionSuffix="Toutes machines · 90j"
                />
            </div>
```

- [ ] **Step 5: Type-check**

Run (from `app/frontend/`): `pnpm exec tsc -p tsconfig.app.json --noEmit`
Expected: no errors. (This also catches an unused `Intervention` type import if it became unused — it hasn't, `byMachine` still types against it.)

- [ ] **Step 6: Lint**

Run (from `app/frontend/`): `pnpm run lint`
Expected: no errors.

- [ ] **Step 7: Manual browser verification**

1. Start the frontend dev server (Vite) via the preview tool.
2. Navigate to `/admin/dashboard` (or `/cheftech/dashboard`), log in if needed, click the "Fiabilité" tab.
3. Confirm via screenshot + accessibility snapshot:
   - 4 cards render, each with: icon+label top-left, value, % delta badge top-right (or no badge if `previous` data is unavailable), a filled area chart, x-axis date labels at start/end of the chart, and a caption line.
   - Disponibilité, MTTR, and MTBF cards show a dashed target reference line; Arrêt total cumulé does not.
   - Cards fade/slide in with a slight stagger on load (visually, or confirm via the `initial`/`animate` props being present — a static screenshot won't show animation, so this is a code-review check, not a pixel check).
   - Grid stays 2 columns at mobile width, 4 columns at desktop width (use `preview_resize` to check both).
4. Check `preview_console_logs` for errors (level: `error`) — expect none.

- [ ] **Step 8: Commit**

```bash
git add app/frontend/src/modules/shared/ReliabilityDashboardTab.tsx
git commit -m "feat(reliability): wire KPI trend cards into Fiabilité tab"
```
