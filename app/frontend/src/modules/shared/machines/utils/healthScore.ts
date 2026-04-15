import type { Machine } from '@/lib/types';

export interface HealthScoreFactors {
    daysSinceLastMaintenance: number;
    openWorkOrders: number;
    recentInterventions: number;
    isDown: boolean;
}

export interface HealthScoreDeductions {
    maintenance: number;
    overdue: number;
    workOrders: number;
    interventions: number;
    status: number;
    predictive: number;
}

export interface HealthScoreResult {
    score: number;
    label: string;
    colorClass: string;
    barGradient: string;
    textColor: string;
    iconColor: string;
    factors: HealthScoreFactors;
    deductions: HealthScoreDeductions;
    // DST fusion metadata (present when score_source === "dst_fusion")
    dst_verdict?: "Healthy" | "Degrading" | "Critical" | "Unknown";
    conflict_k?: number;
    score_source?: "dst_fusion" | "fallback_additive";
}

/**
 * COMPATIBILITY LAYER: computeHealthScore
 * This remains the entry point for most UI components (Grids, Tabs).
 * It performs basic operational scoring and merges ML data if provided.
 */
export function computeHealthScore(
    machine: Machine,
    openWorkOrders = 0,
    recentInterventions = 0,
    mlHealthData?: any
): HealthScoreResult {
    // 1. If we have full ML data, use the specialized mapper
    if (mlHealthData) {
        return computeHealthScoreFromML(machine, mlHealthData);
    }

    // 2. Fallback: Basic Operational Health (for Grid/List views)
    const now = new Date();
    const daysSinceLastMaintenance = machine.date_derniere_maintenance
        ? Math.floor((now.getTime() - new Date(machine.date_derniere_maintenance).getTime()) / (1000 * 60 * 60 * 24))
        : -1;

    const isDown = machine.statut === 'EN_PANNE' || machine.statut === 'HORS_SERVICE';

    const deductions: HealthScoreDeductions = {
        maintenance: daysSinceLastMaintenance > 0 ? Math.min(daysSinceLastMaintenance * 0.5, 30) : 0,
        overdue: 0,
        workOrders: Math.min(openWorkOrders * 12, 36),
        interventions: Math.min(recentInterventions * 10, 30),
        status: isDown ? 60 : 0,
        predictive: 0
    };

    if (machine.date_prochaine_maintenance) {
        const nextMaint = new Date(machine.date_prochaine_maintenance);
        if (now > nextMaint) {
            const daysOverdue = Math.floor((now.getTime() - nextMaint.getTime()) / (1000 * 60 * 60 * 24));
            deductions.overdue = Math.min(daysOverdue * 2, 40);
        }
    }

    const score = Math.max(0, Math.min(100, Math.round(100 - (deductions.maintenance + deductions.overdue + deductions.workOrders + deductions.interventions + deductions.status))));

    const baseResult = {
        score,
        factors: { daysSinceLastMaintenance, openWorkOrders, recentInterventions, isDown },
        deductions,
    };

    return finalizeResult(baseResult, false);
}

/**
 * Specialized ML Mapper for Detail Pages.
 * Prefers unified_health_score (DST fusion) over legacy health_score when available.
 */
export function computeHealthScoreFromML(
    machine: Machine,
    mlHealthData: any
): HealthScoreResult {
    if (!mlHealthData) return getNeutralHealth();

    const { health_breakdown } = mlHealthData;

    // Prefer DST-fused score; fall back to legacy health_score
    const rawScore =
        mlHealthData.unified_health_score ??
        mlHealthData.health_score ??
        0;
    const score = Math.max(0, Math.min(100, Math.round(rawScore)));
    const breakdown = health_breakdown || {};

    // DST fusion metadata
    const scoreSource: "dst_fusion" | "fallback_additive" =
        breakdown.score_source ?? (mlHealthData.unified_health_score != null ? "dst_fusion" : "fallback_additive");
    const dstVerdict = breakdown.dst_verdict ?? mlHealthData.dst_verdict;
    const conflictK = breakdown.conflict_factor_K ?? mlHealthData.conflict_factor_K;

    const baseResult = {
        score,
        factors: {
            daysSinceLastMaintenance: breakdown.days_since_maintenance ?? -1,
            openWorkOrders: breakdown.open_work_orders ?? 0,
            recentInterventions: breakdown.recent_interventions ?? 0,
            isDown: machine.statut === 'EN_PANNE' || machine.statut === 'HORS_SERVICE',
        },
        deductions: {
            maintenance: breakdown.maintenance_deduction ?? 0,
            overdue: breakdown.overdue_deduction ?? 0,
            workOrders: breakdown.work_order_deduction ?? 0,
            interventions: breakdown.intervention_deduction ?? 0,
            status: breakdown.status_deduction ?? 0,
            // anomaly_penalty removed — DST fusion handles anomaly signal correctly
            predictive: breakdown.predictive_risk ?? 0,
        },
        score_source: scoreSource,
        dst_verdict: dstVerdict,
        conflict_k: conflictK,
    };

    return finalizeResult(baseResult, true);
}

function finalizeResult(base: any, isIA: boolean): HealthScoreResult {
    const { score } = base;
    const suffix = isIA ? ' (IA)' : '';
    
    if (score >= 80) {
        return {
            ...base,
            label: `Bonne Condition${suffix}`,
            colorClass: 'from-emerald-400 to-emerald-600',
            barGradient: 'bg-gradient-to-r from-emerald-400 to-emerald-600',
            textColor: 'text-emerald-600',
            iconColor: 'text-emerald-500',
        };
    } else if (score >= 60) {
        return {
            ...base,
            label: `Attention Requise${suffix}`,
            colorClass: 'from-amber-400 to-amber-600',
            barGradient: 'bg-gradient-to-r from-amber-400 to-amber-600',
            textColor: 'text-amber-600',
            iconColor: 'text-amber-500',
        };
    } else {
        return {
            ...base,
            label: `État Critique${suffix}`,
            colorClass: 'from-red-400 to-red-600',
            barGradient: 'bg-gradient-to-r from-red-400 to-red-600',
            textColor: 'text-red-600',
            iconColor: 'text-red-500',
        };
    }
}

function getNeutralHealth(): HealthScoreResult {
    return {
        score: 100,
        label: 'Analyse en cours...',
        colorClass: 'from-gray-400 to-gray-600',
        barGradient: 'bg-gray-200',
        textColor: 'text-gray-500',
        iconColor: 'text-gray-400',
        factors: { daysSinceLastMaintenance: -1, openWorkOrders: 0, recentInterventions: 0, isDown: false },
        deductions: { maintenance: 0, overdue: 0, workOrders: 0, interventions: 0, status: 0, predictive: 0 }
    };
}

export function formatDuration(days: number): string {
    if (days < 0) return "Aucune";
    if (days === 0) return "Aujourd'hui";
    if (days === 1) return 'Hier';
    if (days < 30) return `${days} jours`;
    if (days < 365) return `${Math.floor(days / 30)} mois`;
    return `${Math.floor(days / 365)} an${Math.floor(days / 365) > 1 ? 's' : ''}`;
}
