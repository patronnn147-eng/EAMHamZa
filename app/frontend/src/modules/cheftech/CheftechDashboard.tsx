import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertTriangle, BarChart2 } from 'lucide-react';
import {
  DashboardStatsCards,
  InterventionsTab,
  MachinesTab,
  TechniciansTab,
  WorkOrdersTab,
  CompletedWorkOrdersTab,
  AnalyticsTab,
} from './dashboard/components';
import { useCheftechDashboardData } from './dashboard/hooks';
import { ReliabilityDashboardTab } from '@/modules/shared/ReliabilityDashboardTab';

interface CheftechDashboardProps {
  role?: string;
}

const CheftechDashboard: React.FC<CheftechDashboardProps> = ({ role }) => {
  const navigate = useNavigate();
  const [userRole, setUserRole] = useState<string>(role || 'CHEFTECH');
  const {
    stats,
    interventions,
    workOrders,
    technicians,
    machines,
    loading,
    fetchInterventions,
    fetchTechnicians,
    fetchMachines,
    assignWorkOrder,
    updateMachineStatus,
    approveIntervention,
    rejectIntervention,
    validateWorkOrder,
    rejectWorkOrder,
  } = useCheftechDashboardData();

  const isAdmin = userRole === 'ADMIN';

  useEffect(() => {
    if (role) return; // Skip fetching if role is forced
    const fetchUserRole = async () => {
      try {
        const userData = await client.auth.me();
        if (userData.data) {
          // Use the role directly from auth.me response
          setUserRole(userData.data.role);
        }
      } catch (error) {
        console.error('Error fetching user role:', error);
      }
    };
    fetchUserRole();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const getDashboardTitle = () => {
    switch (userRole) {
      case 'ADMIN': return 'Administration - Tableau de Bord';
      case 'CHETOP': return 'Chef des Opérations - Tableau de Bord';
      default: return 'Chef Technique - Tableau de Bord';
    }
  };

  const getDashboardSubTitle = () => {
    switch (userRole) {
      case 'ADMIN': return 'Gestion complète du système et supervision';
      case 'CHETOP': return 'Pilotage des opérations et maintenance';
      default: return 'Supervision technique et gestion des équipes';
    }
  };

  return (
    <div className="min-h-screen bg-transparent p-8 animate-premium-fade-in">
      <div className="max-w-[1600px] mx-auto">
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-black text-gray-900 dark:text-white tracking-tight leading-none mb-3">
              {getDashboardTitle()}
            </h1>
            <p className="text-gray-500 font-medium text-lg max-w-2xl border-l-4 border-gradient-premium pl-4 py-1">
              {getDashboardSubTitle()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-4 py-2 glass rounded-2xl border-gray-200 dark:border-gray-800 shadow-sm flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-tighter">Système En Ligne</span>
            </div>
          </div>
        </div>

        {stats && <DashboardStatsCards stats={stats} machines={machines} />}

        <Tabs defaultValue="interventions" className="space-y-6">
          <TabsList>
            <TabsTrigger value="interventions">Interventions</TabsTrigger>
            <TabsTrigger value="ordres">Ordres de travail</TabsTrigger>
            <TabsTrigger value="techniciens">Techniciens</TabsTrigger>
            <TabsTrigger value="machines">Machines</TabsTrigger>
            <TabsTrigger value="fiabilite" className="flex items-center gap-1.5">
              <BarChart2 className="h-3.5 w-3.5" />
              Fiabilité
            </TabsTrigger>
            <TabsTrigger value="analytics">Analytics & PDCA</TabsTrigger>
            <TabsTrigger value="completes">Complétés</TabsTrigger>
            <TabsTrigger value="urgent-alert">Alerte Urgente</TabsTrigger>
          </TabsList>

          <TabsContent value="interventions">
            <InterventionsTab
              interventions={interventions}
              fetchInterventions={fetchInterventions}
              approveIntervention={isAdmin ? undefined : approveIntervention}
              rejectIntervention={isAdmin ? undefined : rejectIntervention}
            />
          </TabsContent>

          <TabsContent value="ordres">
            <WorkOrdersTab
              workOrders={workOrders}
              technicians={technicians}
              machines={machines}
              assignWorkOrder={isAdmin ? undefined : assignWorkOrder}
              validateWorkOrder={isAdmin ? undefined : validateWorkOrder}
              rejectWorkOrder={isAdmin ? undefined : rejectWorkOrder}
            />
          </TabsContent>

          <TabsContent value="analytics">
            <AnalyticsTab />
          </TabsContent>

          <TabsContent value="completes">
            <CompletedWorkOrdersTab />
          </TabsContent>

          <TabsContent value="techniciens">
            <TechniciansTab technicians={technicians} fetchTechnicians={fetchTechnicians} />
          </TabsContent>

          <TabsContent value="machines">
            <MachinesTab
              machines={machines}
              fetchMachines={fetchMachines}
              updateMachineStatus={updateMachineStatus}
            />
          </TabsContent>

          <TabsContent value="fiabilite">
            <ReliabilityDashboardTab />
          </TabsContent>

          <TabsContent value="urgent-alert">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-red-600 flex items-center gap-2">
                  <AlertTriangle className="h-6 w-6" />
                  Alertes Urgentes
                </h2>
                <Button
                  onClick={() => navigate('/cheftech/urgent-alert')}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Nouvelle Alerte
                </Button>
              </div>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center text-gray-600">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">Gestion des Alertes Urgentes</p>
                    <p className="text-sm">
                      Créez et gérez les alertes urgentes émises par les techniciens.
                      Les responsables sont notifiés immédiatement.
                    </p>
                    <Button
                      onClick={() => navigate('/cheftech/urgent-alert')}
                      className="mt-4 bg-red-600 hover:bg-red-700"
                    >
                      <AlertTriangle className="mr-2 h-4 w-4" />
                      Créer une Alerte
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default CheftechDashboard;
