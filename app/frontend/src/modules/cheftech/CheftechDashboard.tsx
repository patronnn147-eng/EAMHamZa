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
  } = useCheftechDashboardData();

  useEffect(() => {
    if (role) return; // Skip fetching if role is forced
    const fetchUserRole = async () => {
      try {
        const userData = await client.auth.me();
        if (userData.data) {
          const response = await client.entities.utilisateurs.query({
            query: { user_id: userData.data.id },
            limit: 1
          });
          if (response.data.items && response.data.items.length > 0) {
            setUserRole(response.data.items[0].role);
          }
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">{getDashboardTitle()}</h1>
          <p className="text-gray-600 mt-2">{getDashboardSubTitle()}</p>
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
            <TabsTrigger value="urgent-alert">Alerte Urgente</TabsTrigger>
          </TabsList>

          <TabsContent value="interventions">
            <InterventionsTab
              interventions={interventions}
              fetchInterventions={fetchInterventions}
              approveIntervention={approveIntervention}
              rejectIntervention={rejectIntervention}
            />
          </TabsContent>

          <TabsContent value="ordres">
            <WorkOrdersTab
              workOrders={workOrders}
              technicians={technicians}
              machines={machines}
              assignWorkOrder={assignWorkOrder}
            />
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
