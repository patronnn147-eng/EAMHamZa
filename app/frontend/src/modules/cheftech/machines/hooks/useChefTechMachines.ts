import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { toDateInputValue } from '@/lib/date';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine } from '@/lib/types';

export const useChefTechMachines = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState<Machine | null>(null);
  const { toast } = useToast();
  const { notifyChange, subscribe } = useDataSync();

  const [formData, setFormData] = useState({
    nom: '',
    identifiant_machine: '',
    type: '',
    emplacement: '',
    statut: 'EN_ATTENTE',
    date_derniere_maintenance: '',
    date_prochaine_maintenance: '',
    image_url: '',
  });

  const fetchMachines = async () => {
    try {
      const response = await client.entities.machines.query({
        query: {},
        sort: '-created_at',
        limit: 100,
      });
      const machinesList = response.data.items || [];
      setMachines(machinesList);
      setFilteredMachines(machinesList);
    } catch (error) {
      console.error('Error fetching machines:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (event.type === 'machine') {
        fetchMachines();
      }
    });
    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = machines.filter(
        (m) =>
          m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.identifiant_machine.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.emplacement.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.type.toLowerCase().includes(searchTerm.toLowerCase()),
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const handleOpenDialog = (machine?: Machine) => {
    if (machine) {
      setEditingMachine(machine);
      setFormData({
        nom: machine.nom,
        identifiant_machine: machine.identifiant_machine,
        type: machine.type,
        emplacement: machine.emplacement,
        statut: machine.statut,
        date_derniere_maintenance: toDateInputValue(machine.date_derniere_maintenance),
        date_prochaine_maintenance: toDateInputValue(machine.date_prochaine_maintenance),
        image_url: machine.image_url || '',
      });
    } else {
      setEditingMachine(null);
      setFormData({
        nom: '',
        identifiant_machine: '',
        type: '',
        emplacement: '',
        statut: 'EN_ATTENTE',
        date_derniere_maintenance: '',
        date_prochaine_maintenance: '',
        image_url: '',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingMachine) {
        await client.entities.machines.update({
          id: editingMachine.id.toString(),
          data: formData,
        });
        notifyChange({
          type: 'machine',
          action: 'update',
          id: editingMachine.id,
        });
        toast({
          title: 'Success',
          description: 'Machine updated successfully',
        });
      } else {
        const response = await client.entities.machines.create({
          data: formData,
        });
        notifyChange({
          type: 'machine',
          action: 'create',
          id: response.data.id,
        });
        toast({
          title: 'Success',
          description: 'Machine created successfully',
        });
      }

      setDialogOpen(false);
      fetchMachines();
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;

      toast({
        title: 'Error',
        description: detail || 'Failed to save machine',
        variant: 'destructive',
      });
    }
  };

  return {
    filteredMachines,
    searchTerm,
    setSearchTerm,
    loading,
    dialogOpen,
    setDialogOpen,
    editingMachine,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
  };
};
