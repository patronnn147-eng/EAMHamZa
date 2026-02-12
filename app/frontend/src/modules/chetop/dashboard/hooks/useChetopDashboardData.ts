import React, { useEffect, useState } from 'react';
import { toast } from '@/hooks/use-toast';
import { client } from '@/lib/api';
import type { CreateWorkOrderFormData, DashboardStats, Machine, Planning, WorkOrder } from '../types';

export const useChetopDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [attachments, setAttachments] = useState<File[]>([]);

  const [formData, setFormData] = useState<CreateWorkOrderFormData>({
    titre: '',
    description: '',
    priorite: 'MOYENNE',
    machine_ids: [],
    planning_id: null,
    chef_technique_id: null,
    technicien_ids: [],
    date_echeance: '',
    statut: 'EN_ATTENTE',
  });

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

      const statsResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/dashboard`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      const statsData = await statsResponse.json();
      setStats(statsData);

      const ordersResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/ordres`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      const ordersData = await ordersResponse.json();
      setWorkOrders(ordersData);

      const machinesResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/machines`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      const machinesData = await machinesResponse.json();
      setMachines(machinesData);

      const planningsResponse = await fetch(`${API_BASE_URL}/api/v1/plannings?skip=0&limit=100`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const planningsData = await planningsResponse.json();
      setPlannings(planningsData.items || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les données du tableau de bord',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.titre || !formData.description || formData.machine_ids.length === 0) {
      toast({
        title: 'Erreur',
        description: 'Veuillez remplir tous les champs obligatoires',
        variant: 'destructive',
      });
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      if (!token) throw new Error('No authentication token');

      const createdOrders: WorkOrder[] = [];
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
          throw new Error(error.detail || 'Échec de la création');
        }

        const newOrder = await response.json();
        createdOrders.push(newOrder);

        if (formData.planning_id) {
          await client.entities.planning_ordres_travail.create({
            data: {
              planning_id: formData.planning_id,
              ordre_travail_id: newOrder.id,
              created_at: new Date().toISOString(),
            },
          });
        }

        for (const file of attachments) {
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
          if (uploadUrl) {
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
      }

      setWorkOrders((prev) => [...createdOrders, ...prev]);
      setShowCreateModal(false);
      setFormData({
        titre: '',
        description: '',
        priorite: 'MOYENNE',
        machine_ids: [],
        planning_id: null,
        chef_technique_id: null,
        technicien_ids: [],
        date_echeance: '',
        statut: 'EN_ATTENTE',
      });
      setAttachments([]);

      toast({
        title: 'Succès',
        description: 'Ordre de travail créé avec succès',
      });

      fetchDashboardData();
    } catch (error) {
      console.error('Error creating work order:', error);
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Échec de la création',
        variant: 'destructive',
      });
    }
  };

  return {
    stats,
    workOrders,
    machines,
    plannings,
    loading,
    showCreateModal,
    setShowCreateModal,
    selectedOrder,
    setSelectedOrder,
    formData,
    setFormData,
    attachments,
    setAttachments,
    handleCreateOrder,
  };
};
