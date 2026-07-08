/**
 * ProcurementRecommendationModal — P7.4 guarded draft approval.
 * Shows the auto-generated draft work order and requires explicit
 * human approve / reject before anything commits.
 * Never auto-commits — all actions require a button click.
 */
import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Package, CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';

const API       = import.meta.env.VITE_API_BASE_URL || '';
const getToken  = () => localStorage.getItem('access_token');

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    machineId: number;
    machineName?: string;
    /** Pass the parts_demand from unified-health if available */
    partsDemand?: {
        horizon_days: number;
        source: string;
        items: {
            piece_id: number;
            name: string;
            expected_qty: number;
            on_hand: number;
            shortfall: number;
            recommended_order_qty: number;
            driver: 'condition' | 'consumption';
        }[];
    } | null;
    onDraftCreated?: (woId: number) => void;
}

type Step = 'review' | 'creating' | 'created' | 'approving' | 'approved' | 'rejected' | 'error';

export function ProcurementRecommendationModal({
    open, onOpenChange, machineId, machineName, partsDemand, onDraftCreated,
}: Readonly<Props>) {
    const [step, setStep]         = useState<Step>('review');
    const [woId, setWoId]         = useState<number | null>(null);
    const [errorMsg, setErrorMsg] = useState('');

    const shortfallItems = partsDemand?.items.filter(i => i.shortfall > 0) ?? [];

    async function handleCreateDraft() {
        setStep('creating');
        try {
            const res = await fetch(`${API}/api/v1/ml/procurement/draft/${machineId}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${getToken()}` },
            });
            const json = await res.json();
            if (!res.ok || !json.success) {
                setErrorMsg(json.message ?? json.detail ?? 'Failed to create draft');
                setStep('error');
                return;
            }
            setWoId(json.wo_id);
            setStep('created');
            onDraftCreated?.(json.wo_id);
        } catch (e: any) {
            setErrorMsg(e.message ?? 'Network error');
            setStep('error');
        }
    }

    async function handleApprove() {
        if (!woId) return;
        setStep('approving');
        try {
            const res = await fetch(`${API}/api/v1/ml/procurement/draft/${woId}/approve`, {
                method: 'PATCH',
                headers: { Authorization: `Bearer ${getToken()}` },
            });
            const json = await res.json();
            if (!res.ok || !json.success) {
                setErrorMsg(json.message ?? json.detail ?? 'Approval failed');
                setStep('error');
                return;
            }
            setStep('approved');
        } catch (e: any) {
            setErrorMsg(e.message ?? 'Network error');
            setStep('error');
        }
    }

    async function handleReject() {
        if (!woId) return;
        try {
            await fetch(`${API}/api/v1/ml/procurement/draft/${woId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${getToken()}` },
            });
        } catch { /* best-effort */ }
        setStep('rejected');
    }

    function handleClose() {
        setStep('review');
        setWoId(null);
        setErrorMsg('');
        onOpenChange(false);
    }

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent style={{ maxWidth: 520, background: '#0f1623', border: '1px solid rgba(255,255,255,0.08)', color: '#fff' }}>
                <DialogHeader>
                    <DialogTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fff' }}>
                        <Package className="h-5 w-5 text-orange-400" />
                        Parts Procurement Draft
                    </DialogTitle>
                    <DialogDescription style={{ color: '#64748b' }}>
                        {machineName ? `Machine: ${machineName} (#${machineId})` : `Machine #${machineId}`}
                        {' · '}Next {partsDemand?.horizon_days ?? 30} days
                    </DialogDescription>
                </DialogHeader>

                {/* ── REVIEW / CREATE step ── */}
                {(step === 'review' || step === 'creating') && (
                    <>
                        <div style={{ padding: '0.5rem 0' }}>
                            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.75rem', lineHeight: 1.6 }}>
                                A draft work order will be created from the parts forecast below.{' '}
                                <strong style={{ color: '#f97316' }}> No reservation is made until you approve.</strong>
                            </p>

                            {shortfallItems.length === 0 ? (
                                <p style={{ fontSize: '0.75rem', color: '#64748b' }}>No shortage detected — draft is precautionary.</p>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 200, overflowY: 'auto' }}>
                                    {shortfallItems.map(item => (
                                        <div key={item.piece_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0.6rem', background: 'rgba(249,115,22,0.06)', borderRadius: '0.4rem', border: '1px solid rgba(249,115,22,0.15)' }}>
                                            <span style={{ fontSize: '0.72rem', color: '#e2e8f0', textTransform: 'capitalize' }}>{item.name}</span>
                                            <span style={{ fontSize: '0.7rem', color: '#f97316', fontWeight: 700 }}>
                                                Order {Math.ceil(item.recommended_order_qty)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <DialogFooter style={{ gap: '0.5rem' }}>
                            <Button variant="ghost" onClick={handleClose} style={{ color: '#64748b' }}>Cancel</Button>
                            <Button onClick={handleCreateDraft} disabled={step === 'creating'} style={{ background: '#f97316', color: '#fff' }}>
                                {step === 'creating' ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Creating…</> : 'Create Draft Work Order'}
                            </Button>
                        </DialogFooter>
                    </>
                )}

                {/* ── CREATED — approve / reject ── */}
                {(step === 'created' || step === 'approving') && (
                    <>
                        <div style={{ padding: '0.75rem', background: 'rgba(0,242,255,0.06)', borderRadius: '0.75rem', border: '1px solid rgba(0,242,255,0.15)', marginBottom: '0.75rem' }}>
                            <p style={{ fontSize: '0.8rem', color: '#00f2ff', fontWeight: 700, marginBottom: '0.25rem' }}>
                                Draft WO #{woId} created
                            </p>
                            <p style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.6 }}>
                                Approve to submit this work order into the maintenance workflow.
                                Reject to discard it — nothing will be reserved or ordered.
                            </p>
                        </div>
                        <DialogFooter style={{ gap: '0.5rem' }}>
                            <Button variant="ghost" onClick={handleReject} disabled={step === 'approving'} style={{ color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)' }}>
                                <XCircle className="h-4 w-4 mr-1" /> Reject
                            </Button>
                            <Button onClick={handleApprove} disabled={step === 'approving'} style={{ background: '#10b981', color: '#fff' }}>
                                {step === 'approving' ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Approving…</> : <><CheckCircle className="h-4 w-4 mr-1" />Approve</>}
                            </Button>
                        </DialogFooter>
                    </>
                )}

                {/* ── APPROVED ── */}
                {step === 'approved' && (
                    <>
                        <div style={{ textAlign: 'center', padding: '1rem 0' }}>
                            <CheckCircle className="h-10 w-10 text-green-400 mx-auto mb-3" />
                            <p style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 700 }}>Work order submitted</p>
                            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.4rem' }}>
                                WO #{woId} is now in the maintenance workflow. CHEFTECH will assign a technician.
                            </p>
                        </div>
                        <DialogFooter><Button onClick={handleClose}>Done</Button></DialogFooter>
                    </>
                )}

                {/* ── REJECTED ── */}
                {step === 'rejected' && (
                    <>
                        <div style={{ textAlign: 'center', padding: '1rem 0' }}>
                            <XCircle className="h-10 w-10 text-slate-400 mx-auto mb-3" />
                            <p style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 700 }}>Draft discarded</p>
                            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.4rem' }}>
                                No work order was created. The parts forecast remains visible.
                            </p>
                        </div>
                        <DialogFooter><Button variant="ghost" onClick={handleClose}>Close</Button></DialogFooter>
                    </>
                )}

                {/* ── ERROR ── */}
                {step === 'error' && (
                    <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: '0.5rem', border: '1px solid rgba(239,68,68,0.2)' }}>
                            <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0" />
                            <p style={{ fontSize: '0.75rem', color: '#f87171' }}>{errorMsg}</p>
                        </div>
                        <DialogFooter>
                            <Button variant="ghost" onClick={() => setStep('review')}>Try again</Button>
                            <Button variant="ghost" onClick={handleClose}>Close</Button>
                        </DialogFooter>
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}
