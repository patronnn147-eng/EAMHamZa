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
            const start = new Date(i.date_debut!);
            const end = new Date(i.date_fin!);
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
        ? entriesWithMttr.reduce((s, e) => s + e.metrics.mttr!, 0) / entriesWithMttr.length
        : null;

    const entriesWithMtbf = entries.filter((e) => e.metrics.mtbf !== null);
    const avgMtbf = entriesWithMtbf.length > 0
        ? entriesWithMtbf.reduce((s, e) => s + e.metrics.mtbf!, 0) / entriesWithMtbf.length
        : null;

    const totalDowntimeMinutes = entries.reduce((s, e) => s + e.metrics.totalDowntimeMinutes, 0);
    const criticalCount = entries.filter((e) => e.metrics.classification === 'Critique').length;
    const goodCount = entries.filter(
        (e) => e.metrics.classification === 'Excellent' || e.metrics.classification === 'Bon'
    ).length;

    return { entries, avgUptimePct, avgMttr, avgMtbf, totalDowntimeMinutes, criticalCount, goodCount };
}
