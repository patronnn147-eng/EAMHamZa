/**
 * Inventory consumption-workflow hooks.
 *
 * Thin fetch wrappers — no React Query (project already uses bare fetch
 * pattern elsewhere). Each hook returns { data, loading, error, refresh }.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

const apiBase = import.meta.env.VITE_API_BASE_URL || '';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

// ─── Types ───────────────────────────────────────────────────────────────

export interface PickerPiece {
  id: number;
  reference: string;
  name: string;
  category: string | null;
  unit_price: number | null;
  min_stock: number | null;
  is_consumable: boolean;
  default_unit: string;
  stock_quantity: string | number;
  reserved_quantity?: string | number;
  available_quantity: string | number;
}

export interface MachinePiecesResponse {
  compatible: PickerPiece[];
  consumables: PickerPiece[];
  other: PickerPiece[];
}

export interface Availability {
  piece_id: number;
  stock_quantity: string;
  reserved_quantity: string;
  available_quantity: string;
}

export interface PieceSuggestion {
  piece_id: number;
  name: string;
  reference: string;
  category: string | null;
  similarity: number;
  tier: 'high' | 'medium' | 'low';
  machine_match: boolean;
}

export interface PendingPiece {
  id: number;
  intervention_id: number | null;
  submitted_by: number | null;
  submitted_by_name: string | null;
  name: string;
  category: string | null;
  quantity: string;
  unit: string;
  photo_object_key: string | null;
  notes: string | null;
  status: 'PENDING_REVIEW' | 'MATCHED' | 'CREATED' | 'REJECTED';
  matched_piece_id: number | null;
  matched_piece_name: string | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}

export interface RequiredPiece {
  id: number;
  intervention_id: number;
  piece_id: number;
  piece_name: string;
  piece_reference: string;
  quantity_planned: string;
  unit: string;
  quantity_reserved: string;
  reservation_expires_at: string | null;
  approved: boolean | null;
  created_at: string;
  available_quantity?: string | null;
}

export interface ConsumedPiece {
  id: number;
  required_piece_id: number;
  piece_id: number;
  piece_name: string;
  piece_reference: string;
  quantity_used: string;
  quantity_returned: string;
  quantity_wasted: string;
  unit: string;
  disposition: 'used' | 'partial' | 'not_used' | 'wasted' | 'returned';
  notes: string | null;
  created_at: string;
}

export interface InterventionPartsDetail {
  intervention_id: number;
  parts_approved: boolean | null;
  required: RequiredPiece[];
  consumed: ConsumedPiece[];
  pending: PendingPiece[];
  parts_replaced_json: unknown;
}

// ─── Hook: pieces by machine (PiecePicker source) ───────────────────────

export function useMachinePieces(machineId: number | null | undefined, search?: string) {
  const [data, setData] = useState<MachinePiecesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!machineId) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      const resp = await fetch(
        `${apiBase}/api/v1/inventory/pieces/by-machine/${machineId}?${params.toString()}`,
        { headers: getAuthHeaders() }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setData(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
    } finally {
      setLoading(false);
    }
  }, [machineId, search]);

  useEffect(() => { void fetchData(); }, [fetchData]);
  return { data, loading, error, refresh: fetchData };
}

// ─── Hook: availability batch (live picker badges) ──────────────────────

export function usePieceAvailability(pieceIds: number[]) {
  const [data, setData] = useState<Record<number, Availability>>({});
  const [loading, setLoading] = useState(false);
  const idsRef = useRef<string>('');

  const fetchData = useCallback(async () => {
    if (pieceIds.length === 0) {
      setData({});
      return;
    }
    const key = [...pieceIds].sort((a, b) => a - b).join(',');
    if (key === idsRef.current) return;
    idsRef.current = key;

    setLoading(true);
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/inventory/availability?piece_ids=${key}`,
        { headers: getAuthHeaders() }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const rows: Availability[] = await resp.json();
      const map: Record<number, Availability> = {};
      rows.forEach((r) => { map[r.piece_id] = r; });
      setData(map);
    } catch {
      // silent — picker can fall back to stock_quantity
    } finally {
      setLoading(false);
    }
  }, [pieceIds]);

  useEffect(() => { void fetchData(); }, [fetchData]);
  return { data, loading, refresh: fetchData };
}

// ─── Hook: fuzzy suggestion (debounced 300 ms) ──────────────────────────

export function usePieceSuggestions(query: string, machineId?: number | null) {
  const [data, setData] = useState<PieceSuggestion[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setData([]);
      return;
    }
    const handle = globalThis.setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ q: query.trim() });
        if (machineId) params.set('machine_id', String(machineId));
        const resp = await fetch(
          `${apiBase}/api/v1/inventory/pieces/suggest/lookup?${params.toString()}`,
          { headers: getAuthHeaders() }
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const out = await resp.json();
        setData(out.results || []);
      } catch {
        setData([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => globalThis.clearTimeout(handle);
  }, [query, machineId]);

  return { data, loading };
}

// ─── Hook: pending queue (admin review) ─────────────────────────────────

export function usePendingPieces(status: string = 'PENDING_REVIEW') {
  const [data, setData] = useState<PendingPiece[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ status, size: '100' });
      const resp = await fetch(
        `${apiBase}/api/v1/inventory/pending?${params.toString()}`,
        { headers: getAuthHeaders() }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const body = await resp.json();
      setData(body.items || []);
      setTotal(body.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { void fetchData(); }, [fetchData]);

  // Actions
  const matchPending = useCallback(async (pendingId: number, matchedPieceId: number) => {
    const resp = await fetch(
      `${apiBase}/api/v1/inventory/pending/${pendingId}/match`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ matched_piece_id: matchedPieceId }),
      }
    );
    if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'match failed');
    await fetchData();
  }, [fetchData]);

  const rejectPending = useCallback(async (pendingId: number, reason: string) => {
    const resp = await fetch(
      `${apiBase}/api/v1/inventory/pending/${pendingId}/reject`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ rejection_reason: reason }),
      }
    );
    if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'reject failed');
    await fetchData();
  }, [fetchData]);

  const createFromPending = useCallback(async (pendingId: number, payload: Record<string, unknown>) => {
    const resp = await fetch(
      `${apiBase}/api/v1/inventory/pending/${pendingId}/create-piece`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );
    if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'create-piece failed');
    await fetchData();
  }, [fetchData]);

  return { data, total, loading, error, refresh: fetchData, matchPending, rejectPending, createFromPending };
}

// ─── Hook: intervention parts detail (existing intervention view) ───────

export function useInterventionParts(interventionId: number | null | undefined) {
  const [data, setData] = useState<InterventionPartsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!interventionId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/inventory/intervention/${interventionId}/parts`,
        { headers: getAuthHeaders() }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setData(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
    } finally {
      setLoading(false);
    }
  }, [interventionId]);

  useEffect(() => { void fetchData(); }, [fetchData]);
  return { data, loading, error, refresh: fetchData };
}

// ─── Action helpers ──────────────────────────────────────────────────────

export async function attachRequiredPieces(
  interventionId: number,
  items: Array<{ piece_id: number; quantity_planned: number | string; unit?: string }>
): Promise<RequiredPiece[]> {
  const resp = await fetch(
    `${apiBase}/api/v1/inventory/required-pieces/${interventionId}`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(items),
    }
  );
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'attach failed');
  return resp.json();
}

export async function submitPendingPiece(
  payload: { name: string; quantity: number | string; unit?: string; category?: string; notes?: string },
  interventionId?: number
): Promise<PendingPiece> {
  const url = interventionId
    ? `${apiBase}/api/v1/inventory/pending?intervention_id=${interventionId}`
    : `${apiBase}/api/v1/inventory/pending`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'submit failed');
  return resp.json();
}


// ─── Hook: parts detail keyed by work_order_id (completion dialog) ──────

export function useInterventionPartsByWO(workOrderId: number | null | undefined) {
  const [data, setData] = useState<InterventionPartsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!workOrderId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/inventory/intervention/by-wo/${workOrderId}/parts`,
        { headers: getAuthHeaders() }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setData(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
    } finally {
      setLoading(false);
    }
  }, [workOrderId]);

  useEffect(() => { void fetchData(); }, [fetchData]);
  return { data, loading, error, refresh: fetchData };
}
