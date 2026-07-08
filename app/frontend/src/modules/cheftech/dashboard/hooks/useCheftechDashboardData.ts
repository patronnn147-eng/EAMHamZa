import { useEffect, useState } from 'react';
import { toast } from '@/hooks/use-toast';
import type {
  DashboardStats,
  Intervention,
  Machine,
  Technician,
  WorkOrder,
} from '../types';

const getAuthToken = () => localStorage.getItem('access_token');

export interface DistributionSlice {
  name: string;
  value: number;
}

export interface InterventionDistributions {
  by_status: DistributionSlice[];
  by_type: DistributionSlice[];
  by_root_cause: DistributionSlice[];
  by_machine_category: DistributionSlice[];
}

export const useCheftechDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [distributions, setDistributions] = useState<InterventionDistributions | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);

  // Pagination states
  const [interventionsPage, setInterventionsPage] = useState(1);
  const [interventionsTotalPages, setInterventionsTotalPages] = useState(1);
  const [workOrdersPage, setWorkOrdersPage] = useState(1);
  const [workOrdersTotalPages, setWorkOrdersTotalPages] = useState(1);
  const [techniciansPage, setTechniciansPage] = useState(1);
  const [techniciansTotalPages, setTechniciansTotalPages] = useState(1);
  const [machinesPage, setMachinesPage] = useState(1);
  const [machinesTotalPages, setMachinesTotalPages] = useState(1);
  const [pageSize] = useState(100);

  const fetchDashboardData = async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        throw new Error('Token non trouvé');
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/dashboard`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error('Erreur lors du chargement des statistiques');
      }

      const data = await response.json();
      setStats(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les statistiques',
        variant: 'destructive',
      });
    }
  };

  const fetchDistributions = async () => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/dashboard/distributions`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) throw new Error('Erreur lors du chargement des répartitions');
      const data = await response.json();
      setDistributions(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les répartitions',
        variant: 'destructive',
      });
    }
  };

  const approveIntervention = async (interventionId: number) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_intervention/${interventionId}/validate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'APPROVE'
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Erreur lors de l'approbation");
      }

      toast({ title: 'Succès', description: 'Intervention approuvée et assignée' });
      fetchInterventions();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : "Impossible d'approuver",
        variant: 'destructive',
      });
    }
  };

  const rejectIntervention = async (interventionId: number, reason?: string) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_intervention/${interventionId}/validate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'REJECT',
            rejection_reason: reason || null
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Erreur lors du rejet');
      }

      toast({ title: 'Succès', description: 'Intervention rejetée' });
      fetchInterventions();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Impossible de rejeter',
        variant: 'destructive',
      });
    }
  };

  const validateWorkOrder = async (ordreId: number, technicianId: number) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_travail/${ordreId}/validate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'APPROVE',
            utilisateur_id: technicianId
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Erreur lors de la validation");
      }

      toast({ title: 'Succès', description: 'Ordre de travail validé et assigné' });
      fetchWorkOrders();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : "Impossible de valider",
        variant: 'destructive',
      });
    }
  };

  const rejectWorkOrder = async (ordreId: number, reason?: string) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_travail/${ordreId}/validate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'REJECT',
            reason: reason || null
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Erreur lors du rejet');
      }

      toast({ title: 'Succès', description: 'Ordre de travail rejeté' });
      fetchWorkOrders();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Impossible de rejeter',
        variant: 'destructive',
      });
    }
  };

  const assignWorkOrder = async (
    ordreId: number,
    technicienIds: number[],
    machineIds: number[],
    estimatedCompletionDate?: string,
  ) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/ordres-travail/${ordreId}/assign`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            technicien_ids: technicienIds,
            machine_ids: machineIds,
            estimated_completion_date: estimatedCompletionDate ? new Date(estimatedCompletionDate).toISOString() : null,
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Erreur lors de l'assignation");
      }

      toast({
        title: 'Succès',
        description: 'Ordre de travail assigné',
      });

      fetchWorkOrders();
      fetchInterventions();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : "Impossible d'assigner l'ordre",
        variant: 'destructive',
      });
    }
  };

  const fetchInterventions = async (filters?: {
    statut?: string;
    page?: number;
    size?: number;
  }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const pageNum = filters?.page || interventionsPage;
      const sizeNum = filters?.size || pageSize;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      params.append('page', pageNum.toString());
      params.append('size', sizeNum.toString());

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/interventions?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) throw new Error('Erreur lors du chargement des interventions');
      const data = await response.json();
      setInterventions(data.items || []);
      setInterventionsTotalPages(data.total_pages || 1);
      setInterventionsPage(pageNum);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les interventions',
        variant: 'destructive',
      });
    }
  };

  const fetchWorkOrders = async (filters?: { statut?: string; priorite?: string; page?: number; size?: number }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const pageNum = filters?.page || workOrdersPage;
      const sizeNum = filters?.size || pageSize;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.priorite) params.append('priorite', filters.priorite);
      params.append('page', pageNum.toString());
      params.append('size', sizeNum.toString());

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/ordres-travail?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) throw new Error('Erreur lors du chargement des ordres de travail');
      const data = await response.json();
      setWorkOrders(data.items || []);
      setWorkOrdersTotalPages(data.total_pages || 1);
      setWorkOrdersPage(pageNum);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les ordres de travail',
        variant: 'destructive',
      });
    }
  };

  const fetchTechnicians = async (filters?: { disponible?: boolean; page?: number; size?: number }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const pageNum = filters?.page || techniciansPage;
      const sizeNum = filters?.size || pageSize;

      const params = new URLSearchParams();
      if (filters?.disponible !== undefined) params.append('disponible', filters.disponible.toString());
      params.append('page', pageNum.toString());
      params.append('size', sizeNum.toString());

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/techniciens?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) throw new Error('Erreur lors du chargement des techniciens');
      const data = await response.json();
      setTechnicians(data.items || []);
      setTechniciansTotalPages(data.total_pages || 1);
      setTechniciansPage(pageNum);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les techniciens',
        variant: 'destructive',
      });
    }
  };

  const fetchMachines = async (filters?: { statut?: string; maintenance_required?: boolean; page?: number; size?: number }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const pageNum = filters?.page || machinesPage;
      const sizeNum = filters?.size || pageSize;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.maintenance_required !== undefined) {
        params.append('maintenance_required', filters.maintenance_required.toString());
      }
      params.append('page', pageNum.toString());
      params.append('size', sizeNum.toString());

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/machines?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) throw new Error('Erreur lors du chargement des machines');
      const data = await response.json();
      if (data?.items) {
          setMachines(data.items);
          setMachinesTotalPages(data.total_pages || 1);
          setMachinesPage(pageNum);
          return;
      }

      const fallback = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/machines?query=${encodeURIComponent(
          JSON.stringify({}),
        )}&limit=2000`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!fallback.ok) {
        setMachines([]);
        return;
      }

      const fallbackData = (await fallback.json()) as { items?: Machine[] };
      setMachines(fallbackData.items || []);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les machines',
        variant: 'destructive',
      });
    }
  };


  const updateMachineStatus = async (machineId: number, status: string) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/machines/${machineId}/status`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ statut: status }),
        },
      );

      if (!response.ok) throw new Error('Erreur lors de la mise à jour');

      toast({
        title: 'Succès',
        description: 'Statut de la machine mis à jour',
      });

      fetchMachines();
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de mettre à jour le statut',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchDashboardData(),
        fetchDistributions(),
        fetchInterventions(),
        fetchWorkOrders(),
        fetchTechnicians(),
        fetchMachines(),
      ]);
      setLoading(false);
    };

    loadData();
  }, []);

  return {
    stats,
    distributions,
    interventions,
    workOrders,
    technicians,
    machines,
    loading,
    fetchInterventions,
    fetchWorkOrders,
    fetchTechnicians,
    fetchMachines,
    assignWorkOrder,
    updateMachineStatus,
    approveIntervention,
    rejectIntervention,
    validateWorkOrder,
    rejectWorkOrder,
    // Pagination data
    interventionsPage,
    interventionsTotalPages,
    setInterventionsPage,
    workOrdersPage,
    workOrdersTotalPages,
    setWorkOrdersPage,
    techniciansPage,
    techniciansTotalPages,
    setTechniciansPage,
    machinesPage,
    machinesTotalPages,
    setMachinesPage,
  };
};
