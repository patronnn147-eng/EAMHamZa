import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
    format,
    startOfDay,
    differenceInCalendarDays,
    startOfMonth,
    endOfMonth,
    eachDayOfInterval,
    getDay,
    isSameMonth,
    isWithinInterval,
    isSameDay,
    addMonths,
    subMonths,
} from 'date-fns';

interface User {
    id: number;
    nom: string;
    email: string;
    role: string;
    shift_type?: string | null;
}

interface Planning {
    id: number;
    identifiant_planning: string;
    date_debut: string;
    date_fin: string;
    type: string;
    shift_type?: string;
    zone_travail?: string;
    assigned_users: User[];
}

const COLORS = {
    bg: '#0b1326',
    surfaceLow: '#131b2e',
    surfaceHigh: '#222a3d',
    surfaceHighest: '#2d3449',
    glass: 'rgba(19, 27, 46, 0.45)',
    primary: '#9fcaff',
    primaryContainer: '#0099ff',
    secondary: '#e0b6ff',
    secondaryContainer: '#6d11ad',
    error: '#ffb4ab',
    errorContainer: 'rgba(147, 0, 10, 0.4)',
    onSurface: '#dae2fd',
    onSurfaceVariant: '#bfc7d5',
    outlineVariant: '#3f4753',
    cyan400: '#22d3ee',
    orange400: '#fb923c',
    purple500: '#a855f7',
};

const WEEK_DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

function getTypeColor(type: string): string {
    switch (type.toUpperCase()) {
        case 'MAINTENANCE': return COLORS.orange400;
        case 'SHIFT': return COLORS.primary;
        default: return COLORS.cyan400;
    }
}

function getTypeLabel(type: string): string {
    const map: Record<string, string> = {
        MAINTENANCE: 'Maintenance',
        SHIFT: 'Shift',
    };
    return map[type.toUpperCase()] ?? type;
}

function getUserInitials(nom: string): string {
    return nom.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
}

