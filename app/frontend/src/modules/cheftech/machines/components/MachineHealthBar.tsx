import React from 'react';
import type { HealthScoreResult } from '../utils/healthScore';

interface MachineHealthBarProps {
    health: HealthScoreResult;
    compact?: boolean;
}

/**
 * Gradient progress bar showing machine health score (0–100).
 * compact=true → used inside machine cards (minimal height).
 */
const MachineHealthBar: React.FC<MachineHealthBarProps> = ({ health, compact = false }) => {
    const { score, label, barGradient, textColor } = health;

    if (compact) {
        return (
            <div className="space-y-1">
                <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500 font-medium">Santé Machine</span>
                    <span className={`text-xs font-bold ${textColor}`}>{score}/100</span>
                </div>
                {/* Bar */}
                <div className="relative h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                    <div
                        className={`h-2 rounded-full ${barGradient} transition-all duration-700 ease-out`}
                        style={{ width: `${score}%` }}
                    />
                </div>
                <div className={`text-xs font-medium ${textColor}`}>{label}</div>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">Score de Santé</span>
                <span className={`text-2xl font-black ${textColor}`}>{score}<span className="text-sm font-normal text-gray-400">/100</span></span>
            </div>
            <div className="relative h-3 w-full rounded-full bg-gray-100 overflow-hidden shadow-inner">
                <div
                    className={`h-3 rounded-full ${barGradient} transition-all duration-1000 ease-out shadow-sm`}
                    style={{ width: `${score}%` }}
                />
            </div>
            <div className={`text-sm font-semibold uppercase tracking-wide ${textColor}`}>{label}</div>
        </div>
    );
};

export default MachineHealthBar;
