import { useEffect, useMemo, useState } from 'react';
import { client } from '@/lib/api';
import { toDateInputValue } from '@/lib/date';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine, OrdreTravail } from '@/lib/types';

type UseWorkOrdersOptions = {
  attachments: File[];
  clearAttachments: () => void;
  userRole?: string;
};

export const useWorkOrders = (options: UseWorkOrdersOptions) => {
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

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const isChetop = useMemo(() => options.userRole === 'CHETOP', [options.userRole]);

  const [formData, setFormData] = useState({
    titre: '',
    description: '',
    machine_ids: [] as number[],
    planning_id: null as number | null,
    chef_technique_id: null as number | null,
    technicien_ids: [] as number[],
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
          limit: 2000,
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
    const openForEdit = async () => {
      if (!workOrder) return;

      setEditingWorkOrder(workOrder);

      let planningId: number | null = null;
      try {
        const relResp = await client.entities.planning_ordres_travail.queryAll({
          query: { ordre_travail_id: workOrder.id },
          limit: 1,
        });
        const rel = relResp.data.items?.[0];
        planningId = rel?.planning_id ?? null;
      } catch {
        planningId = null;
      }

      let technicienIds: number[] = [];
      try {
        const interResp = await client.entities.ordres_intervention.queryAll({
          query: { ordre_travail_id: workOrder.id },
          limit: 2000,
        });
        technicienIds = (interResp.data.items || [])
          .map((i: { technicien_id?: number | null }) => i.technicien_id)
          .filter((id: number | null | undefined): id is number => typeof id === 'number');
      } catch {
        technicienIds = [];
      }

      setFormData({
        titre: workOrder.titre || '',
        description: workOrder.description || '',
        machine_ids: [workOrder.machine_id],
        planning_id: planningId,
        chef_technique_id: workOrder.utilisateur_id || null,
        technicien_ids: technicienIds,
        date_echeance: toDateInputValue(workOrder.date_echeance),
        priorite: workOrder.priorite,
        statut: workOrder.statut,
      });
    };

    if (workOrder) {
      void openForEdit();
    } else {
      setEditingWorkOrder(null);
      setFormData({
        titre: '',
        description: '',
        machine_ids: [],
        planning_id: null,
        chef_technique_id: null,
        technicien_ids: [],
        date_echeance: '',
        priorite: 'MOYENNE',
        statut: 'EN_ATTENTE',
      });
    }

    options.clearAttachments();
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingWorkOrder) {
        const submitData = {
          titre: formData.titre,
          description: formData.description,
          machine_id: formData.machine_ids[0],
          utilisateur_id: formData.chef_technique_id,
          date_echeance: formData.date_echeance,
          priorite: formData.priorite,
          statut: formData.statut,
        };

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
        if (!formData.titre || !formData.description || formData.machine_ids.length === 0) {
          toast({
            title: 'Error',
            description: 'Please fill title, description, and select at least one machine',
            variant: 'destructive',
          });
          return;
        }

        const createdIds: number[] = [];

        if (isChetop) {

          const token = localStorage.getItem('access_token');
          if (!token) throw new Error('No authentication token');

          if (!formData.planning_id) {
            toast({
              title: 'Error',
              description: 'Please select a planning so related users can be notified',
              variant: 'destructive',
            });
            return;
          }


             if (!token) throw new Error('No authentication token');

          const relatedUserIds = Array.from(
            new Set([
              ...(formData.chef_technique_id ? [formData.chef_technique_id] : []),
              ...formData.technicien_ids,
            ])
          );

          if (relatedUserIds.length === 0) {
            toast({
              title: 'Error',
              description: 'Please select related users (ChefTech and/or technicians) to notify',
              variant: 'destructive',
            });
            return;
          }

          for (const machineId of formData.machine_ids) {
            const response = await fetch(`${API_BASE_URL}/api/v1/chetop/ordres`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                titre: formData.titre,
                description: formData.description,
                priorite: formData.priorite,
                machine_id: machineId,
                utilisateur_id: formData.chef_technique_id,
                date_echeance: formData.date_echeance ? new Date(formData.date_echeance).toISOString() : null,
              }),
            });

            if (!response.ok) {
              const error = await response.json();
              throw new Error(error.detail || 'Failed to create work order');
            }

            const newOrder = (await response.json()) as { id: number };
            createdIds.push(newOrder.id);

            if (formData.planning_id) {
              await client.entities.planning_ordres_travail.create({
                data: {
                  planning_id: formData.planning_id,
                  ordre_travail_id: newOrder.id,
                  created_at: new Date().toISOString(),
                },
              });
            }

            for (const technicienId of formData.technicien_ids) {
              await client.entities.ordres_intervention.create({
                data: {
                  date_intervention: new Date().toISOString(),
                  ordre_travail_id: newOrder.id,
                  technicien_id: technicienId,
                  statut: 'EN_ATTENTE',
                },
              });
            }

    await client.apiCall.invoke({
              url: '/api/v1/notifications/bulk',
              method: 'POST',
              data: {
                utilisateur_ids: relatedUserIds,
                titre: 'Work Order Created',
                priorite: formData.priorite,
                type: 'WORK_ORDER_CREATED',
                message: `New work order #${newOrder.id}: ${formData.titre}`,
              },
            });

            for (const file of options.attachments) {
              const objectKey = `${newOrder.id}/${file.name}`;
              const uploadUrlResp = await client.apiCall.invoke({
                url: '/api/v1/storage/upload-url',
                method: 'POST',
                data: {
                  bucket_name: 'attachments',
                  object_key: objectKey,
                },
              });

              const uploadUrl = (uploadUrlResp as { data?: { upload_url?: string } }).data?.upload_url;
              if (!uploadUrl) {
                continue;
              }

              await fetch(uploadUrl, {
                method: 'PUT',
                body: file,
              });

              await client.entities.archives.create({
                data: {
                  identifiant_archive: `ARCH-${Date.now()}`,
                  nom: file.name,
                  date_archivage: new Date().toISOString(),
                  type: 'DOCUMENT',
                  object_key: objectKey,
                  ordre_travail_id: newOrder.id,
                  created_at: new Date().toISOString(),
                },
              });
            }
          }
        } else {
          for (const machineId of formData.machine_ids) {
            const response = await client.entities.ordres_travail.create({
              data: {
                titre: formData.titre,
                description: formData.description,
                priorite: formData.priorite,
                machine_id: machineId,
                utilisateur_id: formData.chef_technique_id,
                date_echeance: formData.date_echeance,
                statut: formData.statut,
              },
            });

            createdIds.push(response.data.id);

            for (const file of options.attachments) {
              const objectKey = `${response.data.id}/${file.name}`;
              const uploadUrlResp = await client.apiCall.invoke({
                url: '/api/v1/storage/upload-url',
                method: 'POST',
                data: {
                  bucket_name: 'attachments',
                  object_key: objectKey,
                },
              });

              const uploadUrl = (uploadUrlResp as { data?: { upload_url?: string } }).data?.upload_url;
              if (!uploadUrl) {
                continue;
              }

              await fetch(uploadUrl, {
                method: 'PUT',
                body: file,
              });

              await client.entities.archives.create({
                data: {
                  identifiant_archive: `ARCH-${Date.now()}`,
                  nom: file.name,
                  date_archivage: new Date().toISOString(),
                  type: 'DOCUMENT',
                  object_key: objectKey,
                  ordre_travail_id: response.data.id,
                  created_at: new Date().toISOString(),
                },
              });
            }
          }
        }

        for (const id of createdIds) {
          notifyChange({
            type: 'work_order',
            action: 'create',
            id,
          });
        }

        toast({
          title: 'Success',
          description: 'Work order created successfully',
        });
      }

      setDialogOpen(false);
      options.clearAttachments();
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
