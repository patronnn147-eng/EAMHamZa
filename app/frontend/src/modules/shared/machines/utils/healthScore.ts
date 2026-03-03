import type { Machine } from '@/lib/types';

export interface HealthScoreFactors {
    daysSinceLastMaintenance: number;
    openWorkOrders: number;
    recentInterventions: number;
    isDown: boolean;
}

export interface HealthScoreResult {
    score: number;
    label: string;
    colorClass: string;
    barGradient: string;
    textColor: string;
    iconColor: string;
    factors: HealthScoreFactors;
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

    let score = 100;
    score -= Math.min(daysSinceLastMaintenance * 0.5, 30); // max -30
    score -= Math.min(openWorkOrders * 10, 30);             // max -30
    score -= Math.min(recentInterventions * 8, 24);         // max -24
    if (isDown) score -= 30;

    const finalScore = Math.max(0, Math.min(100, Math.round(score)));

    const factors: HealthScoreFactors = {
        daysSinceLastMaintenance,
        openWorkOrders,
        recentInterventions,
        isDown,
    };

    if (finalScore >= 80) {
        return {
            score: finalScore,
            label: 'Bonne Condition',
            colorClass: 'from-emerald-400 to-emerald-600',
            barGradient: 'bg-gradient-to-r from-emerald-400 to-emerald-600',
            textColor: 'text-emerald-600',
            iconColor: 'text-emerald-500',
            factors,
        };
    } else if (finalScore >= 60) {
        return {
            score: finalScore,
            label: 'Attention Requise',
            colorClass: 'from-amber-400 to-amber-600',
            barGradient: 'bg-gradient-to-r from-amber-400 to-amber-600',
            textColor: 'text-amber-600',
            iconColor: 'text-amber-500',
            factors,
        };
    } else {
        return {
            score: finalScore,
            label: 'État Critique',
            colorClass: 'from-red-400 to-red-600',
            barGradient: 'bg-gradient-to-r from-red-400 to-red-600',
            textColor: 'text-red-600',
            iconColor: 'text-red-500',
            factors,
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
