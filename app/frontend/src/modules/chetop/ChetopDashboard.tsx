import React from 'react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus } from 'lucide-react';
import {
  CreateItvRequestModal,
  DashboardStatsCards,
  MachinesTab,
  InterventionRequestsTab,
} from './dashboard/components';
import { useChetopDashboardData } from './dashboard/hooks';
import ChefOpWorkOrders from './ChefOpWorkOrders';

const ChetopDashboard: React.FC = () => {
  const {
    stats,
    interventionRequests,
    machines,
    loading,
    showCreateModal,
    setShowCreateModal,
    refreshData
  } = useChetopDashboardData();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg animate-pulse font-bold text-blue-400 italic">Chargement du tableau de bord...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent p-8 animate-premium-fade-in font-sans">
      <div className="max-w-[1600px] mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-6">
          <div>
            <h1 className="text-4xl font-black text-white dark:text-white tracking-tight leading-none mb-3">
              Ops Dashboard
            </h1>
            <p className="text-blue-300 font-medium text-lg border-l-4 border-violet-500 pl-4 py-1">
              Gestion des demandes et suivi des opérations
            </p>
          </div>
          <Button 
            onClick={() => setShowCreateModal(true)} 
            className="flex items-center gap-2 bg-gradient-premium hover:opacity-90 transition-all duration-300 shadow-lg px-8 py-7 rounded-[1.5rem] font-bold text-white border-none scale-100 hover:scale-[1.02] active:scale-95 shadow-violet-500/20"
          >
            <Plus className="h-6 w-6" />
            Nouvelle Demande
          </Button>
        </div>

        {stats && <DashboardStatsCards stats={stats} />}

        <Tabs defaultValue="requests" className="space-y-6">
          <TabsList className="bg-white/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/20 shadow-sm inline-flex">
            <TabsTrigger 
              value="requests" 
              className="px-8 py-3 rounded-xl data-[state=active]:bg-violet-500 data-[state=active]:text-white data-[state=active]:shadow-lg font-bold transition-all"
            >
              Demandes d'Intervention
            </TabsTrigger>
            <TabsTrigger 
              value="work-orders" 
              className="px-8 py-3 rounded-xl data-[state=active]:bg-violet-500 data-[state=active]:text-white data-[state=active]:shadow-lg font-bold transition-all"
            >
              Ordres de Travail
            </TabsTrigger>
            <TabsTrigger 
              value="machines" 
              className="px-8 py-3 rounded-xl data-[state=active]:bg-violet-500 data-[state=active]:text-white data-[state=active]:shadow-lg font-bold transition-all"
            >
              Parc Machines
            </TabsTrigger>
          </TabsList>

          <TabsContent value="requests" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <InterventionRequestsTab requests={interventionRequests} />
          </TabsContent>

          <TabsContent value="work-orders" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <ChefOpWorkOrders />
          </TabsContent>

          <TabsContent value="machines" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <MachinesTab machines={machines} />
          </TabsContent>
        </Tabs>

        <CreateItvRequestModal
          open={showCreateModal}
          onOpenChange={(open) => setShowCreateModal(open)}
          onSuccess={() => {
            setShowCreateModal(false);
            refreshData();
          }}
        />
      </div>
    </div>
  );
};

export default ChetopDashboard;