function MonthCalendar({
    viewMonth,
    startDate,
    endDate,
    typeColor,
}: {
    viewMonth: Date;
    startDate: Date;
    endDate: Date;
    typeColor: string;
}) {
    const monthStart = startOfMonth(viewMonth);
    const monthEnd = endOfMonth(viewMonth);
    const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // ISO week starts Monday (0=Mon … 6=Sun), getDay() returns 0=Sun..6=Sat
    const firstDow = getDay(monthStart); // 0=Sun
    const paddingBefore = firstDow === 0 ? 6 : firstDow - 1; // shift so Mon=0

    const cells: (Date | null)[] = [
        ...Array(paddingBefore).fill(null),
        ...days,
    ];
    // Pad to full rows
    while (cells.length % 7 !== 0) cells.push(null);

    return (
        <div>
            <div
                className="grid grid-cols-7 mb-1"
                style={{ gap: 2 }}
            >
                {WEEK_DAYS.map(d => (
                    <div
                        key={d}
                        className="text-center py-2 text-xs font-bold uppercase tracking-widest"
                        style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                    >
                        {d}
                    </div>
                ))}
            </div>
            <div className="grid grid-cols-7" style={{ gap: 4 }}>
                {cells.map((day, i) => {
                    if (!day) {
                        return <div key={`empty-${i}`} className="rounded-lg" style={{ aspectRatio: '1/1' }} />;
                    }
                    const inRange = isWithinInterval(day, { start: startDate, end: endDate });
                    const isStart = isSameDay(day, startDate);
                    const isEnd = isSameDay(day, endDate);
                    const isCurrentMonth = isSameMonth(day, viewMonth);
                    const isToday = isSameDay(day, startOfDay(new Date()));

                    return (
                        <div
                            key={day.toISOString()}
                            className="flex flex-col p-1 rounded-lg transition-all"
                            style={{
                                aspectRatio: '1/1',
                                background: isStart || isEnd
                                    ? `${typeColor}22`
                                    : inRange
                                        ? 'rgba(19,27,46,0.6)'
                                        : 'rgba(19,27,46,0.3)',
                                border: isStart || isEnd
                                    ? `1px solid ${typeColor}60`
                                    : inRange
                                        ? `1px solid ${typeColor}25`
                                        : `1px solid transparent`,
                                opacity: isCurrentMonth ? 1 : 0.3,
                            }}
                        >
                            <span
                                className="text-xs font-bold leading-none"
                                style={{
                                    color: isStart || isEnd
                                        ? typeColor
                                        : isToday
                                            ? COLORS.primary
                                            : COLORS.onSurface,
                                    fontFamily: 'Space Grotesk, sans-serif',
                                }}
                            >
                                {format(day, 'd')}
                            </span>
                            {inRange && (
                                <div
                                    className="mt-auto rounded-full"
                                    style={{
                                        height: 3,
                                        background: typeColor,
                                        opacity: isStart || isEnd ? 1 : 0.5,
                                    }}
                                />
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function PlanningCalendarView() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [planning, setPlanning] = useState<Planning | null>(null);
    const [loading, setLoading] = useState(true);
    const [viewMonth, setViewMonth] = useState<Date>(new Date());

    useEffect(() => {
        if (id) fetchPlanningDetail(id);
    }, [id]);

    const fetchPlanningDetail = async (planningId: string) => {
        try {
            const response = await client.apiCall.invoke({
                url: `/api/v1/plannings/${planningId}`,
                method: 'GET',
            });

            console.log('[CalendarView] raw response:', JSON.stringify(response, null, 2));

            // Unwrap SDK envelope — handles single and double nesting
            const raw = (response as any)?.data ?? response;
            let planningObj: Planning = (raw?.identifiant_planning ? raw : raw?.data ?? raw) as Planning;

            console.log('[CalendarView] planningObj after unwrap:', planningObj);
            console.log('[CalendarView] assigned_users:', planningObj?.assigned_users);

            // Fallback: if assigned_users is missing/empty, fetch from list endpoint
            if (!planningObj?.assigned_users?.length) {
                console.log('[CalendarView] assigned_users empty, trying list fallback...');
                try {
                    const listResp = await client.apiCall.invoke({
                        url: `/api/v1/plannings?page=1&size=200`,
                        method: 'GET',
                    });
                    const listRaw = (listResp as any)?.data ?? listResp;
                    const items: Planning[] = listRaw?.items ?? (Array.isArray(listRaw) ? listRaw : []);
                    const match = items.find((p) => String(p.id) === String(planningId));
                    console.log('[CalendarView] list fallback match:', match);
                    if (match?.assigned_users?.length) {
                        planningObj = { ...planningObj, assigned_users: match.assigned_users };
                    }
                } catch {
                    // silently ignore list fallback errors
                }
            }

            setPlanning(planningObj);
            if (planningObj?.date_debut) {
                setViewMonth(startOfDay(new Date(planningObj.date_debut)));
            }
        } catch {
            toast({ title: 'Error', description: 'Failed to load planning details', variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div
                className="flex items-center justify-center h-64"
                style={{ background: COLORS.bg }}
            >
                <div
                    className="rounded-full h-12 w-12 border-b-2 animate-spin"
                    style={{ borderColor: COLORS.primaryContainer }}
                />
            </div>
        );
    }

    if (!planning) {
        return (
            <div
                className="min-h-screen flex flex-col items-center justify-center gap-4"
                style={{ background: COLORS.bg }}
            >
                <div style={{ color: COLORS.error, fontSize: 48 }}>⚠</div>
                <h3 className="text-lg font-bold" style={{ color: COLORS.onSurface }}>Planning Not Found</h3>
                <button
                    onClick={() => navigate(-1)}
                    className="px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider"
                    style={{
                        background: COLORS.glass,
                        color: COLORS.primary,
                        border: `1px solid ${COLORS.primary}30`,
                        backdropFilter: 'blur(16px)',
                        fontFamily: 'Space Grotesk, sans-serif',
                    }}
                >
                    ← Back
                </button>
            </div>
        );
    }

    const startDate = startOfDay(new Date(planning.date_debut));
    const endDate = startOfDay(new Date(planning.date_fin));
    const durationDays = differenceInCalendarDays(endDate, startDate) + 1;
    const typeColor = getTypeColor(planning.type);
    const typeLabel = getTypeLabel(planning.type);

    const glassPanelStyle: React.CSSProperties = {
        background: COLORS.glass,
        backdropFilter: 'blur(16px)',
        border: `1px solid ${COLORS.primary}15`,
        boxShadow: '0px 24px 48px -12px rgba(0,153,255,0.08)',
    };

    return (
        <div
            className="min-h-screen relative overflow-hidden"
            style={{ background: COLORS.bg, color: COLORS.onSurface }}
        >
            {/* Ambient glows */}
            <div
                className="absolute pointer-events-none rounded-full"
                style={{
                    top: '-10%', left: '-5%',
                    width: '40%', height: '40%',
                    background: `${COLORS.primaryContainer}18`,
                    filter: 'blur(120px)',
                }}
            />
            <div
                className="absolute pointer-events-none rounded-full"
                style={{
                    bottom: '-10%', right: '-5%',
                    width: '30%', height: '30%',
                    background: `${COLORS.secondary}18`,
                    filter: 'blur(100px)',
                }}
            />

            <div className="relative px-6 py-8 flex flex-col gap-8 max-w-[1400px] mx-auto">
                {/* Back + Header row */}
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate(-1)}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider transition-all"
                        style={{
                            background: COLORS.glass,
                            color: COLORS.onSurfaceVariant,
                            border: `1px solid ${COLORS.outlineVariant}30`,
                            backdropFilter: 'blur(16px)',
                            fontFamily: 'Space Grotesk, sans-serif',
                        }}
                    >
                        ← Back
                    </button>
                </div>

                {/* Title + Actions */}
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                    <div>
                        <h2
                            className="text-4xl font-extrabold tracking-tight"
                            style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.onSurface }}
                        >
                            Planning Calendar
                        </h2>
                        <p className="mt-1 text-sm" style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Inter, sans-serif' }}>
                            {planning.identifiant_planning} &mdash; Schedule overview and team deployment
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            className="px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all"
                            style={{
                                background: COLORS.glass,
                                color: COLORS.onSurface,
                                border: `1px solid ${COLORS.outlineVariant}30`,
                                backdropFilter: 'blur(16px)',
                                fontFamily: 'Space Grotesk, sans-serif',
                            }}
                            onClick={() => navigate(`/admin/planning/${id}`)}
                        >
                            ≡ Details
                        </button>
                    </div>
                </div>

                {/* KPI Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
                    {/* Duration */}
                    <div
                        className="p-5 rounded-2xl relative overflow-hidden"
                        style={glassPanelStyle}
                    >
                        <div
                            className="absolute top-0 right-0 p-3 text-5xl opacity-10"
                            style={{ color: COLORS.primary }}
                        >
                            📅
                        </div>
                        <p
                            className="text-xs font-bold uppercase tracking-widest"
                            style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                        >
                            Duration
                        </p>
                        <h3
                            className="text-4xl font-bold mt-2"
                            style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.onSurface }}
                        >
                            {durationDays}
                        </h3>
                        <div className="mt-3 flex items-center gap-1.5 text-xs" style={{ color: COLORS.cyan400 }}>
                            <span>days</span>
                        </div>
                    </div>

                    {/* Team size */}
                    <div
                        className="p-5 rounded-2xl relative overflow-hidden"
                        style={glassPanelStyle}
                    >
                        <div
                            className="absolute top-0 right-0 p-3 text-5xl opacity-10"
                            style={{ color: COLORS.secondary }}
                        >
                            👥
                        </div>
                        <p
                            className="text-xs font-bold uppercase tracking-widest"
                            style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                        >
                            Team Size
                        </p>
                        <h3
                            className="text-4xl font-bold mt-2"
                            style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.secondary }}
                        >
                            {planning.assigned_users.length}
                        </h3>
                        <div
                            className="mt-3 w-full rounded-full overflow-hidden"
                            style={{ height: 3, background: 'rgba(255,255,255,0.08)' }}
                        >
                            <div
                                className="h-full rounded-full"
                                style={{
                                    width: `${Math.min(planning.assigned_users.length * 10, 100)}%`,
                                    background: COLORS.secondary,
                                }}
                            />
                        </div>
                    </div>

                    {/* Type */}
                    <div
                        className="p-5 rounded-2xl relative overflow-hidden"
                        style={glassPanelStyle}
                    >
                        <div
                            className="absolute top-0 right-0 p-3 text-5xl opacity-10"
                            style={{ color: typeColor }}
                        >
                            ⚙
                        </div>
                        <p
                            className="text-xs font-bold uppercase tracking-widest"
                            style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                        >
                            Type
                        </p>
                        <h3
                            className="text-2xl font-bold mt-2"
                            style={{ fontFamily: 'Manrope, sans-serif', color: typeColor }}
                        >
                            {typeLabel}
                        </h3>
                        {planning.shift_type && (
                            <div className="mt-3 flex items-center gap-1.5 text-xs" style={{ color: typeColor }}>
                                ↻ {planning.shift_type}
                            </div>
                        )}
                    </div>

                    {/* Work Zone */}
                    <div
                        className="p-5 rounded-2xl relative overflow-hidden"
                        style={glassPanelStyle}
                    >
                        <div
                            className="absolute top-0 right-0 p-3 text-5xl opacity-10"
                            style={{ color: COLORS.primary }}
                        >
                            📍
                        </div>
                        <p
                            className="text-xs font-bold uppercase tracking-widest"
                            style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                        >
                            Work Zone
                        </p>
                        <h3
                            className="text-xl font-bold mt-2 leading-tight"
                            style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.primary }}
                        >
                            {planning.zone_travail || '—'}
                        </h3>
                        <div className="mt-3 flex items-center gap-1.5 text-xs" style={{ color: COLORS.primary }}>
                            ✓ Optimal uptime maintained
                        </div>
                    </div>
                </div>

                {/* Calendar + Side panels */}
                <div className="grid grid-cols-1 xl:grid-cols-12 gap-7 items-start">
                    {/* Calendar */}
                    <div
                        className="xl:col-span-8 rounded-2xl overflow-hidden"
                        style={glassPanelStyle}
                    >
                        {/* Calendar header */}
                        <div
                            className="px-6 py-4 flex justify-between items-center"
                            style={{ borderBottom: `1px solid ${COLORS.outlineVariant}18` }}
                        >
                            <h3
                                className="font-bold text-xl flex items-center gap-2"
                                style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.onSurface }}
                            >
                                <span style={{ color: COLORS.primary }}>📅</span>
                                {format(viewMonth, 'MMMM yyyy')}
                            </h3>
                            <div className="flex gap-1 items-center">
                                <button
                                    onClick={() => setViewMonth(m => subMonths(m, 1))}
                                    className="w-8 h-8 flex items-center justify-center rounded-lg transition-all"
                                    style={{ color: COLORS.onSurfaceVariant, background: 'transparent' }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                >
                                    ‹
                                </button>
                                <button
                                    onClick={() => setViewMonth(startOfDay(new Date(planning.date_debut)))}
                                    className="px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-lg transition-all"
                                    style={{
                                        color: COLORS.primaryContainer,
                                        fontFamily: 'Space Grotesk, sans-serif',
                                    }}
                                >
                                    Today
                                </button>
                                <button
                                    onClick={() => setViewMonth(m => addMonths(m, 1))}
                                    className="w-8 h-8 flex items-center justify-center rounded-lg transition-all"
                                    style={{ color: COLORS.onSurfaceVariant }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                >
                                    ›
                                </button>
                            </div>
                        </div>

                        {/* Calendar grid */}
                        <div className="p-5 overflow-x-auto">
                            <div style={{ minWidth: 480 }}>
                                <MonthCalendar
                                    viewMonth={viewMonth}
                                    startDate={startDate}
                                    endDate={endDate}
                                    typeColor={typeColor}
                                />
                            </div>
                        </div>

                        {/* Legend */}
                        <div
                            className="px-6 py-4 flex gap-6"
                            style={{
                                background: 'rgba(11,19,38,0.4)',
                                borderTop: `1px solid ${COLORS.outlineVariant}18`,
                            }}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className="rounded-full"
                                    style={{ width: 10, height: 10, background: typeColor }}
                                />
                                <span
                                    className="text-xs font-bold uppercase tracking-widest"
                                    style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                                >
                                    {typeLabel}
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div
                                    className="rounded-full"
                                    style={{ width: 10, height: 10, background: COLORS.primaryContainer }}
                                />
                                <span
                                    className="text-xs font-bold uppercase tracking-widest"
                                    style={{ color: COLORS.onSurfaceVariant, fontFamily: 'Space Grotesk, sans-serif' }}
                                >
                                    Range
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Right column */}
                    <div className="xl:col-span-4 flex flex-col gap-6">
                        {/* Assigned Users */}
                        <div
                            className="rounded-2xl p-6"
                            style={glassPanelStyle}
                        >
                            <h3
                                className="font-bold text-lg mb-5"
                                style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.onSurface }}
                            >
                                Assigned Team
                            </h3>
                            <div className="flex flex-col gap-3">
                                {planning.assigned_users.length === 0 && (
                                    <p
                                        className="text-sm py-4 text-center"
                                        style={{ color: COLORS.onSurfaceVariant }}
                                    >
                                        No users assigned
                                    </p>
                                )}
                                {planning.assigned_users.map(user => (
                                    <div
                                        key={user.id}
                                        className="flex items-center justify-between p-3 rounded-xl transition-all cursor-default"
                                        style={{
                                            background: `${COLORS.surfaceHigh}55`,
                                            border: `1px solid ${COLORS.outlineVariant}20`,
                                        }}
                                        onMouseEnter={e => (e.currentTarget.style.background = `${COLORS.surfaceHigh}90`)}
                                        onMouseLeave={e => (e.currentTarget.style.background = `${COLORS.surfaceHigh}55`)}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div
                                                className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
                                                style={{
                                                    background: `${COLORS.primaryContainer}30`,
                                                    color: COLORS.primary,
                                                    border: `1.5px solid ${COLORS.primary}35`,
                                                    fontFamily: 'Space Grotesk, sans-serif',
                                                }}
                                            >
                                                {getUserInitials(user.nom)}
                                            </div>
                                            <div>
                                                <p
                                                    className="font-bold text-sm leading-tight"
                                                    style={{ color: COLORS.onSurface }}
                                                >
                                                    {user.nom}
                                                </p>
                                                <p
                                                    className="text-xs uppercase tracking-wide"
                                                    style={{ color: COLORS.primary, fontFamily: 'Space Grotesk, sans-serif' }}
                                                >
                                                    {user.role}
                                                </p>
                                            </div>
                                        </div>
                                        <span style={{ color: COLORS.outlineVariant }}>›</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Schedule Summary */}
                        <div
                            className="rounded-2xl p-6"
                            style={{
                                ...glassPanelStyle,
                                background: `linear-gradient(135deg, ${COLORS.primaryContainer}18, ${COLORS.secondaryContainer}18)`,
                                border: `1px solid ${COLORS.primary}20`,
                            }}
                        >
                            <h4
                                className="font-bold text-sm mb-1"
                                style={{ fontFamily: 'Manrope, sans-serif', color: COLORS.onSurface }}
                            >
                                Schedule Window
                            </h4>
                            <p
                                className="text-xs mb-4"
                                style={{ color: COLORS.onSurfaceVariant }}
                            >
                                This planning spans {durationDays} day{durationDays !== 1 ? 's' : ''}.
                            </p>
                            <div className="flex flex-col gap-2">
                                <div
                                    className="flex justify-between text-xs rounded-lg px-3 py-2"
                                    style={{ background: 'rgba(255,255,255,0.05)', fontFamily: 'Space Grotesk, sans-serif' }}
                                >
                                    <span style={{ color: COLORS.onSurfaceVariant }}>Start</span>
                                    <span style={{ color: COLORS.primary, fontWeight: 700 }}>
                                        {format(startDate, 'MMM d, yyyy')}
                                    </span>
                                </div>
                                <div
                                    className="flex justify-between text-xs rounded-lg px-3 py-2"
                                    style={{ background: 'rgba(255,255,255,0.05)', fontFamily: 'Space Grotesk, sans-serif' }}
                                >
                                    <span style={{ color: COLORS.onSurfaceVariant }}>End</span>
                                    <span style={{ color: COLORS.secondary, fontWeight: 700 }}>
                                        {format(endDate, 'MMM d, yyyy')}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
