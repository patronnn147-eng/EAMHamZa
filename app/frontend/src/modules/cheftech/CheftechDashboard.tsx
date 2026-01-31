import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DashboardStatsCards,
  InterventionsTab,
  MachinesTab,
  TechniciansTab,
  WorkOrdersTab,
} from './dashboard/components';
import { useCheftechDashboardData } from './dashboard/hooks';

const CheftechDashboard: React.FC = () => {
  const {
    stats,
    interventions,
    workOrders,
    technicians,
    machines,
    loading,
    selectedTechnician,
    selectedIntervention,
    setSelectedTechnician,
    setSelectedIntervention,
    fetchInterventions,
    fetchTechnicians,
    fetchMachines,
    assignTechnician,
    updateMachineStatus,
  } = useCheftechDashboardData();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Chef Technique Dashboard</h1>
          <p className="text-gray-600 mt-2">Supervision technique et gestion des équipes</p>
        </div>

        {stats && <DashboardStatsCards stats={stats} />}

        <Tabs defaultValue="interventions" className="space-y-6">
          <TabsList>
            <TabsTrigger value="interventions">Interventions</TabsTrigger>
            <TabsTrigger value="ordres">Ordres de travail</TabsTrigger>
            <TabsTrigger value="techniciens">Techniciens</TabsTrigger>
            <TabsTrigger value="machines">Machines</TabsTrigger>
          </TabsList>

          <TabsContent value="interventions">
            <InterventionsTab
              interventions={interventions}
              technicians={technicians}
              selectedTechnician={selectedTechnician}
              selectedIntervention={selectedIntervention}
              setSelectedTechnician={setSelectedTechnician}
              setSelectedIntervention={setSelectedIntervention}
              fetchInterventions={fetchInterventions}
              assignTechnician={assignTechnician}
            />
          </TabsContent>

          <TabsContent value="ordres">
            <WorkOrdersTab workOrders={workOrders} />
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
        </Tabs>
      </div>
    </div>
  );
};

export default CheftechDashboard;
