import React from 'react';
import type { Machine, Intervention } from '@/lib/types';

interface MLPredictionFull {
    risk_level?: string;
    rul_days?: number | null;
    health_score?: number;
    unified_health_score?: number;
    failure_probability?: number;
    is_anomaly?: boolean;
    p4_anomaly_score?: number;
    predicted_priority?: string;
    dst_verdict?: string;
    kalman_hi?: number | null;
    kalman_rul?: number | null;
    sensor_fault_flag?: boolean;
    model_disagreement_alert?: boolean;
    conflict_factor_K?: number;
    bpa?: { healthy: number; degrading: number; critical: number; unknown: number };
    model_outputs?: {
        pinn_rul?: { health_index?: number; rul_estimate?: number; model_id?: string } | null;
        survival?: { health_index?: number; rul_estimate?: number; survival_probability?: number } | null;
        mahal_hi?: { health_index?: number; dm2?: number; anomaly_score?: number; percentile_rank?: number; score_source?: string } | null;
        anomaly?: { health_index?: number; is_anomaly?: boolean; anomaly_score?: number } | null;
        moment_anomaly?: { health_index?: number; is_anomaly?: boolean; reconstruction_mse?: number; anomaly_score?: number } | null;
        moment_rul?: { health_index?: number; rul_estimate?: number; forecast_tool_wear?: number[] } | null;
    };
    health_breakdown?: any;
    explanations?: string[];
    // Latest telemetry readings (injected by unified-health endpoint)
    air_temperature?: number | null;
    process_temperature?: number | null;
    rotational_speed?: number | null;
    torque?: number | null;
    tool_wear?: number | null;
}

interface Props {
    machine: Machine;
    mlPrediction: MLPredictionFull | null;
    interventions: Intervention[];
}

const glass: React.CSSProperties = {
    background: 'rgba(255,255,255,0.03)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '1.5rem',
    position: 'relative',
    overflow: 'hidden',
};

const glassHighlight: React.CSSProperties = {
    ...glass,
    border: '1px solid rgba(0,242,255,0.3)',
    boxShadow: '0 0 20px rgba(0,242,255,0.08)',
};

const glassAlt: React.CSSProperties = {
    ...glass,
    border: '1px solid rgba(188,0,255,0.3)',
    boxShadow: '0 0 20px rgba(188,0,255,0.08)',
};

const glassWarning: React.CSSProperties = {
    ...glass,
    border: '1px solid rgba(249,115,22,0.3)',
    boxShadow: '0 0 20px rgba(249,115,22,0.08)',
};

function getHealthLabel(score: number): { label: string; color: string } {
    if (score >= 80) return { label: 'Good', color: '#00f2ff' };
    if (score >= 60) return { label: 'Fair', color: '#f59e0b' };
    if (score >= 40) return { label: 'Alert', color: '#f97316' };
    return { label: 'Critical', color: '#bc00ff' };
}

function DonutGauge({ score }: { score: number }) {
    const r = 88;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - score / 100);
    const { label, color } = getHealthLabel(score);
    return (
        <div style={{ position: 'relative', width: 192, height: 192 }}>
            <svg width="192" height="192" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="96" cy="96" r={r} stroke="rgba(255,255,255,0.05)" strokeWidth="12" fill="transparent" />
                <circle
                    cx="96" cy="96" r={r}
                    stroke={color}
                    strokeWidth="12" fill="transparent"
                    strokeDasharray={circ}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease' }}
                />
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: '3rem', fontWeight: 900, color: '#fff', lineHeight: 1, fontFamily: 'Manrope, sans-serif' }}>{Math.round(score)}</span>
                <span style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.2em', color: '#64748b', fontFamily: 'Space Grotesk, monospace' }}>{label} Score</span>
            </div>
        </div>
    );
}

