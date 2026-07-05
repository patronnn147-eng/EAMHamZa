import { useState, useEffect, useRef, useCallback } from 'react';

interface MachineData {
  id: number;
  name: string;
  zone?: string;
  sous_zone?: string;
  statut?: string;
}

interface MLPrediction {
  machine_id: number;
  machine_name: string;
  rul_days: number;
  risk_level: string;
  failure_probability: number;
  predicted_failure_date: string;
  data_points: number;
  predicted_priority?: string;
  is_anomaly?: boolean;
  anomaly_score?: number;
  health_score?: number;
  health_breakdown?: Record<string, number>;
  reliability_score?: number;
  mtbf_pred?: number;
  mttr_pred?: number;
  availability_pred?: number;
  explanations?: Array<{ factor: string; impact: number; intensity: string }>;
  air_temperature?: number;
  process_temperature?: number;
  rotational_speed?: number;
  torque?: number;
  tool_wear?: number;
}

interface UseMachineDetailReturn {
  machine: MachineData | null;
  prediction: MLPrediction | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

// ✅ Cache & in-flight maps
const cache = new Map<number, { machine: MachineData; prediction: MLPrediction }>();
const inFlight = new Map<number, Promise<{ machine: MachineData; prediction: MLPrediction }>>();

async function fetchMachineDetail(
  id: number,
  signal?: AbortSignal
): Promise<{ machine: MachineData; prediction: MLPrediction }> {
  // ✅ Return cached data
  if (cache.has(id)) {
    return cache.get(id);
  }

  // ✅ Prevent duplicate requests
  if (inFlight.has(id)) {
    return inFlight.get(id);
  }

  const controller = new AbortController();
  const finalSignal = signal || controller.signal;

  const timeoutId = setTimeout(() => controller.abort(), 15000);

  const promise = (async () => {
    try {
      const response = await fetch(`/api/v1/ml/machines/${id}/detail`, {
        signal: finalSignal,
        headers: { Accept: 'application/json' },
      });

      clearTimeout(timeoutId);

      if (response.status === 304) {
        throw new Error('Unexpected 304 on first fetch');
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch machine detail: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      const result = {
        machine: data.machine,
        prediction: data.prediction,
      };

      cache.set(id, result);

      return result;
    } catch (err: any) {
      clearTimeout(timeoutId);

      if (err.name === 'AbortError') {
        throw new Error('Request timeout or cancelled');
      }

      throw err;
    } finally {
      inFlight.delete(id);
    }
  })();

  inFlight.set(id, promise);
  return promise;
}

export function useMachineDetail(machineId: number | undefined): UseMachineDetailReturn {
  const [machine, setMachine] = useState<MachineData | null>(null);
  const [prediction, setPrediction] = useState<MLPrediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const loadData = useCallback(async () => {
    if (!machineId) return;

    // ✅ Cancel previous request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    abortRef.current = new AbortController();

    // ✅ Serve cache instantly
    if (cache.has(machineId)) {
      const cached = cache.get(machineId);
      setMachine(cached.machine);
      setPrediction(cached.prediction);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await fetchMachineDetail(machineId, abortRef.current.signal);

      setMachine(result.machine);
      setPrediction(result.prediction);
      setError(null);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to load machine details');
        console.error('useMachineDetail error:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [machineId]);

  useEffect(() => {
    loadData();

    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [loadData]);

  return {
    machine,
    prediction,
    loading,
    error,
    refetch: loadData,
  };
}