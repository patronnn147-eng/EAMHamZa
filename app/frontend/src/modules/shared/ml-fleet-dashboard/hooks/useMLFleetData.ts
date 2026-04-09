import { useState, useEffect, useCallback } from 'react';
import type { FleetMachineCard, FleetDashboardResponse, FleetCriticalResponse } from '@/lib/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const getToken = () => localStorage.getItem('access_token');

interface UseMLFleetDataReturn {
  machines: FleetMachineCard[];
  criticalMachines: FleetMachineCard[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
  summary: {
    totalMachines: number;
    criticalCount: number;
    highRiskCount: number;
    avgHealthScore: number;
    avgReliabilityScore: number;
  };
}

export function useMLFleetData(): UseMLFleetDataReturn {
  const [machines, setMachines] = useState<FleetMachineCard[]>([]);
  const [criticalMachines, setCriticalMachines] = useState<FleetMachineCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState({
    totalMachines: 0,
    criticalCount: 0,
    highRiskCount: 0,
    avgHealthScore: 0,
    avgReliabilityScore: 0,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Fetch fleet dashboard data
      const dashboardRes = await fetch(`${API_BASE}/api/v1/ml/fleet/dashboard`, { headers });
      if (dashboardRes.ok) {
        const dashboardData = await dashboardRes.json();
        // Backend returns array or { machines: [] }
        const machineList = Array.isArray(dashboardData) ? dashboardData : (dashboardData.machines || []);
        setMachines(machineList);
        setSummary({
          totalMachines: machineList.length,
          criticalCount: machineList.filter((m: FleetMachineCard) => m.risk_level === 'CRITICAL').length,
          highRiskCount: machineList.filter((m: FleetMachineCard) => m.risk_level === 'HIGH').length,
          avgHealthScore: machineList.length > 0 
            ? machineList.reduce((sum: number, m: FleetMachineCard) => sum + (m.health_score || 0), 0) / machineList.length 
            : 0,
          avgReliabilityScore: machineList.length > 0 
            ? machineList.reduce((sum: number, m: FleetMachineCard) => sum + (m.reliability_score || 0), 0) / machineList.length 
            : 0,
        });
      }

      // Fetch critical machines
      const criticalRes = await fetch(`${API_BASE}/api/v1/ml/fleet/critical`, { headers });
      if (criticalRes.ok) {
        const criticalData: FleetCriticalResponse = await criticalRes.json();
        setCriticalMachines(criticalData.machines || []);
      }
    } catch (err) {
      console.error('Failed to fetch ML fleet data:', err);
      setError('Impossible de charger les données ML. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { machines, criticalMachines, loading, error, refetch: fetchData, summary };
}
