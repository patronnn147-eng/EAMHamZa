import { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

export interface ForecastItem {
  piece_id: number;
  piece_name: string;
  current_qty: number;
  min_stock: number;
  urgency_score: number;
  urgency_label: 'URGENT' | 'SOON' | 'MONITOR';
  projected_demand: number;
  reorder_qty_suggested: number;
  days_until_stockout: number | null;
  consumption_data: 'real' | 'estimated';
  machines_affected: { id: number; name: string; rul_days: number }[];
}

export interface ForecastResponse {
  generated_at: string;
  horizon_days: number;
  total_urgent: number;
  total_monitor: number;
  items: ForecastItem[];
}

interface UseInventoryForecastReturn {
  data: ForecastResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  refresh: () => Promise<void>;
}

export function useInventoryForecast(horizonDays = 60, limit = 20): UseInventoryForecastReturn {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(
        `${API_BASE}/api/v1/ml/inventory/demand-forecast?horizon_days=${horizonDays}&limit=${limit}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError('Impossible de charger les prévisions de réapprovisionnement.');
    } finally {
      setLoading(false);
    }
  }, [horizonDays, limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refresh = async () => {
    const token = getToken();
    await fetch(`${API_BASE}/api/v1/ml/inventory/demand-forecast/refresh`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    fetchData();
  };

  return { data, loading, error, refetch: fetchData, refresh };
}
