/**
 * MaintenanceTimeline — P7.5 — chronological event timeline for a machine.
 * Fetches from /api/v1/ml/machines/:id/timeline.
 * Plain language, no ML jargon.
 */
import React, { useEffect, useState } from 'react';

const API      = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface TimelineEvent {
    date: string;
    type: string;
    label: string;
    detail?: string | null;
}

interface Props { machineId: number; limit?: number }

const glass: React.CSSProperties = {
    background: 'rgba(255,255,255,0.03)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '1.5rem',
};

const TYPE_CONFIG: Record<string, { color: string; dot: string }> = {
    forecast:       { color: '#00f2ff', dot: '🔍' },
    alert:          { color: '#f97316', dot: '⚠️' },
    wo_created:     { color: '#94a3b8', dot: '📋' },
    wo_approved:    { color: '#10b981', dot: '✅' },
    wo_started:     { color: '#00f2ff', dot: '▶' },
    wo_completed:   { color: '#10b981', dot: '✔' },
    itv_approved:   { color: '#10b981', dot: '✅' },
    itv_completed:  { color: '#10b981', dot: '🔧' },
};

function formatDate(iso: string): string {
    try {
        return new Date(iso).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return iso.slice(0, 10); }
}

export function MaintenanceTimeline({ machineId, limit = 12 }: Readonly<Props>) {
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API}/api/v1/ml/machines/${machineId}/timeline?limit=${limit}`, {
                    headers: { Authorization: `Bearer ${getToken()}` },
                });
                if (res.ok) {
                    const json = await res.json();
                    setEvents((json.events ?? []).reverse()); // newest first in UI
                }
            } catch { /* silent */ }
            finally { setLoading(false); }
        })();
    }, [machineId, limit]);

    if (loading) return (
        <div style={{ ...glass, padding: '1.25rem', marginTop: '0.75rem' }}>
            <p style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace' }}>Loading timeline…</p>
        </div>
    );
    if (events.length === 0) return null;

    return (
        <div style={{ ...glass, padding: '1.25rem', marginTop: '0.75rem' }}>
            <h4 style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Space Grotesk, monospace', marginBottom: '1rem' }}>
                Maintenance Timeline
            </h4>

            <div style={{ position: 'relative', paddingLeft: '1.25rem' }}>
                {/* Vertical line */}
                <div style={{ position: 'absolute', left: '0.4rem', top: 0, bottom: 0, width: '1px', background: 'rgba(255,255,255,0.06)' }} />

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {events.map((e, i) => {
                        const cfg = TYPE_CONFIG[e.type] ?? { color: '#64748b', dot: '·' };
                        return (
                            <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                                {/* Dot */}
                                <div style={{
                                    position: 'absolute', left: 0,
                                    width: '0.85rem', height: '0.85rem', borderRadius: '50%',
                                    background: cfg.color + '22', border: `1px solid ${cfg.color}55`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.45rem',
                                    marginTop: '0.1rem',
                                }}>
                                    {cfg.dot}
                                </div>

                                {/* Content */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                                        <p style={{ fontSize: '0.7rem', color: '#e2e8f0', fontFamily: 'Space Grotesk, monospace', fontWeight: 500 }}>
                                            {e.label}
                                        </p>
                                        <span style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace', whiteSpace: 'nowrap', flexShrink: 0 }}>
                                            {formatDate(e.date)}
                                        </span>
                                    </div>
                                    {e.detail && (
                                        <p style={{ fontSize: '0.6rem', color: '#475569', fontFamily: 'Space Grotesk, monospace', marginTop: '0.15rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {e.detail}
                                        </p>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
