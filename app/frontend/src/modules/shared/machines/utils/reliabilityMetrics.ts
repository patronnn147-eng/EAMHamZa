/**
 * Reliability & Downtime Metrics
 * Computes MTTR, MTBF, uptime %, downtime events, and reliability score
 * from a machine's intervention history.
 */

import type { Intervention } from '@/lib/types';

export interface DowntimeEvent {
    id: number;
    start: Date;
    end: Date;
    durationMinutes: number;
    technicienId?: number;
    rapport?: string;
}

export interface ReliabilityMetrics {
    /** Mean Time To Repair (minutes) */
    mttr: number | null;
    /** Mean Time Between Failures (hours) */
    mtbf: number | null;
    /** Uptime percentage (0-100) */
    uptimePct: number;
    /** Total downtime in minutes */
    totalDowntimeMinutes: number;
    /** Total failures (completed interventions with tracked time) */
    failureCount: number;
    /** Downtime events with full detail */
    downtimeEvents: DowntimeEvent[];
    /** Reliability score 0-100 */
    reliabilityScore: number;
    /** Classification label */
    classification: 'Excellent' | 'Bon' | 'Moyen' | 'Critique';
    /** Tailwind CSS color classes for bar */
    colorClass: string;
    /** Analysis window in days */
    windowDays: number;
}

