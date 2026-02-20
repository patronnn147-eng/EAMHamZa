import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Activity, Settings, Users, Wrench, CalendarClock } from 'lucide-react';
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Interventions</p>
              <p className="text-2xl font-bold">{stats.total_interventions}</p>
              <p className="text-xs text-gray-500">{stats.interventions_en_cours} en cours</p>
            </div>
            <Wrench className="h-8 w-8 text-blue-600" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Ordres de travail</p>
              <p className="text-2xl font-bold">{stats.total_ordres_travail}</p>
              <p className="text-xs text-gray-500">{stats.ordres_en_attente} en attente</p>
            </div>
            <Activity className="h-8 w-8 text-green-600" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Techniciens</p>
              <p className="text-2xl font-bold">{stats.total_techniciens}</p>
              <p className="text-xs text-gray-500">{stats.techniciens_disponibles} disponibles</p>
            </div>
            <Users className="h-8 w-8 text-purple-600" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Machines</p>
              <p className="text-2xl font-bold">{stats.total_machines}</p>
              <p className="text-xs text-gray-500">{stats.machines_critiques} critiques</p>
            </div>
            <Settings className="h-8 w-8 text-orange-600" />
          </div>
        </CardContent>
      </Card>

      <Card className={overdueMaintenance > 0 ? 'border-red-400' : upcomingMaintenance > 0 ? 'border-amber-400' : ''}>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Maintenance préventive</p>
              <p className="text-2xl font-bold">{upcomingMaintenance + overdueMaintenance}</p>
              <p className={`text-xs ${overdueMaintenance > 0 ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                {overdueMaintenance > 0
                  ? `${overdueMaintenance} en retard`
                  : upcomingMaintenance > 0
                    ? `${upcomingMaintenance} à venir (7j)`
                    : 'Aucune à venir'}
              </p>
            </div>
            <CalendarClock className={`h-8 w-8 ${overdueMaintenance > 0 ? 'text-red-600' : 'text-amber-500'}`} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