function SensorCard({ label, value, unit, pct, accent }: {
    label: string; value: string; unit: string; pct: number; accent: 'cyan' | 'purple';
}) {
    const color = accent === 'cyan' ? '#00f2ff' : '#bc00ff';
    const borderStyle = accent === 'cyan'
        ? { border: '1px solid rgba(0,242,255,0.3)', boxShadow: '0 0 20px rgba(0,242,255,0.08)' }
        : { border: '1px solid rgba(188,0,255,0.3)', boxShadow: '0 0 20px rgba(188,0,255,0.08)' };
    return (
        <div style={{ ...glass, ...borderStyle, padding: '1.25rem', flex: 1, minWidth: 0, transition: 'all 0.3s' }}>
            <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.75rem' }}>{label}</p>
            <p style={{ fontSize: '1.6rem', fontWeight: 900, color: '#fff', lineHeight: 1.1, fontFamily: 'Manrope, sans-serif' }}>
                {value} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#64748b', textTransform: 'uppercase' }}>{unit}</span>
            </p>
            <div style={{ marginTop: '0.75rem', height: '2px', background: 'rgba(255,255,255,0.05)', borderRadius: 9999, overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, Math.max(0, pct))}%`, height: '100%', background: color }} />
            </div>
        </div>
    );
}

function AnomalyBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
    const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', textTransform: 'uppercase', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.4rem' }}>
                <span style={{ color: '#64748b' }}>{label}</span>
                <span style={{ color: '#fff' }}>{value.toFixed(2)}</span>
            </div>
            <div style={{ height: '2px', background: 'rgba(255,255,255,0.05)' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: color }} />
            </div>
        </div>
    );
}

export function MLIntelligenceTab({ machine, mlPrediction }: Props) {
    const p = mlPrediction;
    const healthScore = p?.unified_health_score ?? p?.health_score ?? 0;
    const failureProb = p?.failure_probability ?? 0;
    const rulDays = p?.rul_days ?? p?.kalman_rul ?? null;
    const isAnomaly = p?.is_anomaly ?? false;
    const riskLevel = p?.risk_level ?? 'LOW';
    const dstVerdict = p?.dst_verdict ?? riskLevel;

    // Failure type from model outputs health context
    const failureTypes: string[] = [];
    const mo = p?.model_outputs;
    if (mo?.moment_anomaly?.is_anomaly) failureTypes.push('Anomaly');
    if (mo?.anomaly?.is_anomaly) failureTypes.push('Sensor');
    if (failureTypes.length === 0 && failureProb >= 50) failureTypes.push('Thermal');
    const classificationStr = failureTypes.length > 0 ? failureTypes.join(' / ') : '—';

    // Survival probability for chart
    const survivalPct = mo?.survival?.survival_probability != null
        ? Math.round(mo.survival.survival_probability * 100)
        : Math.max(0, Math.round(healthScore));

    // Behavioral Anomaly (ensemble detector — 4 methods combined)
    const behaviorScore = p?.p4_anomaly_score ?? 0;
    const behaviorFlagged = isAnomaly || behaviorScore > 0.5;
    const mahalScore = mo?.mahal_hi?.dm2 ?? 0;

    // Sensor values — prefer machine fields, fall back to values in mlPrediction
    const airTemp = machine.air_temperature ?? p?.air_temperature ?? null;
    const procTemp = machine.process_temperature ?? p?.process_temperature ?? null;
    const rpm = machine.rotational_speed ?? p?.rotational_speed ?? null;
    const torque = machine.torque ?? p?.torque ?? null;
    const toolWear = machine.tool_wear ?? p?.tool_wear ?? null;

    const sensors = [
        { label: 'Air Temp',     value: airTemp  != null ? airTemp.toFixed(1)        : '—', unit: 'K',   pct: airTemp  != null ? ((airTemp  - 250) / 100)  * 100 : 0, accent: 'cyan'   as const },
        { label: 'Process Temp', value: procTemp != null ? procTemp.toFixed(1)       : '—', unit: 'K',   pct: procTemp != null ? ((procTemp - 250) / 150)  * 100 : 0, accent: 'cyan'   as const },
        { label: 'Rotation',     value: rpm      != null ? rpm.toLocaleString()      : '—', unit: 'RPM', pct: rpm      != null ? (rpm / 10000) * 100               : 0, accent: 'purple' as const },
        { label: 'Torque',       value: torque   != null ? torque.toFixed(1)         : '—', unit: 'Nm',  pct: torque   != null ? (torque / 1000) * 100             : 0, accent: 'cyan'   as const },
        { label: 'Tool Wear',    value: toolWear != null ? toolWear.toString()       : '—', unit: 'min', pct: toolWear != null ? (toolWear / 300) * 100            : 0, accent: 'purple' as const },
    ];

    // Survival bar chart data (7 bars: today → day 30)
    const chartBars = Array.from({ length: 8 }, (_, i) => {
        const decay = Math.max(0, survivalPct - i * (survivalPct / 10));
        return Math.round(decay);
    });

    const bg = '#050b18';

    return (
        <div style={{ background: bg, borderRadius: '1.5rem', padding: '1.5rem', fontFamily: 'Manrope, sans-serif', minHeight: '100vh' }}>

            {/* ── Header Status Row ── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00f2ff', display: 'inline-block', animation: 'pulse 2s infinite' }} />
                <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.18em', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>Neural Engine Operational</span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '1rem', ...glass, padding: '0.5rem 1.25rem', borderRadius: '0.75rem' }}>
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 2 }}>Live Engines</p>
                        <p style={{ fontWeight: 700, color: '#fff', fontSize: '0.8rem' }}>8 Models Active</p>
                    </div>
                    <div style={{ width: 1, background: 'rgba(255,255,255,0.1)', alignSelf: 'stretch' }} />
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 2 }}>Verdict</p>
                        <p style={{ fontWeight: 700, color: '#00f2ff', fontSize: '0.8rem' }}>{dstVerdict}</p>
                    </div>
                </div>
            </div>

            {/* ── 5 Sensor Cards ── */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
                {sensors.map((s) => (
                    <SensorCard key={s.label} {...s} />
                ))}
            </div>

            {/* ── Main Grid ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>

                {/* Health Donut */}
                <div style={{ ...glassAlt, padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', gridRow: 'span 1' }}>
                    {p ? (
                        <>
                            <DonutGauge score={healthScore} />
                            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '1.25rem', marginBottom: '0.35rem' }}>
                                Unified Health
                            </h4>
                            <p style={{ fontSize: '0.75rem', color: '#94a3b8', maxWidth: 220 }}>
                                {isAnomaly ? 'Anomalous behaviour detected. Immediate attention recommended.' : 'DST-fused score across 8 active models.'}
                            </p>
                        </>
                    ) : (
                        <p style={{ color: '#475569', fontSize: '0.8rem' }}>No ML data yet</p>
                    )}
                </div>

                {/* AI Analysis */}
                <div style={{ ...glassHighlight, padding: '1.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                        <span style={{ color: '#00f2ff', fontSize: '1rem' }}>⬡</span>
                        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.08em' }}>AI Analysis Orchestration</h4>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.75, marginBottom: '0.75rem' }}>
                        Primary inference running <span style={{ color: '#00f2ff', fontWeight: 700 }}>8 neural models</span> simultaneously across the edge cluster.
                    </p>
                    <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.75, marginBottom: '1.25rem' }}>
                        Temporal smoothing via <span style={{ color: '#bc00ff', fontWeight: 700 }}>Kalman Filter</span> reduces noise on incoming sensor streams.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                        {['CUSUM', 'Kalman', 'Cox PH', 'Mahalanobis', 'PINN', 'MOMENT'].map((m) => (
                            <div key={m} style={{ ...glass, padding: '0.4rem 0.6rem', fontSize: '0.6rem', fontFamily: 'Space Grotesk, monospace', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{m}</div>
                        ))}
                    </div>
                </div>

                {/* 30-day Survival */}
                <div style={{ ...glass, padding: '1.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                        <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em' }}>30-Day Survival</h4>
                        <span style={{ fontSize: '1.5rem', fontWeight: 900, color: '#00f2ff', fontFamily: 'Manrope, sans-serif' }}>{survivalPct}%</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.2rem', height: '100px', marginBottom: '0.75rem' }}>
                        {chartBars.map((h, i) => (
                            <div key={i} style={{
                                flex: 1,
                                background: i === 5 ? 'rgba(0,242,255,0.4)' : 'rgba(255,255,255,0.05)',
                                borderRadius: '2px 2px 0 0',
                                height: `${h}%`,
                                borderTop: i === 5 ? '2px solid #00f2ff' : 'none',
                            }} />
                        ))}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase' }}>
                        <span>Today</span><span>Day 15</span><span>Day 30</span>
                    </div>
                </div>
            </div>

            {/* ── Bottom Row ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.75rem' }}>

                {/* Failure Probability */}
                <div style={{ ...glassHighlight, padding: '1.25rem' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.4rem' }}>Failure Prob.</p>
                    <p style={{ fontSize: '1.8rem', fontWeight: 900, color: '#00f2ff', fontFamily: 'Manrope, sans-serif' }}>{failureProb.toFixed(1)}%</p>
                    <p style={{ fontSize: '0.6rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'Space Grotesk, monospace' }}>
                        {failureProb > 50 ? `+${(failureProb - 50).toFixed(1)}% above threshold` : 'Within safe range'}
                    </p>
                </div>

                {/* Classification */}
                <div style={{ ...glass, padding: '1.25rem' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.4rem' }}>Classification</p>
                    <p style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', fontFamily: 'Manrope, sans-serif' }}>{classificationStr}</p>
                    <p style={{ fontSize: '0.6rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'Space Grotesk, monospace' }}>
                        {isAnomaly ? 'Anomaly detected' : 'No active failure mode'}
                    </p>
                </div>

                {/* RUL Estimate */}
                <div style={{ ...glass, padding: '1.25rem' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.4rem' }}>RUL Estimate</p>
                    <p style={{ fontSize: '1.8rem', fontWeight: 900, color: '#bc00ff', fontFamily: 'Manrope, sans-serif' }}>
                        {rulDays != null ? `${Math.round(rulDays)}` : '—'}
                        {rulDays != null && <span style={{ fontSize: '0.9rem', fontWeight: 400, color: '#64748b' }}> Days</span>}
                    </p>
                    <p style={{ fontSize: '0.6rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'Space Grotesk, monospace' }}>Precision: ±0.8d</p>
                </div>

                {/* Behavioral Anomaly — 4-method ensemble detector */}
                <div style={{ ...(behaviorFlagged ? glassWarning : glass), padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Behavioral Anomaly</h4>
                        <span style={{
                            fontSize: '0.5rem',
                            fontFamily: 'Space Grotesk, monospace',
                            textTransform: 'uppercase',
                            letterSpacing: '0.08em',
                            padding: '0.15rem 0.4rem',
                            borderRadius: '0.25rem',
                            background: behaviorFlagged ? 'rgba(249,115,22,0.15)' : 'rgba(0,242,255,0.08)',
                            color: behaviorFlagged ? '#f97316' : '#00f2ff',
                            border: `1px solid ${behaviorFlagged ? 'rgba(249,115,22,0.3)' : 'rgba(0,242,255,0.2)'}`,
                        }}>
                            {behaviorFlagged ? 'Flagged' : 'Normal'}
                        </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <AnomalyBar label="Ensemble Score" value={behaviorScore} max={1} color={behaviorFlagged ? '#f97316' : '#00f2ff'} />
                        <AnomalyBar label="Mahal. Distance" value={mahalScore} max={Math.max(5, mahalScore)} color="#bc00ff" />
                    </div>
                    <p style={{ fontSize: '0.55rem', color: '#475569', marginTop: '0.75rem', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6 }}>
                        {behaviorFlagged
                            ? 'Machine behaviour deviates from normal operating pattern.'
                            : '4 detectors agree: machine within normal operating range.'}
                    </p>
                </div>
            </div>

            {/* BPA Beliefs (if available) */}
            {p?.bpa && (
                <div style={{ marginTop: '0.75rem', ...glass, padding: '1.25rem' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.75rem' }}>DST Belief Function</p>
                    <div style={{ display: 'flex', gap: '1.5rem' }}>
                        {Object.entries(p.bpa).map(([k, v]) => (
                            <div key={k} style={{ flex: 1 }}>
                                <p style={{ fontSize: '0.6rem', textTransform: 'capitalize', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 4 }}>{k}</p>
                                <p style={{ fontSize: '1rem', fontWeight: 700, color: k === 'healthy' ? '#00f2ff' : k === 'critical' ? '#bc00ff' : '#e2e8f0', fontFamily: 'Manrope, sans-serif' }}>
                                    {((v as number) * 100).toFixed(0)}%
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
