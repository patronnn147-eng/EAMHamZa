import { useState, useEffect, useCallback } from 'react';
import { toast } from '@/hooks/use-toast';

const getAuthToken = () => localStorage.getItem('access_token');

export interface PendingAdminWorkOrder {
  id: number;
  titre: string;
  description: string;
  priorite: string;
  statut: string;
  machine_id: number;
  machine_nom?: string;
  created_by_role: 'ADMIN' | 'CHEFTECH' | 'CHETOP' | 'TECHNICIEN';
  created_at: string;
  utilisateur_nom?: string;
}

/**
 * Hook for Admin to validate CHETOP-created work orders
 * Phase 3: CHETOP Work Requires Admin Validation
 */
export const useAdminWorkOrderValidation = () => {
  const [pendingWorkOrders, setPendingWorkOrders] = useState<PendingAdminWorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [validatingId, setValidatingId] = useState<number | null>(null);

  const fetchPendingAdminValidation = useCallback(async () => {
    try {
      setLoading(true);
      const token = getAuthToken();
      if (!token) {
        throw new Error('Token non trouvé');
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/admin/work-orders/pending-admin-validation`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        // If endpoint doesn't exist yet, return empty array (graceful degradation)
        if (response.status === 404) {
          setPendingWorkOrders([]);
          return;
        }
        throw new Error('Erreur lors du chargement');
      }

      const data = await response.json();
      setPendingWorkOrders(data.items || []);
    } catch (error) {
      console.error('Error fetching pending admin validation:', error);
      // Don't show error toast - might be endpoint not implemented yet
      setPendingWorkOrders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const validateByAdmin = useCallback(async (workOrderId: number) => {
    try {
      setValidatingId(workOrderId);
      const token = getAuthToken();
      if (!token) {
        throw new Error('Token non trouvé');
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/admin/work-orders/${workOrderId}/validate-by-admin`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Erreur lors de la validation");
      }

      toast({
        title: 'Succès',
        description: `Ordre de travail #${workOrderId} validé par ADMIN`,
      });

      // Refresh the list
      fetchPendingAdminValidation();
    } catch (error) {
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Impossible de valider',
        variant: 'destructive',
      });
    } finally {
      setValidatingId(null);
    }
  }, [fetchPendingAdminValidation]);

  const rejectByAdmin = useCallback(async (workOrderId: number, reason?: string) => {
    try {
      setValidatingId(workOrderId);
      const token = getAuthToken();
      if (!token) {
        throw new Error('Token non trouvé');
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/admin/work-orders/${workOrderId}/reject-by-admin`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            reason: reason || null,
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Erreur lors du rejet");
      }

      toast({
        title: 'Succès',
        description: `Ordre de travail #${workOrderId} rejeté par ADMIN`,
      });

      // Refresh the list
      fetchPendingAdminValidation();
    } catch (error) {
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Impossible de rejeter',
        variant: 'destructive',
      });
    } finally {
      setValidatingId(null);
    }
  }, [fetchPendingAdminValidation]);

  useEffect(() => {
    fetchPendingAdminValidation();
  }, [fetchPendingAdminValidation]);

  return {
    pendingWorkOrders,
    loading,
    validatingId,
    validateByAdmin,
    rejectByAdmin,
    refetch: fetchPendingAdminValidation,
  };
};