import React from 'react';
import { useMLFleetData } from './ml-fleet-dashboard/hooks/useMLFleetData';
import { FleetOverview } from './ml-fleet-dashboard/components/FleetOverview';
import { DemandForecastPanel } from './ml-fleet-dashboard/components/DemandForecastPanel';
import { Button } from '@/components/ui/button';
import { BrainCircuit, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function MLFleetDashboard() {
  const { machines, loading, error, refetch, summary } = useMLFleetData();
  const { toast } = useToast();

  const handleRefresh = () => {
    refetch();
    toast({
      title: 'Actualisation',
      description: 'Chargement des données ML en cours...',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-3" />
          <p className="text-sm text-blue-300">Chargement des données ML...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <BrainCircuit className="h-16 w-16 mx-auto mb-4 text-gray-300" />
        <p className="text-blue-300 text-lg mb-4">{error}</p>
        <Button onClick={handleRefresh} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Réessayer
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <BrainCircuit className="h-7 w-7 text-blue-600" />
            Tableau de Bord IA — Flotte
          </h1>
          <p className="text-sm text-blue-300 mt-1">
            Surveillance prédictive et analyse de santé pour l'ensemble de la flotte de machines
          </p>
        </div>
        <Button onClick={handleRefresh} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualiser
        </Button>
      </div>

      {/* Fleet Overview */}
      <FleetOverview machines={machines} summary={summary} />

      {/* Demand Forecast — Inventory x ML cross-signal */}
      <div className="mt-8 border-t border-blue-900/40 pt-6">
        <DemandForecastPanel />
      </div>
    </div>
  );
}
