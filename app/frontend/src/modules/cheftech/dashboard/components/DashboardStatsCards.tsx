import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Activity, Settings, Users, Wrench } from 'lucide-react';
import type { DashboardStats } from '../types';

interface DashboardStatsCardsProps {
  stats: DashboardStats;
}

export const DashboardStatsCards: React.FC<DashboardStatsCardsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
    </div>
  );
};
