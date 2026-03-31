import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Activity, Settings, Users, Wrench, CalendarClock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DashboardStats, Machine } from '../types';

interface DashboardStatsCardsProps {
  stats: DashboardStats;
  machines?: Machine[];
}

export const DashboardStatsCards: React.FC<DashboardStatsCardsProps> = ({ stats, machines = [] }) => {
  const now = new Date();
  const in7Days = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

  const upcomingMaintenance = machines.filter((m) => {
    if (!m.date_prochaine_maintenance) return false;
    const d = new Date(m.date_prochaine_maintenance);
    return d >= now && d <= in7Days;
  }).length;

  const overdueMaintenance = machines.filter((m) => {
    if (!m.date_prochaine_maintenance) return false;
    return new Date(m.date_prochaine_maintenance) < now;
  }).length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-10 mt-2">
      <Card className="border-none shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-1 bg-white dark:bg-gray-900 group overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
          <Wrench className="h-16 w-16 -mr-4 -mt-4" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Interventions</p>
              <p className="text-3xl font-extrabold text-gray-900 dark:text-white">{stats.total_interventions}</p>
              <div className="flex items-center mt-2">
                <span className="flex h-2 w-2 rounded-full bg-blue-500 mr-2 animate-pulse" />
                <p className="text-[11px] font-medium text-gray-500">{stats.interventions_en_cours} en cours</p>
              </div>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-2xl shadow-sm group-hover:scale-110 transition-transform duration-300">
              <Wrench className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-none shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-1 bg-white dark:bg-gray-900 group overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
          <Activity className="h-16 w-16 -mr-4 -mt-4" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Ordres de Travail</p>
              <p className="text-3xl font-extrabold text-gray-900 dark:text-white">{stats.total_ordres_travail}</p>
              <div className="flex items-center mt-2">
                <span className="flex h-2 w-2 rounded-full bg-emerald-500 mr-2" />
                <p className="text-[11px] font-medium text-gray-500">{stats.ordres_en_attente} en attente</p>
              </div>
            </div>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/30 rounded-2xl shadow-sm group-hover:scale-110 transition-transform duration-300">
              <Activity className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-none shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-1 bg-white dark:bg-gray-900 group overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
          <Users className="h-16 w-16 -mr-4 -mt-4" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Techniciens</p>
              <p className="text-3xl font-extrabold text-gray-900 dark:text-white">{stats.total_techniciens}</p>
              <div className="flex items-center mt-2">
                <span className="flex h-2 w-2 rounded-full bg-purple-500 mr-2" />
                <p className="text-[11px] font-medium text-gray-500">{stats.techniciens_disponibles} disponibles</p>
              </div>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/30 rounded-2xl shadow-sm group-hover:scale-110 transition-transform duration-300">
              <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-none shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-1 bg-white dark:bg-gray-900 group overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
          <Settings className="h-16 w-16 -mr-4 -mt-4" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Parc Machines</p>
              <p className="text-3xl font-extrabold text-gray-900 dark:text-white">{stats.total_machines}</p>
              <div className="flex items-center mt-2">
                <span className="flex h-2 w-2 rounded-full bg-orange-500 mr-2" />
                <p className="text-[11px] font-medium text-gray-500">{stats.machines_critiques} critiques</p>
              </div>
            </div>
            <div className="p-3 bg-orange-50 dark:bg-orange-900/30 rounded-2xl shadow-sm group-hover:scale-110 transition-transform duration-300">
              <Settings className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className={cn(
        "border-none shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-1 group overflow-hidden relative",
        overdueMaintenance > 0 ? 'bg-red-50 dark:bg-red-950' : upcomingMaintenance > 0 ? 'bg-amber-50 dark:bg-amber-950' : 'bg-white dark:bg-gray-900'
      )}>
        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-current">
          <CalendarClock className="h-16 w-16 -mr-4 -mt-4 text-current" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Maintenance Prev.</p>
              <p className={cn(
                "text-3xl font-extrabold",
                overdueMaintenance > 0 ? 'text-red-700 dark:text-red-400' : 'text-gray-900 dark:text-white'
              )}>
                {upcomingMaintenance + overdueMaintenance}
              </p>
              <p className={cn(
                "text-[11px] font-bold mt-2",
                overdueMaintenance > 0 ? 'text-red-600 animate-pulse' : upcomingMaintenance > 0 ? 'text-amber-600' : 'text-gray-500'
              )}>
                {overdueMaintenance > 0
                  ? `${overdueMaintenance} EN RETARD`
                  : upcomingMaintenance > 0
                    ? `${upcomingMaintenance} À VENIR (7j)`
                    : 'Aucune à venir'}
              </p>
            </div>
            <div className={cn(
              "p-3 rounded-2xl shadow-sm group-hover:scale-110 transition-transform duration-300",
              overdueMaintenance > 0 ? 'bg-red-200 dark:bg-red-800' : 'bg-amber-100 dark:bg-amber-900/30'
            )}>
              <CalendarClock className={cn(
                "h-6 w-6",
                overdueMaintenance > 0 ? 'text-red-700 dark:text-red-100' : 'text-amber-600 dark:text-amber-400'
              )} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
