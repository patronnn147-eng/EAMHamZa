/**
 * ReadinessScoreTile — P7.5 — 0-100 machine readiness gauge.
 * Fetches from /api/v1/ml/machines/:id/readiness on mount.
 * Plain language: no ML jargon.
 */
import React, { useEffect, useState } from 'react';

const API      = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface ReadinessData {
    readiness_score: number;
    breakdown: {
        health: number;
        inventory_coverage: number;
        procurement_risk: number;
        maintenance_recency: number;
    };
    inputs: {
        unified_health_score: number;
        inventory_coverage_pct: number;
        parts_shortage_active: boolean;
        days_since_last_maintenance: number | null;
    };
}

interface Props { machineId: number }

const glass: React.CSSProperties = {
    background: 'rgba(255,255,255,0.03)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '1.5rem',
};

function scoreColor(score: number): string {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#00f2ff';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
}

function scoreLabel(score: number): string {
    if (score >= 80) return 'Ready';
    if (score >= 60) return 'Adequate';
    if (score >= 40) return 'At Risk';
    return 'Not Ready';
}

export function ReadinessScoreTile({ machineId }: Readonly<Props>) {
    const [data, setData]     = useState<ReadinessData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API}/api/v1/ml/machines/${machineId}/readiness`, {
                    headers: { Authorization: `Bearer ${getToken()}` },
                });
                if (res.ok) {
                    const json = await res.json();
                    setData(json);
                }
            } catch { /* silent */ }
            finally { setLoading(false); }
        })();
    }, [machineId]);

    if (loading) {
        return (
            <div style={{ ...glass, padding: '1.25rem', marginTop: '0.75rem' }}>
                <p style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>
                    Loading readiness score…
                </p>
            </div>
        );
    }
    if (!data) return null;

    const score  = data.readiness_score;
    const color  = scoreColor(score);
    const label  = scoreLabel(score);
    const r      = 44;
    const circ   = 2 * Math.PI * r;
    const offset = circ * (1 - score / 100);

    const bars = [
        { key: 'health',              label: 'Machine condition', val: data.breakdown.health,              max: 40 },
        { key: 'inventory_coverage',  label: 'Parts in stock',    val: data.breakdown.inventory_coverage,  max: 30 },
        { key: 'procurement_risk',    label: 'No shortage active', val: data.breakdown.procurement_risk,   max: 20 },
        { key: 'maintenance_recency', label: 'Recent maintenance', val: data.breakdown.maintenance_recency, max: 10 },
    ];

    return (
        <div style={{ ...glass, border: `1px solid ${color}33`, boxShadow: `0 0 20px ${color}10`, padding: '1.25rem', marginTop: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>
                    Maintenance Readiness
                </h4>
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'Space Grotesk, monospace', background: `${color}18`, padding: '0.2rem 0.6rem', borderRadius: 999 }}>
                    {label}
                </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                {/* Mini donut */}
                <div style={{ position: 'relative', flexShrink: 0 }}>
                    <svg width="96" height="96" style={{ transform: 'rotate(-90deg)' }}>
                        <circle cx="48" cy="48" r={r} stroke="rgba(255,255,255,0.05)" strokeWidth="8" fill="transparent" />
                        <circle cx="48" cy="48" r={r} stroke={color} strokeWidth="8" fill="transparent"
                            strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
                            style={{ transition: 'stroke-dashoffset 1s ease' }}
                        />
                    </svg>
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', lineHeight: 1, fontFamily: 'Manrope, sans-serif' }}>{Math.round(score)}</span>
                        <span style={{ fontSize: '0.5rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>/100</span>
                    </div>
                </div>

                {/* Breakdown bars */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {bars.map(b => (
                        <div key={b.key}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                                <span style={{ fontSize: '0.6rem', color: '#64748b', fontFamily: 'Space Grotesk, monospace' }}>{b.label}</span>
                                <span style={{ fontSize: '0.6rem', color: '#fff', fontFamily: 'Space Grotesk, monospace' }}>{b.val.toFixed(1)}/{b.max}</span>
                            </div>
                            <div style={{ height: '2px', background: 'rgba(255,255,255,0.05)', borderRadius: 9999 }}>
                                <div style={{ width: `${Math.min(100, (b.val / b.max) * 100)}%`, height: '100%', background: color, transition: 'width 0.8s ease' }} />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {data.inputs.parts_shortage_active && (
                <p style={{ fontSize: '0.55rem', color: '#f97316', marginTop: '0.75rem', fontFamily: 'Space Grotesk, monospace' }}>
                    ⚠ Parts shortage is reducing readiness score.
                </p>
            )}
        </div>
    );
}
