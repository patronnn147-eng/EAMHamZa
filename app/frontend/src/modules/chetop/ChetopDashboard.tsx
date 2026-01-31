import React from 'react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus } from 'lucide-react';
import {
  CreateOrderModal,
  DashboardStatsCards,
  MachinesTab,
  WorkOrdersTab,
} from './dashboard/components';
import { useChetopDashboardData } from './dashboard/hooks';

const ChetopDashboard: React.FC = () => {
  const {
    stats,
    workOrders,
    machines,
    loading,
    showCreateModal,
    setShowCreateModal,
    setSelectedOrder,
    formData,
    setFormData,
    handleCreateOrder,
  } = useChetopDashboardData();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Tableau de Bord - Chef des Opérations</h1>
          <Button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Nouvel Ordre de Travail
          </Button>
        </div>

        {stats && <DashboardStatsCards stats={stats} />}

        <Tabs defaultValue="ordres" className="space-y-6">
          <TabsList>
            <TabsTrigger value="ordres">Ordres de Travail</TabsTrigger>
            <TabsTrigger value="machines">Machines</TabsTrigger>
          </TabsList>

          <TabsContent value="ordres">
            <WorkOrdersTab workOrders={workOrders} onSelectOrder={setSelectedOrder} />
          </TabsContent>

          <TabsContent value="machines">
            <MachinesTab machines={machines} />
          </TabsContent>
        </Tabs>

        <CreateOrderModal
          open={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          formData={formData}
          setFormData={setFormData}
          machines={machines}
          onSubmit={handleCreateOrder}
        />
      </div>
    </div>
  );
};

export default ChetopDashboard;
