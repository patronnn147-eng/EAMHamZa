/**
 * ExplainabilityDrawer — P7 plain-language breakdown of parts demand.
 * Opens from PartsDemandCard. No ML jargon in user-facing text.
 *
 * 4 sections: Why · What if ignored · What to prepare · Who acts (role-aware)
 */
import React, { useState } from 'react';
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
} from '@/components/ui/sheet';
import { useUserRole, type UserRole } from '@/hooks/usePermission';
import { useNavigate } from 'react-router-dom';
import type { Machine } from '@/lib/types';
import { ProcurementRecommendationModal } from './ProcurementRecommendationModal';

// ── Local type mirrors for parts_demand contract ──────────────────────────
interface DemandItem {
    piece_id: number;
    name: string;
    reference: string;
    expected_qty: number;
    on_hand: number;
    shortfall: number;
    urgency_score: number;
    recommended_order_qty: number;
    driver: 'condition' | 'consumption';
}

interface PartsDemand {
    horizon_days: number;
    source: string;
    items: DemandItem[];
}

interface MLPredictionSnippet {
    rul_days?: number | null;
    kalman_rul?: number | null;
    p2_failure_types?: Record<string, { detected: boolean; probability: number }>;
    failure_probability?: number;
    risk_level?: string;
}

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    machine: Machine;
    parts_demand: PartsDemand | null | undefined;
    mlPrediction: MLPredictionSnippet | null | undefined;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function topFailureType(
    ft?: Record<string, { detected: boolean; probability: number }>
): string | null {
    if (!ft) return null;
    const entries = Object.entries(ft).filter(([, v]) => v.detected || v.probability > 20);
    if (!entries.length) return null;
    entries.sort((a, b) => b[1].probability - a[1].probability);
    const map: Record<string, string> = {
        TWF: 'tool wear',
        HDF: 'overheating',
        PWF: 'power fluctuation',
        OSF: 'overload stress',
        RNF: 'random failure',
    };
    return map[entries[0][0]] ?? entries[0][0];
}

function rulLabel(rul: number | null | undefined): string {
    if (rul == null) return 'an unknown timeframe';
    if (rul <= 0) return 'immediately — failure is overdue';
    if (rul < 7) return `${Math.round(rul)} day${rul === 1 ? '' : 's'} — urgent`;
    if (rul < 30) return `${Math.round(rul)} days`;
    return `${Math.round(rul)} days — within the planning horizon`;
}

function whoActsContent(role: UserRole | null, machine: Machine, shortfallCount: number) {
    switch (role) {
        case 'ADMIN':
            return {
                title: 'Your action — Procurement approval',
                body: `${shortfallCount} part${shortfallCount !== 1 ? 's are' : ' is'} below required stock. Create a draft work order for procurement review — you can approve or reject it before anything is ordered.`,
                actionLabel: 'Create Procurement Draft',
                actionPath: null,  // handled by modal below
            };
        case 'CHEFTECH':
            return {
                title: 'Your action — Schedule maintenance',
                body: `Create a work order for this machine and reserve the listed parts. Early scheduling prevents unplanned downtime and ensures technicians have what they need on the day.`,
                actionLabel: `Open Machine #${machine.id}`,
                actionPath: `/machines/${machine.id}`,
            };
        case 'CHETOP': {
            let shortfallSummary = 'Stock levels are adequate.';
            if (shortfallCount > 0) {
                const partSuffix = shortfallCount !== 1 ? 's are' : ' is';
                shortfallSummary = `${shortfallCount} part${partSuffix} missing.`;
            }
            return {
                title: 'Business risk overview',
                body: `${shortfallSummary} An unplanned breakdown on this machine risks production downtime, emergency procurement costs, and SLA delays. Proactive maintenance this cycle avoids those costs.`,
                actionLabel: null,
                actionPath: null,
            };
        }
        case 'TECHNICIEN':
            return {
                title: 'Before you start — Prepare these parts',
                body: 'Gather the parts listed below before beginning this intervention. Having everything ready reduces machine downtime and avoids mid-repair delays.',
                actionLabel: null,
                actionPath: null,
            };
        default:
            return {
                title: 'Recommended action',
                body: 'Review the parts list and coordinate with your team to ensure availability before the maintenance window.',
                actionLabel: null,
                actionPath: null,
            };
    }
}

// ── Sub-components ────────────────────────────────────────────────────────

function Section({ icon, title, children }: Readonly<{ icon: string; title: string; children: React.ReactNode }>) {
    return (
        <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '1rem' }}>{icon}</span>
                <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace' }}>
                    {title}
                </h4>
            </div>
            <div style={{ paddingLeft: '1.5rem' }}>{children}</div>
        </div>
    );
}

function BodyText({ children }: Readonly<{ children: React.ReactNode }>) {
    return (
        <p style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.75, fontFamily: 'Manrope, sans-serif' }}>
            {children}
        </p>
    );
}

// ── Main component ────────────────────────────────────────────────────────