/** Format minutes into e.g. "2h 30m" or "45m" */
export function formatDuration(minutes: number): string {
    if (minutes < 1) return '<1m';
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    if (h === 0) return `${m}m`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}m`;
}

/** Format hours into "X j Y h" or "Y h Z m" */
export function formatHours(hours: number): string {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    const d = Math.floor(hours / 24);
    const h = Math.round(hours % 24);
    if (d === 0) return `${h}h`;
    if (h === 0) return `${d}j`;
    return `${d}j ${h}h`;
}

/**
 * Compute reliability metrics from an array of interventions.
 * Only uses interventions that have both date_debut and date_fin
 * (i.e., fully logged downtime events), within the given window.
 */
export function computeReliabilityMetrics(
    interventions: Intervention[],
    windowDays = 90
): ReliabilityMetrics {
    const cutoff = new Date(Date.now() - windowDays * 24 * 60 * 60 * 1000);

    // Filter to recent completed (has start + end time)
    const completedWithTime = interventions.filter((i) => {
        if (!i.date_debut || !i.date_fin) return false;
        const start = new Date(i.date_debut);
        return start >= cutoff;
    });

    // Build downtime events
    const downtimeEvents: DowntimeEvent[] = completedWithTime
        .map((i) => {
            const start = new Date(i.date_debut);
            const end = new Date(i.date_fin);
            const durationMinutes = Math.max(0, (end.getTime() - start.getTime()) / 60000);
            return {
                id: i.id,
                start,
                end,
                durationMinutes,
                technicienId: i.technicien_id,
                rapport: i.rapport,
            };
        })
        .filter((e) => e.durationMinutes > 0)
        .sort((a, b) => b.start.getTime() - a.start.getTime());

    const failureCount = downtimeEvents.length;
    const totalDowntimeMinutes = downtimeEvents.reduce((sum, e) => sum + e.durationMinutes, 0);

    // MTTR = total downtime / number of failures (in minutes)
    const mttr = failureCount > 0 ? totalDowntimeMinutes / failureCount : null;

    // MTBF calculation: average time between consecutive failures (in hours)
    // If we have 2+ events, sort ascending by start and compute gaps
    let mtbf: number | null = null;
    if (failureCount >= 2) {
        const sortedAsc = [...downtimeEvents].sort((a, b) => a.start.getTime() - b.start.getTime());
        let gapTotal = 0;
        for (let i = 1; i < sortedAsc.length; i++) {
            const gap = (sortedAsc[i].start.getTime() - sortedAsc[i - 1].end.getTime()) / 3600000;
            if (gap > 0) gapTotal += gap;
        }
        mtbf = gapTotal / (failureCount - 1);
    } else if (failureCount === 1) {
        // Single failure: MTBF = window time minus downtime
        const windowHours = windowDays * 24;
        const downtimeHours = totalDowntimeMinutes / 60;
        mtbf = windowHours - downtimeHours;
    }

    // Uptime % = (window minutes - total downtime minutes) / window minutes * 100
    const windowMinutes = windowDays * 24 * 60;
    const uptimePct = Math.max(0, Math.min(100,
        ((windowMinutes - totalDowntimeMinutes) / windowMinutes) * 100
    ));

    // Reliability score (0-100): weighted combo of uptime% and failure frequency
    const failurePenalty = Math.min(50, failureCount * 5);
    const reliabilityScore = Math.round(Math.max(0, uptimePct - failurePenalty * 0.5));

    let classification: ReliabilityMetrics['classification'];
    let colorClass: string;
    if (reliabilityScore >= 90) {
        classification = 'Excellent';
        colorClass = 'from-emerald-400 to-emerald-500';
    } else if (reliabilityScore >= 75) {
        classification = 'Bon';
        colorClass = 'from-blue-400 to-blue-500';
    } else if (reliabilityScore >= 50) {
        classification = 'Moyen';
        colorClass = 'from-amber-400 to-amber-500';
    } else {
        classification = 'Critique';
        colorClass = 'from-red-400 to-red-600';
    }

    return {
        mttr,
        mtbf,
        uptimePct,
        totalDowntimeMinutes,
        failureCount,
        downtimeEvents,
        reliabilityScore,
        classification,
        colorClass,
        windowDays,
    };
}

/**
 * Compute fleet reliability summary from multiple machines' interventions.
 * Returns per-machine reliability plus aggregate fleet metrics.
 */
export interface FleetReliabilityEntry {
    machineId: number;
    machineName: string;
    metrics: ReliabilityMetrics;
}

export interface FleetReliabilitySummary {
    entries: FleetReliabilityEntry[];
    avgUptimePct: number;
    avgMttr: number | null;
    avgMtbf: number | null;
    totalDowntimeMinutes: number;
    criticalCount: number;
    goodCount: number;
}

export function computeFleetReliability(
    machines: Array<{ id: number; nom: string }>,
    interventionsByMachineId: Record<number, Intervention[]>,
    windowDays = 90
): FleetReliabilitySummary {
    const entries: FleetReliabilityEntry[] = machines.map((m) => ({
        machineId: m.id,
        machineName: m.nom,
        metrics: computeReliabilityMetrics(interventionsByMachineId[m.id] ?? [], windowDays),
    }));

    const avgUptimePct = entries.length > 0
        ? entries.reduce((s, e) => s + e.metrics.uptimePct, 0) / entries.length
        : 100;

    const entriesWithMttr = entries.filter((e) => e.metrics.mttr !== null);
    const avgMttr = entriesWithMttr.length > 0
        ? entriesWithMttr.reduce((s, e) => s + e.metrics.mttr, 0) / entriesWithMttr.length
        : null;

    const entriesWithMtbf = entries.filter((e) => e.metrics.mtbf !== null);
    const avgMtbf = entriesWithMtbf.length > 0
        ? entriesWithMtbf.reduce((s, e) => s + e.metrics.mtbf, 0) / entriesWithMtbf.length
        : null;

    const totalDowntimeMinutes = entries.reduce((s, e) => s + e.metrics.totalDowntimeMinutes, 0);
    const criticalCount = entries.filter((e) => e.metrics.classification === 'Critique').length;
    const goodCount = entries.filter(
        (e) => e.metrics.classification === 'Excellent' || e.metrics.classification === 'Bon'
    ).length;

    return { entries, avgUptimePct, avgMttr, avgMtbf, totalDowntimeMinutes, criticalCount, goodCount };
}

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
            current: current.mttrMinutes === null ? 0 : Math.round(current.mttrMinutes),
            previous: previous.mttrMinutes === null ? null : Math.round(previous.mttrMinutes),
            pctChange: pctChange(current.mttrMinutes ?? 0, previous.mttrMinutes),
            goodDirection: 'down',
            target: 1440,
        },
        mtbf: {
            series: mtbfSeries,
            current: current.mtbfHours === null ? 0 : Math.round(current.mtbfHours),
            previous: previous.mtbfHours === null ? null : Math.round(previous.mtbfHours),
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
