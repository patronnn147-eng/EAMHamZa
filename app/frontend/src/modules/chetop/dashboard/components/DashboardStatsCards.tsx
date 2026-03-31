import React from 'react';
import { Card } from '@/components/ui/card';
import { 
  ClipboardList, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  Settings, 
  Activity,
  AlertTriangle
} from 'lucide-react';
import type { DashboardStats } from '../types';

interface DashboardStatsCardsProps {
  stats: DashboardStats;
}

export const DashboardStatsCards: React.FC<DashboardStatsCardsProps> = ({ stats }) => {
  const cards = [
    {
      title: 'Total Demandes',
      value: stats.total_requests,
      icon: ClipboardList,
      color: 'text-violet-600',
      bg: 'bg-violet-50',
    },
    {
      title: 'En Attente',
      value: stats.requests_pending,
      icon: Clock,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      title: 'Approuvées',
      value: stats.requests_approved,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      title: 'Rejetées',
      value: stats.requests_rejected,
      icon: XCircle,
      color: 'text-rose-600',
      bg: 'bg-rose-50',
    },
    {
      title: 'Total Machines',
      value: stats.total_machines,
      icon: Settings,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      title: 'En Maintenance',
      value: stats.machines_en_maintenance,
      icon: Activity,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
    },
    {
      title: 'Hors Service',
      value: stats.machines_hors_service,
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-6 mb-8">
      {cards.map((card, index) => (
        <Card key={index} className="p-6 border-none shadow-xl bg-white/70 backdrop-blur-md rounded-3xl hover:translate-y-[-4px] transition-all duration-300 group">
          <div className={`${card.bg} w-12 h-12 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
            <card.icon className={`h-6 w-6 ${card.color}`} />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-bold text-gray-500 uppercase tracking-tight">{card.title}</p>
            <p className="text-3xl font-black text-gray-900">{card.value}</p>
          </div>
        </Card>
      ))}
    </div>
  );
};
