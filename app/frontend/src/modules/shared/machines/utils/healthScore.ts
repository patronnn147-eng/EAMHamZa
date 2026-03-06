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
}

/**
 * Compute a machine health score (0–100) from live factors.
 */
export function computeHealthScore(
    machine: Machine,
    openWorkOrders = 0,
    recentInterventions = 0
): HealthScoreResult {
    const now = new Date();

    const daysSinceLastMaintenance = machine.date_derniere_maintenance
        ? Math.floor(
            (now.getTime() - new Date(machine.date_derniere_maintenance).getTime()) /
            (1000 * 60 * 60 * 24)
        )
        : 60;

    const isDown =
        machine.statut === 'EN_PANNE' || machine.statut === 'HORS_SERVICE';

    const deductions: HealthScoreDeductions = {
        maintenance: Math.min(daysSinceLastMaintenance * 0.5, 30),
        overdue: 0,
        workOrders: Math.min(openWorkOrders * 12, 36),
        interventions: Math.min(recentInterventions * 10, 30),
        status: isDown ? 60 : 0
    };

    // Calculate overdue deduction
    if (machine.date_prochaine_maintenance) {
        const nextMaint = new Date(machine.date_prochaine_maintenance);
        if (now > nextMaint) {
            const daysOverdue = Math.floor((now.getTime() - nextMaint.getTime()) / (1000 * 60 * 60 * 24));
            deductions.overdue = Math.min(daysOverdue * 2, 40);
        }
    }

    let score = 100 - (deductions.maintenance + deductions.overdue + deductions.workOrders + deductions.interventions + deductions.status);
    const finalScore = Math.max(0, Math.min(100, Math.round(score)));

    const factors: HealthScoreFactors = {
        daysSinceLastMaintenance,
        openWorkOrders,
        recentInterventions,
        isDown,
    };

    const baseResult = {
        score: finalScore,
        factors,
        deductions,
    };

    if (finalScore >= 80) {
        return {
            ...baseResult,
            label: 'Bonne Condition',
            colorClass: 'from-emerald-400 to-emerald-600',
            barGradient: 'bg-gradient-to-r from-emerald-400 to-emerald-600',
            textColor: 'text-emerald-600',
            iconColor: 'text-emerald-500',
        };
    } else if (finalScore >= 60) {
        return {
            ...baseResult,
            label: 'Attention Requise',
            colorClass: 'from-amber-400 to-amber-600',
            barGradient: 'bg-gradient-to-r from-amber-400 to-amber-600',
            textColor: 'text-amber-600',
            iconColor: 'text-amber-500',
        };
    } else {
        return {
            ...baseResult,
            label: 'État Critique',
            colorClass: 'from-red-400 to-red-600',
            barGradient: 'bg-gradient-to-r from-red-400 to-red-600',
            textColor: 'text-red-600',
            iconColor: 'text-red-500',
        };
    }
}

export function formatDuration(days: number): string {
    if (days === 0) return "Aujourd'hui";
    if (days === 1) return 'Hier';
    if (days < 30) return `${days} jours`;
    if (days < 365) return `${Math.floor(days / 30)} mois`;
    return `${Math.floor(days / 365)} an${Math.floor(days / 365) > 1 ? 's' : ''}`;
}
