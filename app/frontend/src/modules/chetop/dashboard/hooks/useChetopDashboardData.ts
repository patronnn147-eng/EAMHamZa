import { useEffect, useState } from 'react';
import type { DashboardStats, Machine, InterventionRequest } from '../types';

export const useChetopDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [interventionRequests, setInterventionRequests] = useState<InterventionRequest[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) throw new Error('No authentication token');

      // Fetch Stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (statsResponse.ok) {
        setStats(await statsResponse.json());
      }

      // Fetch Intervention Requests (Recent 5)
      const itvResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/intervention-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (itvResponse.ok) {
        const data = await itvResponse.json();
        setInterventionRequests(data.slice(0, 5));
      }

      // Fetch Machines
      const machinesResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/machines`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (machinesResponse.ok) {
        setMachines(await machinesResponse.json());
      }

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return {
    stats,
    interventionRequests,
    machines,
    loading,
    showCreateModal,
    setShowCreateModal,
    refreshData: fetchDashboardData
  };
};
