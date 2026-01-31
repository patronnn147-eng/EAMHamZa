import React, { useEffect, useState } from 'react';
import { toast } from '@/hooks/use-toast';
import type { CreateWorkOrderFormData, DashboardStats, Machine, WorkOrder } from '../types';

export const useChetopDashboardData = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);

  const [formData, setFormData] = useState<CreateWorkOrderFormData>({
    titre: '',
    description: '',
    priorite: 'MOYENNE',
    machine_id: 0,
    utilisateur_id: null,
    date_echeance: '',
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

    if (!formData.titre || !formData.description || !formData.machine_id) {
      toast({
        title: 'Erreur',
        description: 'Veuillez remplir tous les champs obligatoires',
        variant: 'destructive',
      });
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/api/v1/chetop/ordres`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Échec de la création');
      }

      const newOrder = await response.json();
      setWorkOrders((prev) => [newOrder, ...prev]);
      setShowCreateModal(false);
      setFormData({
        titre: '',
        description: '',
        priorite: 'MOYENNE',
        machine_id: 0,
        utilisateur_id: null,
        date_echeance: '',
      });

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
    loading,
    showCreateModal,
    setShowCreateModal,
    selectedOrder,
    setSelectedOrder,
    formData,
    setFormData,
    handleCreateOrder,
  };
};
