import React, { useState } from 'react';
import { WhyButton } from '@/modules/shared/explain/WhyButton';
import { buildHealthWhy } from '@/modules/shared/explain/producers/buildHealthWhy';
import { buildAnomalyWhy } from '@/modules/shared/explain/producers/buildAnomalyWhy';
import type { Machine, Intervention } from '@/lib/types';
import { MachineMini3D } from './3d/MachineMini3D';
import { ExplainabilityDrawer } from './ExplainabilityDrawer';
import { ReadinessScoreTile } from './ReadinessScoreTile';
import { MaintenanceTimeline } from './MaintenanceTimeline';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

interface MLPredictionFull {
    risk_level?: string;
    rul_days?: number | null;
    rul_confidence_interval?: { low: number; high: number; confidence: number } | null;
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
    // P6: maintenance schedule
    p6_schedule_days?: number | null;
    // Telemetry availability (injected by unified-health endpoint). When
    // telemetry_available is false the sensor fields below are null and the
    // ML models were not run — figures come from maintenance history only.
    telemetry_available?: boolean;
    telemetry_data_points?: number;
    // Latest telemetry readings (injected by unified-health endpoint)
    air_temperature?: number | null;
    process_temperature?: number | null;
    rotational_speed?: number | null;
    torque?: number | null;
    tool_wear?: number | null;
    // Inventory parts readiness (injected by unified-health endpoint)
    parts_readiness?: {
        status: 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN';
        parts_checked: number;
        critical_missing: { id: number; name: string; qty: number }[];
        low_stock: { id: number; name: string; qty: number; min_stock: number }[];
        all_available: boolean;
    };
    // P7: condition-aware parts demand forecast (injected by unified-health endpoint)
    parts_demand?: {
        horizon_days: number;
        source: string;
        items: {
            piece_id: number;
            reference: string;
            name: string;
            expected_qty: number;
            on_hand: number;
            min_stock: number;
            shortfall: number;
            urgency_score: number;
            recommended_order_qty: number;
            driver: 'condition' | 'consumption';
        }[];
    } | null;
    // Post-maintenance recovery (most recent completed WO within 7-day window)
    recovery?: RecoveryInfo | null;
}

export interface RecoveryInfo {
    work_order_id: number | null;
    delta: number | null;
    status: 'Recovered' | 'Recovering' | 'No improvement' | 'Monitoring' | 'No baseline';
    score_before: number | null;
    score_after_completion: number | null;
    current_score: number | null;
    days_since_completion: number | null;
    within_recovery_window: boolean;
    completion_date: string | null;
}

