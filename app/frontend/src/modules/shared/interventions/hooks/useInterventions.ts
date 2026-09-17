import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';
import { toDateInputValue } from '@/lib/date';
import type { Intervention, OrdreTravail } from '@/lib/types';

export const useInterventions = () => {
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [filteredInterventions, setFilteredInterventions] = useState<Intervention[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingIntervention, setEditingIntervention] = useState<Intervention | null>(null);
  const [deletingIntervention, setDeletingIntervention] = useState<Intervention | null>(null);
  const { toast } = useToast();
  const { notifyChange, subscribe } = useDataSync();

  const [formData, setFormData] = useState({
    date_intervention: '',
    rapport: '',
    ordre_travail_id: '',
  });

  const fetchData = async () => {
    try {
      const [interventionsResponse, workOrdersResponse] = await Promise.all([
        client.entities.ordres_intervention.query({
          query: {},
          sort: '-date_intervention',
          limit: 100,
        }),
        client.entities.ordres_travail.query({
          query: {},
          limit: 100,
        }),
      ]);

      const interventionsList = interventionsResponse.data.items || [];
      const workOrdersList = workOrdersResponse.data.items || [];

      setInterventions(interventionsList);
      setFilteredInterventions(interventionsList);
      setWorkOrders(workOrdersList);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (event.type === 'intervention') {
        fetchData();
      }
    });
    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = interventions.filter(
        (i) =>
          i.rapport.toLowerCase().includes(searchTerm.toLowerCase()) ||
          i.id.toString().includes(searchTerm),
      );
      setFilteredInterventions(filtered);
    } else {
      setFilteredInterventions(interventions);
    }
  }, [searchTerm, interventions]);

  const handleOpenDialog = (intervention?: Intervention) => {
    if (intervention) {
      setEditingIntervention(intervention);
      setFormData({
        date_intervention: toDateInputValue(intervention.date_intervention),
        rapport: intervention.rapport,
        ordre_travail_id: intervention.ordre_travail_id.toString(),
      });
    } else {
      setEditingIntervention(null);
      setFormData({
        date_intervention: new Date().toISOString().split('T')[0],
        rapport: '',
        ordre_travail_id: '',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (!formData.ordre_travail_id || !formData.date_intervention || !formData.rapport.trim()) {
        toast({
          title: 'Validation Error',
          description: 'Please fill in all required fields',
          variant: 'destructive',
        });
        return;
      }

      const submitData = {
        date_intervention: formData.date_intervention,
        rapport: formData.rapport,
        ordre_travail_id: parseInt(formData.ordre_travail_id),
      };

      if (editingIntervention) {
        await client.entities.ordres_intervention.update({
          id: editingIntervention.id.toString(),
          data: submitData,
        });
        notifyChange({
          type: 'intervention',
          action: 'update',
          id: editingIntervention.id,
        });
        toast({
          title: 'Success',
          description: 'Intervention updated successfully',
        });
      } else {
        const response = await client.entities.ordres_intervention.create({
          data: submitData,
        });
        notifyChange({
          type: 'intervention',
          action: 'create',
          id: response.data.id,
        });
        toast({
          title: 'Success',
          description: 'Intervention recorded successfully',
        });
      }

      setDialogOpen(false);
      fetchData();
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;

      toast({
        title: 'Error',
        description: detail || 'Failed to save intervention',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingIntervention) return;

    try {
      await client.entities.ordres_intervention.delete({ id: deletingIntervention.id.toString() });
      notifyChange({
        type: 'intervention',
        action: 'delete',
        id: deletingIntervention.id,
      });
      toast({
        title: 'Success',
        description: 'Intervention deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingIntervention(null);
      fetchData();
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;

      toast({
        title: 'Error',
        description: detail || 'Failed to delete intervention',
        variant: 'destructive',
      });
    }
  };

  return {
    workOrders,
    filteredInterventions,
    searchTerm,
    setSearchTerm,
    loading,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingIntervention,
    deletingIntervention,
    setDeletingIntervention,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
  };
};
