import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Alert {
  id: number;
  alert_id: string;
  machine_id: number;
  alert_type: string;
  severity: string;
  message: string;
  rul_days?: number;
  failure_probability?: number;
  is_active: boolean;
  is_linked_to_wo: boolean;
  work_order_id?: number;
  priority?: string;
  created_at: string;
  dismissed_at?: string;
  dismissed_by?: number;
}

export interface Technician {
  id: number;
  nom: string;
  email: string;
  role: string;
}

// ─── Severity Config ──────────────────────────────────────────────────────────

export const severityConfig: Record<string, {
  border: string;
  iconBg: string;
  icon: React.ReactNode;
  badgeClass: string;
  barColor: string;
  glow: string;
  label: string;
}> = {
  CRITICAL: {
    border: 'border-l-red-500',
    iconBg: 'bg-red-500/10',
    icon: <AlertTriangle className="h-5 w-5 text-red-500" />,
    badgeClass: 'bg-red-500/20 text-red-400 border-red-500/30',
    barColor: 'bg-red-500',
    glow: 'shadow-red-500/10',
    label: 'CRITICAL',
  },
  HIGH: {
    border: 'border-l-orange-500',
    iconBg: 'bg-orange-500/10',
    icon: <AlertCircle className="h-5 w-5 text-orange-400" />,
    badgeClass: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    barColor: 'bg-orange-500',
    glow: 'shadow-orange-500/10',
    label: 'HIGH',
  },
  MEDIUM: {
    border: 'border-l-yellow-500',
    iconBg: 'bg-yellow-500/10',
    icon: <AlertCircle className="h-5 w-5 text-yellow-400" />,
    badgeClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    barColor: 'bg-yellow-500',
    glow: 'shadow-yellow-500/10',
    label: 'MEDIUM',
  },
  LOW: {
    border: 'border-l-blue-500',
    iconBg: 'bg-blue-500/10',
    icon: <Info className="h-5 w-5 text-blue-400" />,
    badgeClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    barColor: 'bg-blue-500',
    glow: 'shadow-blue-500/10',
    label: 'LOW',
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function getRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}j`;
}