interface Props {
    machine: Machine;
    mlPrediction: MLPredictionFull | null;
    interventions: Intervention[];
    onProvisioned?: () => void;   // refetch unified-health after Quick Action
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

function DonutGauge({ score }: Readonly<{ score: number }>) {
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

function SensorCard({ label, value, unit, pct, accent }: Readonly<{
    label: string; value: string; unit: string; pct: number; accent: 'cyan' | 'purple';
}>) {
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

function AnomalyBar({ label, value, max, color }: Readonly<{ label: string; value: number; max: number; color: string }>) {
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

function PartsReadinessCard({ readiness }: Readonly<{ readiness: MLPredictionFull['parts_readiness'] }>) {
    if (!readiness || readiness.status === 'OK' || readiness.status === 'UNKNOWN') return null;

    const isCritical = readiness.status === 'CRITICAL';
    const cardStyle: React.CSSProperties = isCritical
        ? {
            background: 'rgba(255,255,255,0.03)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(239,68,68,0.35)',
            boxShadow: '0 0 20px rgba(239,68,68,0.08)',
            borderRadius: '1.5rem',
            position: 'relative',
            overflow: 'hidden',
            padding: '1.25rem',
        }
        : {
            background: 'rgba(255,255,255,0.03)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(245,158,11,0.35)',
            boxShadow: '0 0 20px rgba(245,158,11,0.08)',
            borderRadius: '1.5rem',
            position: 'relative',
            overflow: 'hidden',
            padding: '1.25rem',
        };

    const accentColor = isCritical ? '#ef4444' : '#f59e0b';
    const badgeLabel = isCritical ? 'Parts Missing' : 'Low Stock';
    const problemParts = isCritical
        ? readiness.critical_missing
        : readiness.low_stock.map(p => ({ ...p, display: `${p.qty} / ${p.min_stock} min` }));
    const displayParts = problemParts.slice(0, 5);

    return (
        <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>
                    Parts Readiness
                </h4>
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: accentColor, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'Space Grotesk, monospace', background: `${accentColor}18`, padding: '0.2rem 0.6rem', borderRadius: 999 }}>
                    {badgeLabel}
                </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {displayParts.map((part) => (
                    <div key={part.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontFamily: 'Space Grotesk, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '70%' }}>
                            {part.name}
                        </span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: accentColor, fontFamily: 'Manrope, sans-serif', flexShrink: 0 }}>
                            {isCritical ? 'Out of stock' : `Qty: ${part.qty}`}
                        </span>
                    </div>
                ))}
                {problemParts.length > 5 && (
                    <p style={{ fontSize: '0.6rem', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginTop: '0.25rem' }}>
                        +{problemParts.length - 5} more
                    </p>
                )}
            </div>
            <p style={{ fontSize: '0.55rem', color: '#475569', marginTop: '0.75rem', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6 }}>
                {readiness.parts_checked} part{readiness.parts_checked === 1 ? '' : 's'} checked for this machine.
            </p>
        </div>
    );
}

function PartsDemandCard({
    demand,
    machine,
    mlPrediction,
    onProvisioned,
}: Readonly<{
    demand: MLPredictionFull['parts_demand'];
    machine?: Machine;
    mlPrediction?: MLPredictionFull | null;
    onProvisioned?: () => void;
}>) {
    const [showAll, setShowAll] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [qaLoading, setQaLoading] = useState(false);
    const { isAdmin } = useAuth();
    const { toast } = useToast();
    const QA_API = import.meta.env.VITE_API_BASE_URL || '';

    async function handleQuickAction() {
        if (!machine) return;
        setQaLoading(true);
        try {
            const res = await fetch(`${QA_API}/api/v1/ml/procurement/quick-action/${machine.id}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
            });
            const json = await res.json();
            if (!res.ok || json.success === false) {
                toast({
                    title: 'Quick Action failed',
                    description: json.error ?? json.message ?? 'Unknown error',
                    variant: 'destructive',
                });
                return;
            }
            const s = json.summary ?? {};
            toast({
                title: json.idempotent ? 'Already up to date' : 'Quick Action complete',
                description: json.idempotent
                    ? 'No changes needed — parts already provisioned.'
                    : `${s.pieces_created ?? 0} created · ${s.stock_updated ?? 0} stock updated`,
            });
            onProvisioned?.();
        } catch (e: any) {
            toast({ title: 'Quick Action failed', description: e?.message ?? 'Network error', variant: 'destructive' });
        } finally {
            setQaLoading(false);
        }
    }

    if (!demand || demand.items.length === 0) {
        if (demand?.source === 'p7_model') {
            return (
                <div style={{ ...glass, padding: '1.25rem', marginTop: '0.75rem' }}>
                    <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.5rem' }}>
                        Parts Needed · Next {demand.horizon_days} Days
                    </h4>
                    <p style={{ fontSize: '0.7rem', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>
                        No parts needed in the next {demand.horizon_days} days.
                    </p>
                </div>
            );
        }
        return null;
    }

    const hasShortfall = demand.items.some(i => i.shortfall > 0);
    const accentColor  = hasShortfall ? '#f97316' : '#00f2ff';
    const cardBorder   = hasShortfall
        ? { border: '1px solid rgba(249,115,22,0.3)', boxShadow: '0 0 20px rgba(249,115,22,0.08)' }
        : { border: '1px solid rgba(0,242,255,0.3)',  boxShadow: '0 0 20px rgba(0,242,255,0.08)' };

    const PREVIEW = 5;
    const visibleItems = showAll ? demand.items : demand.items.slice(0, PREVIEW);
    const hiddenCount  = demand.items.length - PREVIEW;

    return (
        <div style={{ ...glass, ...cardBorder, padding: '1.25rem', marginTop: '0.75rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>
                    Parts Needed · Next {demand.horizon_days} Days
                    <span style={{ marginLeft: '0.5rem', color: '#475569', fontWeight: 400 }}>({demand.items.length})</span>
                </h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {isAdmin && (
                        <button
                            onClick={handleQuickAction}
                            disabled={qaLoading}
                            title="Create missing pieces and top up stock for all recommended parts"
                            style={{
                                display: 'flex', alignItems: 'center', gap: '0.3rem',
                                fontSize: '0.6rem', fontWeight: 700, color: accentColor,
                                background: `${accentColor}18`, border: `1px solid ${accentColor}55`,
                                borderRadius: 999, padding: '0.15rem 0.6rem',
                                cursor: qaLoading ? 'wait' : 'pointer', opacity: qaLoading ? 0.6 : 1,
                                fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase', letterSpacing: '0.08em',
                            }}
                        >
                            {qaLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                            Quick Action
                        </button>
                    )}
                    {/* Why? drawer trigger */}
                    {machine && (
                        <button
                            onClick={() => setDrawerOpen(true)}
                            style={{
                                fontSize: '0.6rem', fontWeight: 600, color: '#00f2ff',
                                background: 'rgba(0,242,255,0.08)', border: '1px solid rgba(0,242,255,0.2)',
                                borderRadius: 999, padding: '0.15rem 0.6rem', cursor: 'pointer',
                                fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase', letterSpacing: '0.08em',
                            }}
                        >
                            Why?
                        </button>
                    )}
                    {hasShortfall && (
                        <span style={{
                            fontSize: '0.6rem', fontWeight: 700, color: accentColor,
                            textTransform: 'uppercase', letterSpacing: '0.08em',
                            fontFamily: 'Space Grotesk, monospace',
                            background: `${accentColor}18`, padding: '0.2rem 0.6rem', borderRadius: 999,
                        }}>
                            Order Required
                        </span>
                    )}
                </div>
            </div>
            {/* Explainability Drawer */}
            {machine && (
                <ExplainabilityDrawer
                    open={drawerOpen}
                    onOpenChange={setDrawerOpen}
                    machine={machine}
                    parts_demand={demand}
                    mlPrediction={mlPrediction}
                />
            )}

            {/* Part rows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {visibleItems.map((item) => {
                    const needsOrder = item.shortfall > 0;
                    return (
                        <div key={item.piece_id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{
                                flexShrink: 0, width: 6, height: 6, borderRadius: '50%',
                                background: needsOrder ? '#f97316' : '#00f2ff',
                            }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <p style={{
                                    fontSize: '0.7rem', color: '#e2e8f0',
                                    fontFamily: 'Space Grotesk, monospace',
                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                    textTransform: 'capitalize',
                                }}>
                                    {item.name}
                                </p>
                                <p style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>
                                    In stock: {item.on_hand} &nbsp;·&nbsp; Need: {item.expected_qty.toFixed(1)} &nbsp;·&nbsp;
                                    {item.driver === 'condition' ? 'Condition-based' : 'Usage-based'}
                                </p>
                            </div>
                            {needsOrder ? (
                                <span style={{
                                    flexShrink: 0, fontSize: '0.6rem', fontWeight: 700,
                                    color: '#f97316', fontFamily: 'Space Grotesk, monospace',
                                    background: 'rgba(249,115,22,0.12)', padding: '0.15rem 0.5rem',
                                    borderRadius: 999, border: '1px solid rgba(249,115,22,0.25)',
                                }}>
                                    Order {Math.ceil(item.recommended_order_qty)}
                                </span>
                            ) : (
                                <span style={{
                                    flexShrink: 0, fontSize: '0.6rem', fontWeight: 700,
                                    color: '#00f2ff', fontFamily: 'Space Grotesk, monospace',
                                    background: 'rgba(0,242,255,0.08)', padding: '0.15rem 0.5rem',
                                    borderRadius: 999,
                                }}>
                                    In stock
                                </span>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Expand / collapse toggle */}
            {demand.items.length > PREVIEW && (
                <button
                    onClick={() => setShowAll(v => !v)}
                    style={{
                        marginTop: '0.75rem',
                        display: 'flex', alignItems: 'center', gap: '0.35rem',
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '0.5rem',
                        padding: '0.3rem 0.75rem',
                        cursor: 'pointer',
                        fontSize: '0.65rem', fontWeight: 600,
                        color: accentColor,
                        fontFamily: 'Space Grotesk, monospace',
                        textTransform: 'uppercase', letterSpacing: '0.08em',
                        width: '100%', justifyContent: 'center',
                        transition: 'background 0.2s',
                    }}
                >
                    {showAll
                        ? '▲ Show less'
                        : `▼ Show all ${demand.items.length} parts (+${hiddenCount} more)`}
                </button>
            )}

            {/* Footer */}
            <p style={{ fontSize: '0.55rem', color: '#475569', marginTop: '0.75rem', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6 }}>
                {demand.source === 'p7_model'
                    ? 'Forecast based on machine condition and failure pattern history.'
                    : 'Standard maintenance estimate — condition data improves accuracy.'}
            </p>
        </div>
    );
}

export function formatDeltaLabel(delta: number | null | undefined): string {
    if (delta == null) return '—';
    const sign = delta > 0 ? '+' : '';
    return `${sign}${delta.toFixed(1)} pts`;
}

export function formatDaysLabel(days: number | null | undefined): string | null {
    if (days == null) return null;
    return `${days} day${days === 1 ? '' : 's'} ago`;
}

export function formatWindowLabel(withinWindow: boolean, days: number | null | undefined): string {
    if (withinWindow && days != null) {
        const remaining = Math.max(0, 7 - days);
        return `${remaining} day${remaining === 1 ? '' : 's'} remaining`;
    }
    return 'Window closed';
}

function PostMaintenanceRecoveryCard({ recovery }: Readonly<{ recovery: RecoveryInfo }>) {
    const { status, delta, score_before, current_score, days_since_completion, within_recovery_window, work_order_id } = recovery;

    // Color tokens per status
    const palette: Record<RecoveryInfo['status'], { accent: string; bg: string; badgeBg: string; }> = {
        'Recovered':       { accent: '#10b981', bg: 'rgba(16,185,129,0.35)',  badgeBg: 'rgba(16,185,129,0.15)' },
        'Recovering':      { accent: '#f59e0b', bg: 'rgba(245,158,11,0.35)',  badgeBg: 'rgba(245,158,11,0.15)' },
        'No improvement':  { accent: '#ef4444', bg: 'rgba(239,68,68,0.35)',   badgeBg: 'rgba(239,68,68,0.15)' },
        'Monitoring':      { accent: '#00f2ff', bg: 'rgba(0,242,255,0.30)',   badgeBg: 'rgba(0,242,255,0.10)' },
        'No baseline':     { accent: '#64748b', bg: 'rgba(100,116,139,0.30)', badgeBg: 'rgba(100,116,139,0.10)' },
    };
    const tone = palette[status];

    const cardStyle: React.CSSProperties = {
        background: 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: `1px solid ${tone.bg}`,
        boxShadow: `0 0 20px ${tone.bg.replace('0.35', '0.10').replace('0.30', '0.08')}`,
        borderRadius: '1.5rem',
        position: 'relative',
        overflow: 'hidden',
        padding: '1.25rem',
        marginTop: '0.75rem',
    };

    const deltaLabel = formatDeltaLabel(delta);
    const daysLabel = formatDaysLabel(days_since_completion);
    const windowLabel = formatWindowLabel(within_recovery_window, days_since_completion);

    return (
        <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
                <div>
                    <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>
                        Post-Maintenance Recovery
                    </h4>
                    {work_order_id != null && (
                        <p style={{ fontSize: '0.55rem', color: '#64748b', marginTop: '0.2rem', fontFamily: 'Space Grotesk, monospace' }}>
                            WO #{work_order_id}{daysLabel ? ` · ${daysLabel}` : ''}
                        </p>
                    )}
                </div>
                <span style={{
                    fontSize: '0.6rem', fontWeight: 700, color: tone.accent,
                    textTransform: 'uppercase', letterSpacing: '0.08em',
                    fontFamily: 'Space Grotesk, monospace',
                    background: tone.badgeBg, padding: '0.2rem 0.6rem', borderRadius: 999,
                    border: `1px solid ${tone.bg}`,
                }}>
                    {status}
                </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ textAlign: 'left' }}>
                    <p style={{ fontSize: '0.55rem', color: '#64748b', fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Before</p>
                    <p style={{ fontSize: '1.6rem', fontWeight: 800, color: '#94a3b8', fontFamily: 'Manrope, sans-serif' }}>
                        {score_before == null ? '—' : score_before.toFixed(0)}
                    </p>
                </div>
                <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, transparent, ${tone.accent}, transparent)`, position: 'relative' }}>
                    <span style={{
                        position: 'absolute', top: '-0.6rem', left: '50%', transform: 'translateX(-50%)',
                        fontSize: '0.75rem', fontWeight: 800, color: tone.accent, fontFamily: 'Manrope, sans-serif',
                        background: 'rgba(15,23,42,0.85)', padding: '0.05rem 0.5rem', borderRadius: 999,
                    }}>
                        {deltaLabel}
                    </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.55rem', color: '#64748b', fontFamily: 'Space Grotesk, monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Now</p>
                    <p style={{ fontSize: '1.6rem', fontWeight: 800, color: tone.accent, fontFamily: 'Manrope, sans-serif' }}>
                        {current_score == null ? '—' : current_score.toFixed(0)}
                    </p>
                </div>
            </div>

            <p style={{ fontSize: '0.55rem', color: '#475569', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6 }}>
                {status === 'Recovered' && 'Machine returned to healthy range. Maintenance effective.'}
                {status === 'Recovering' && 'Health trending up, not yet in healthy range.'}
                {status === 'No improvement' && 'Telemetry has not improved after this work order. Investigate.'}
                {status === 'Monitoring' && 'Work order still in progress — baseline captured at creation.'}
                {status === 'No baseline' && 'Baseline missing (ML service was offline at WO creation).'}
                {` · ${windowLabel}`}
            </p>
        </div>
    );
}

export function MLIntelligenceTab({ machine, mlPrediction, onProvisioned }: Readonly<Props>) {
    const p = mlPrediction;
    const healthScore = p?.unified_health_score ?? p?.health_score ?? 0;
    const failureProb = p?.failure_probability ?? 0;
    const rulDays = p?.rul_days ?? p?.kalman_rul ?? null;
    const rulInterval = p?.rul_confidence_interval ?? null;
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

    const scheduleDays = p?.p6_schedule_days ?? null;
    const nextMaintDate = machine.date_prochaine_maintenance
        ? new Date(machine.date_prochaine_maintenance)
        : null;
    const scheduleOverdue = nextMaintDate != null && nextMaintDate < new Date();

    let scheduleDateLabel: string;
    if (!nextMaintDate) {
        scheduleDateLabel = 'Next recommended interval';
    } else if (scheduleOverdue) {
        scheduleDateLabel = `Overdue · ${nextMaintDate.toLocaleDateString('fr-FR')}`;
    } else {
        scheduleDateLabel = nextMaintDate.toLocaleDateString('fr-FR');
    }

    // Survival probability for chart
    const survivalPct = mo?.survival?.survival_probability == null
        ? Math.max(0, Math.round(healthScore))
        : Math.round(mo.survival.survival_probability * 100);

    // Behavioral Anomaly (ensemble detector — 4 methods combined)
    const behaviorScore = p?.p4_anomaly_score ?? 0;
    const behaviorFlagged = isAnomaly || behaviorScore > 0.5;
    const mahalScore = mo?.mahal_hi?.dm2 ?? 0;

    // The backend reports telemetry_available: false when the machine has no
    // usable sensor history. In that case every sensor field is null and the
    // ML models were never called — say so instead of rendering a full board
    // of numbers that are really maintenance-history fallbacks.
    const telemetryAvailable = p?.telemetry_available !== false;

    // Sensor values — prefer machine fields, fall back to values in mlPrediction
    const airTemp = machine.air_temperature ?? p?.air_temperature ?? null;
    const procTemp = machine.process_temperature ?? p?.process_temperature ?? null;
    const rpm = machine.rotational_speed ?? p?.rotational_speed ?? null;
    const torque = machine.torque ?? p?.torque ?? null;
    const toolWear = machine.tool_wear ?? p?.tool_wear ?? null;

    const sensors = [
        { label: 'Air Temp',     value: airTemp  == null ? '—' : airTemp.toFixed(1),        unit: 'K',   pct: airTemp  == null ? 0 : ((airTemp  - 250) / 100)  * 100, accent: 'cyan'   as const },
        { label: 'Process Temp', value: procTemp == null ? '—' : procTemp.toFixed(1),       unit: 'K',   pct: procTemp == null ? 0 : ((procTemp - 250) / 150)  * 100, accent: 'cyan'   as const },
        { label: 'Rotation',     value: rpm      == null ? '—' : rpm.toLocaleString(),      unit: 'RPM', pct: rpm      == null ? 0 : (rpm / 10000) * 100,               accent: 'purple' as const },
        { label: 'Torque',       value: torque   == null ? '—' : torque.toFixed(1),         unit: 'Nm',  pct: torque   == null ? 0 : (torque / 1000) * 100,             accent: 'cyan'   as const },
        { label: 'Tool Wear',    value: toolWear == null ? '—' : toolWear.toString(),       unit: 'min', pct: toolWear == null ? 0 : (toolWear / 300) * 100,            accent: 'purple' as const },
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
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: telemetryAvailable ? '#00f2ff' : '#64748b', display: 'inline-block', animation: telemetryAvailable ? 'pulse 2s infinite' : 'none' }} />
                <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.18em', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>
                    {telemetryAvailable ? 'Neural Engine Operational' : 'Neural Engine Idle — No Sensor Data'}
                </span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '1rem', ...glass, padding: '0.5rem 1.25rem', borderRadius: '0.75rem' }}>
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 2 }}>Live Engines</p>
                        <p style={{ fontWeight: 700, color: '#fff', fontSize: '0.8rem' }}>{telemetryAvailable ? '8 Models Active' : 'Models Idle'}</p>
                    </div>
                    <div style={{ width: 1, background: 'rgba(255,255,255,0.1)', alignSelf: 'stretch' }} />
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 2 }}>Verdict</p>
                        <p style={{ fontWeight: 700, color: '#00f2ff', fontSize: '0.8rem' }}>{dstVerdict}</p>
                    </div>
                </div>
            </div>

            {/* ── No-telemetry banner ── */}
            {!telemetryAvailable && (
                <div style={{
                    ...glassAlt,
                    padding: '0.85rem 1.1rem',
                    marginBottom: '1rem',
                    borderLeft: '3px solid #f59e0b',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                }}>
                    <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fbbf24' }}>
                        No sensor data for this machine
                    </p>
                    <p style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.5 }}>
                        Sensor readings are unavailable, so the predictive models were not run.
                        The figures below are estimated from maintenance history alone and are not
                        condition-based. Record telemetry to enable full predictions.
                    </p>
                </div>
            )}

            {/* ── 5 Sensor Cards ── */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
                {sensors.map((s) => (
                    <SensorCard key={s.label} {...s} />
                ))}
            </div>

            {/* ── Main Grid ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>

                {/* Health Donut */}
                <div style={{ ...glassAlt, padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', gridRow: 'span 1' }}>
                    <MachineMini3D
                        riskLevel={
                            (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(riskLevel)
                                ? riskLevel
                                : 'LOW') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
                        }
                    />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        {p ? (
                            <>
                                <DonutGauge score={healthScore} />
                                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '1.25rem', marginBottom: '0.35rem' }}>
                                    Unified Health
                                </h4>
                                <p style={{ fontSize: '0.75rem', color: '#94a3b8', maxWidth: 220 }}>
                                    {isAnomaly ? 'Anomalous behaviour detected. Immediate attention recommended.' : 'DST-fused score across 8 active models.'}
                                </p>
                                <div style={{ marginTop: '0.6rem' }}>
                                    <WhyButton payload={buildHealthWhy(p as any)} />
                                </div>
                            </>
                        ) : (
                            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No ML data yet</p>
                        )}
                    </div>
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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem' }}>

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
                        {rulDays == null ? '—' : `${Math.round(rulDays)}`}
                        {rulDays != null && <span style={{ fontSize: '0.9rem', fontWeight: 400, color: '#64748b' }}> Days</span>}
                    </p>
                    <p style={{ fontSize: '0.6rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'Space Grotesk, monospace' }}>
                        {rulInterval
                            ? `Likely range: ${Math.round(rulInterval.low)}–${Math.round(rulInterval.high)}d`
                            : 'Range: not yet available'}
                    </p>
                </div>

                {/* P6 Schedule */}
                <div style={{ ...glass, padding: '1.25rem', borderColor: scheduleOverdue ? 'rgba(249,115,22,0.4)' : 'rgba(34,197,94,0.25)' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.4rem' }}>Schedule</p>
                    <p style={{ fontSize: '1.8rem', fontWeight: 900, color: scheduleOverdue ? '#f97316' : '#22c55e', fontFamily: 'Manrope, sans-serif' }}>
                        {scheduleDays == null ? '—' : `${Math.round(scheduleDays)}`}
                        {scheduleDays != null && <span style={{ fontSize: '0.9rem', fontWeight: 400, color: '#64748b' }}> Days</span>}
                    </p>
                    <p style={{ fontSize: '0.6rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'Space Grotesk, monospace' }}>
                        {scheduleDateLabel}
                    </p>
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
                    <div style={{ marginTop: '0.6rem' }}>
                        <WhyButton payload={buildAnomalyWhy((p ?? {}) as any)} />
                    </div>
                    <p style={{ fontSize: '0.55rem', color: '#475569', marginTop: '0.75rem', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6 }}>
                        {behaviorFlagged
                            ? 'Machine behaviour deviates from normal operating pattern.'
                            : '4 detectors agree: machine within normal operating range.'}
                    </p>
                </div>
            </div>

            {/* Post-Maintenance Recovery — pre vs post unified_health_score delta */}
            {p?.recovery && (
                <PostMaintenanceRecoveryCard recovery={p.recovery} />
            )}

            {/* Parts Readiness */}
            <PartsReadinessCard readiness={p?.parts_readiness} />

            {/* Parts Demand — condition-aware forecast for next 30 days */}
            <PartsDemandCard demand={p?.parts_demand} machine={machine} mlPrediction={p} onProvisioned={onProvisioned} />

            {/* Maintenance Readiness Score — P7.5 */}
            <ReadinessScoreTile machineId={machine.id} />

            {/* Maintenance Timeline — P7.5 */}
            <MaintenanceTimeline machineId={machine.id} />

            {/* BPA Beliefs (if available) */}
            {p?.bpa && (
                <div style={{ marginTop: '0.75rem', ...glass, padding: '1.25rem' }}>
                    <p style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#64748b', fontFamily: 'Space Grotesk, monospace', marginBottom: '0.75rem' }}>DST Belief Function</p>
                    <div style={{ display: 'flex', gap: '1.5rem' }}>
                        {Object.entries(p.bpa).map(([k, v]) => {
                            let bpaColor = '#e2e8f0';
                            if (k === 'healthy') {
                                bpaColor = '#00f2ff';
                            } else if (k === 'critical') {
                                bpaColor = '#bc00ff';
                            }
                            return (
                            <div key={k} style={{ flex: 1 }}>
                                <p style={{ fontSize: '0.6rem', textTransform: 'capitalize', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginBottom: 4 }}>{k}</p>
                                <p style={{ fontSize: '1rem', fontWeight: 700, color: bpaColor, fontFamily: 'Manrope, sans-serif' }}>
                                    {(v * 100).toFixed(0)}%
                                </p>
                            </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