export function ExplainabilityDrawer({ open, onOpenChange, machine, parts_demand, mlPrediction }: Readonly<Props>) {
    const role = useUserRole();
    const navigate = useNavigate();
    const [procModalOpen, setProcModalOpen] = useState(false);

    const items      = parts_demand?.items ?? [];
    const shortage   = items.filter(i => i.shortfall > 0);
    const rul        = mlPrediction?.rul_days ?? mlPrediction?.kalman_rul ?? null;
    const failType   = topFailureType(mlPrediction?.p2_failure_types);
    const failureProb = mlPrediction?.failure_probability ?? 0;
    const whoActs    = whoActsContent(role, machine, shortage.length);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent
                side="right"
                style={{ width: '420px', maxWidth: '95vw', background: '#080f1e', borderLeft: '1px solid rgba(255,255,255,0.08)', overflowY: 'auto' }}
            >
                <SheetHeader style={{ marginBottom: '1.5rem' }}>
                    <SheetTitle style={{ color: '#fff', fontFamily: 'Manrope, sans-serif', fontSize: '1rem' }}>
                        Parts Forecast — Machine #{machine.id}
                    </SheetTitle>
                    <SheetDescription style={{ color: '#64748b', fontSize: '0.72rem', fontFamily: 'Space Grotesk, monospace' }}>
                        Plain-language breakdown of what is needed and why.
                    </SheetDescription>
                </SheetHeader>

                {/* ── WHY ── */}
                <Section icon="🔍" title="Why is this showing?">
                    <BodyText>
                        {failureProb > 0
                            ? <>This machine has a <strong style={{ color: '#f97316' }}>{failureProb.toFixed(0)}% failure probability</strong> and is estimated to require attention in <strong style={{ color: '#00f2ff' }}>{rulLabel(rul)}</strong>{failType ? `, most likely due to ${failType}` : ''}. Based on past repairs for this failure pattern, the parts below are typically needed.</>
                            : <>Based on machine condition and maintenance history, the listed parts are expected to be needed in the next {parts_demand?.horizon_days ?? 30} days.</>
                        }
                    </BodyText>
                </Section>

                {/* ── WHAT IF IGNORED ── */}
                <Section icon="⚠️" title="What if nothing is ordered?">
                    <BodyText>
                        {shortage.length > 0
                            ? <>{shortage.length} part{shortage.length !== 1 ? 's are' : ' is'} below the required stock level. Without ordering, a breakdown could cause <strong style={{ color: '#f97316' }}>unplanned production downtime</strong>, emergency procurement at higher cost, and longer machine-off time while parts are sourced.</>
                            : <>Current stock levels are sufficient. No immediate action is required, but monitoring is advised as the machine approaches its maintenance window.</>
                        }
                    </BodyText>
                </Section>

                {/* ── WHAT TO PREPARE ── */}
                <Section icon="📦" title="What to prepare">
                    {items.length === 0 ? (
                        <BodyText>No parts identified for the next {parts_demand?.horizon_days ?? 30} days.</BodyText>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {items.slice(0, 10).map(item => (
                                <div key={item.piece_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.06)' }}>
                                    <div>
                                        <p style={{ fontSize: '0.72rem', color: '#e2e8f0', fontFamily: 'Space Grotesk, monospace', textTransform: 'capitalize' }}>{item.name}</p>
                                        <p style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>
                                            In stock: {item.on_hand} · Need: {item.expected_qty.toFixed(1)}
                                        </p>
                                    </div>
                                    {item.shortfall > 0 && (
                                        <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#f97316', background: 'rgba(249,115,22,0.12)', padding: '0.15rem 0.5rem', borderRadius: 999, border: '1px solid rgba(249,115,22,0.25)', whiteSpace: 'nowrap' }}>
                                            Order {Math.ceil(item.recommended_order_qty)}
                                        </span>
                                    )}
                                </div>
                            ))}
                            {items.length > 10 && (
                                <p style={{ fontSize: '0.6rem', color: '#64748b', fontFamily: 'Space Grotesk, monospace' }}>
                                    +{items.length - 10} more parts — view full list in the Parts card above.
                                </p>
                            )}
                        </div>
                    )}
                </Section>

                {/* ── WHO ACTS ── */}
                <Section icon="👤" title={whoActs.title}>
                    <BodyText>{whoActs.body}</BodyText>
                    {whoActs.actionLabel && (
                        <button
                            onClick={() => {
                                if (whoActs.actionPath) {
                                    onOpenChange(false);
                                    navigate(whoActs.actionPath);
                                } else {
                                    // ADMIN → open procurement modal
                                    setProcModalOpen(true);
                                }
                            }}
                            style={{
                                marginTop: '0.75rem',
                                display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                                background: 'rgba(0,242,255,0.08)',
                                border: '1px solid rgba(0,242,255,0.25)',
                                borderRadius: '0.5rem',
                                padding: '0.4rem 1rem',
                                cursor: 'pointer',
                                fontSize: '0.7rem', fontWeight: 600, color: '#00f2ff',
                                fontFamily: 'Space Grotesk, monospace',
                                textTransform: 'uppercase', letterSpacing: '0.08em',
                            }}
                        >
                            {whoActs.actionLabel} →
                        </button>
                    )}
                    {/* Procurement draft modal (ADMIN only) */}
                    <ProcurementRecommendationModal
                        open={procModalOpen}
                        onOpenChange={setProcModalOpen}
                        machineId={machine.id}
                        machineName={machine.nom}
                        partsDemand={parts_demand as any}
                    />
                </Section>

                {/* Source note */}
                <p style={{ fontSize: '0.55rem', color: '#334155', fontFamily: 'Space Grotesk, monospace', lineHeight: 1.6, marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.75rem' }}>
                    {parts_demand?.source === 'p7_model'
                        ? 'Forecast built from failure pattern history across all machines of this type.'
                        : 'Standard maintenance schedule — connect condition sensors for smarter forecasting.'}
                </p>
            </SheetContent>
        </Sheet>
    );
}
