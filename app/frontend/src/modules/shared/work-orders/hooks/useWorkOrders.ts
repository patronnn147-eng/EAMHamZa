import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { toDateInputValue } from '@/lib/date';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine, OrdreTravail } from '@/lib/types';

export const useWorkOrders = () => {
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredWorkOrders, setFilteredWorkOrders] = useState<OrdreTravail[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingWorkOrder, setEditingWorkOrder] = useState<OrdreTravail | null>(null);
  const [deletingWorkOrder, setDeletingWorkOrder] = useState<OrdreTravail | null>(null);
  const { toast } = useToast();
  const { notifyChange, subscribe } = useDataSync();

  const [formData, setFormData] = useState({
    machine_id: '',
    utilisateur_id: '',
    date_echeance: '',
    priorite: 'MOYENNE',
    statut: 'EN_ATTENTE',
  });

  const fetchData = async () => {
    try {
      const [workOrdersResponse, machinesResponse] = await Promise.all([
        client.entities.ordres_travail.query({
          query: {},
          sort: '-created_at',
          limit: 100,
        }),
        client.entities.machines.query({
          query: {},
          limit: 100,
        }),
      ]);

      const workOrdersList = workOrdersResponse.data.items || [];
      const machinesList = machinesResponse.data.items || [];

      setWorkOrders(workOrdersList);
      setFilteredWorkOrders(workOrdersList);
      setMachines(machinesList);
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
      if (event.type === 'work_order') {
        fetchData();
      }
    });
    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    let filtered = workOrders;

    if (searchTerm) {
      filtered = filtered.filter((wo) => wo.id.toString().includes(searchTerm));
    }

    if (statusFilter !== 'ALL') {
      filtered = filtered.filter((wo) => wo.statut === statusFilter);
    }

    if (priorityFilter !== 'ALL') {
      filtered = filtered.filter((wo) => wo.priorite === priorityFilter);
    }

    setFilteredWorkOrders(filtered);
  }, [searchTerm, statusFilter, priorityFilter, workOrders]);

  const handleOpenDialog = (workOrder?: OrdreTravail) => {
    if (workOrder) {
      setEditingWorkOrder(workOrder);
      setFormData({
        machine_id: workOrder.machine_id.toString(),
        utilisateur_id: workOrder.utilisateur_id?.toString() || '',
        date_echeance: toDateInputValue(workOrder.date_echeance),
        priorite: workOrder.priorite,
        statut: workOrder.statut,
      });
    } else {
      setEditingWorkOrder(null);
      setFormData({
        machine_id: '',
        utilisateur_id: '',
        date_echeance: '',
        priorite: 'MOYENNE',
        statut: 'EN_ATTENTE',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const submitData = {
        machine_id: parseInt(formData.machine_id),
        utilisateur_id: formData.utilisateur_id ? parseInt(formData.utilisateur_id) : null,
        date_echeance: formData.date_echeance,
        priorite: formData.priorite,
        statut: formData.statut,
      };

      if (editingWorkOrder) {
        await client.entities.ordres_travail.update({
          id: editingWorkOrder.id.toString(),
          data: submitData,
        });
        notifyChange({
          type: 'work_order',
          action: 'update',
          id: editingWorkOrder.id,
        });
        toast({
          title: 'Success',
          description: 'Work order updated successfully',
        });
      } else {
        const response = await client.entities.ordres_travail.create({
          data: submitData,
        });
        notifyChange({
          type: 'work_order',
          action: 'create',
          id: response.data.id,
        });
        toast({
          title: 'Success',
          description: 'Work order created successfully',
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
        description: detail || 'Failed to save work order',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingWorkOrder) return;

    try {
      await client.entities.ordres_travail.delete({ id: deletingWorkOrder.id.toString() });
      notifyChange({
        type: 'work_order',
        action: 'delete',
        id: deletingWorkOrder.id,
      });
      toast({
        title: 'Success',
        description: 'Work order deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingWorkOrder(null);
      fetchData();
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;

      toast({
        title: 'Error',
        description: detail || 'Failed to delete work order',
        variant: 'destructive',
      });
    }
  };

  return {
    workOrders,
    machines,
    filteredWorkOrders,
    loading,
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingWorkOrder,
    deletingWorkOrder,
    setDeletingWorkOrder,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
  };
};
