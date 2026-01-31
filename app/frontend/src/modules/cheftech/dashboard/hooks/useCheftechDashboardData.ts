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

export const useCheftechDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTechnician, setSelectedTechnician] = useState<number | null>(null);
  const [selectedIntervention, setSelectedIntervention] = useState<number | null>(null);

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

  const fetchInterventions = async (filters?: {
    statut?: string;
    priorite?: string;
    technicien_id?: number;
  }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.priorite) params.append('priorite', filters.priorite);
      if (filters?.technicien_id) {
        params.append('technicien_id', filters.technicien_id.toString());
      }

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
      setInterventions(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les interventions',
        variant: 'destructive',
      });
    }
  };

  const fetchWorkOrders = async (filters?: { statut?: string; priorite?: string }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.priorite) params.append('priorite', filters.priorite);

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
      setWorkOrders(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les ordres de travail',
        variant: 'destructive',
      });
    }
  };

  const fetchTechnicians = async (disponible?: boolean) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (disponible !== undefined) params.append('disponible', disponible.toString());

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
      setTechnicians(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les techniciens',
        variant: 'destructive',
      });
    }
  };

  const fetchMachines = async (filters?: { statut?: string; maintenance_required?: boolean }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.maintenance_required !== undefined) {
        params.append('maintenance_required', filters.maintenance_required.toString());
      }

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
      setMachines(data);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les machines',
        variant: 'destructive',
      });
    }
  };

  const assignTechnician = async (interventionId: number, technicianId: number) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/interventions/${interventionId}/assign`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ technicien_id: technicianId }),
        },
      );

      if (!response.ok) throw new Error("Erreur lors de l'assignation");

      toast({
        title: 'Succès',
        description: 'Technicien assigné avec succès',
      });

      fetchInterventions();
      fetchTechnicians();
    } catch {
      toast({
        title: 'Erreur',
        description: "Impossible d'assigner le technicien",
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
    fetchWorkOrders,
    fetchTechnicians,
    fetchMachines,
    assignTechnician,
    updateMachineStatus,
  };
};
