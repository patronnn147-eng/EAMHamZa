import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, Plus, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine } from '@/lib/types';

export default function Machines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState<Machine | null>(null);
  const [deletingMachine, setDeletingMachine] = useState<Machine | null>(null);
  const { toast } = useToast();
  const { user } = useAuth();
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
          m.type.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const fetchMachines = async () => {
    try {
      const response = await client.entities.machines.query({
        query: {},
        sort: '-created_at',
        limit: 100
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

  const handleOpenDialog = (machine?: Machine) => {
    if (machine) {
      setEditingMachine(machine);
      setFormData({
        nom: machine.nom,
        identifiant_machine: machine.identifiant_machine,
        type: machine.type,
        emplacement: machine.emplacement,
        statut: machine.statut,
        date_derniere_maintenance: machine.date_derniere_maintenance || '',
        date_prochaine_maintenance: machine.date_prochaine_maintenance || '',
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
          id: editingMachine.id
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
          id: response.data.id
        });
        toast({
          title: 'Success',
          description: 'Machine created successfully',
        });
      }
      setDialogOpen(false);
      fetchMachines();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to save machine',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingMachine) return;
    
    try {
      await client.entities.machines.delete({ id: deletingMachine.id.toString() });
      notifyChange({
        type: 'machine',
        action: 'delete',
        id: deletingMachine.id
      });
      toast({
        title: 'Success',
        description: 'Machine deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingMachine(null);
      fetchMachines();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete machine',
        variant: 'destructive',
      });
    }
  };

  const getStatusBadge = (statut: string) => {
    const statusConfig = {
      EN_ATTENTE: { label: 'Pending', className: 'bg-yellow-100 text-yellow-800' },
      EN_COURS: { label: 'In Progress', className: 'bg-blue-100 text-blue-800' },
      TERMINE: { label: 'Completed', className: 'bg-green-100 text-green-800' },
      ANNULE: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
    };
    const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage and monitor all machines in your facility
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Add Machine
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search machines by name, ID, location, or type..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMachines.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No machines found</p>
          </div>
        ) : (
          filteredMachines.map((machine) => (
            <Card key={machine.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{machine.nom}</CardTitle>
                    <p className="text-sm text-gray-500 mt-1">{machine.identifiant_machine}</p>
                  </div>
                  {getStatusBadge(machine.statut)}
                </div>
              </CardHeader>
              <CardContent>
                <img
                  src={machine.image_url || 'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'}
                  alt={machine.nom}
                  className="w-full h-48 object-cover rounded-md mb-4"
                />
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Type:</span>
                    <span className="font-medium">{machine.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Location:</span>
                    <span className="font-medium">{machine.emplacement}</span>
                  </div>
                  {machine.date_derniere_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Last Maintenance:</span>
                      <span className="font-medium">
                        {new Date(machine.date_derniere_maintenance).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  {machine.date_prochaine_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Next Maintenance:</span>
                      <span className="font-medium text-orange-600">
                        {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleOpenDialog(machine)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  {user?.role === 'ADMIN' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 text-red-600 hover:text-red-700"
                      onClick={() => {
                        setDeletingMachine(machine);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingMachine ? 'Edit Machine' : 'Add New Machine'}</DialogTitle>
            <DialogDescription>
              {editingMachine ? 'Update machine information' : 'Enter the details for the new machine'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="nom">Name</Label>
              <Input
                id="nom"
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Machine name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="identifiant_machine">Machine ID</Label>
              <Input
                id="identifiant_machine"
                value={formData.identifiant_machine}
                onChange={(e) => setFormData({ ...formData, identifiant_machine: e.target.value })}
                placeholder="e.g., MCH-001"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="type">Type</Label>
              <Input
                id="type"
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                placeholder="Machine type"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="emplacement">Location</Label>
              <Input
                id="emplacement"
                value={formData.emplacement}
                onChange={(e) => setFormData({ ...formData, emplacement: e.target.value })}
                placeholder="Machine location"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="statut">Status</Label>
              <Select value={formData.statut} onValueChange={(value) => setFormData({ ...formData, statut: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="EN_ATTENTE">Pending</SelectItem>
                  <SelectItem value="EN_COURS">In Progress</SelectItem>
                  <SelectItem value="TERMINE">Completed</SelectItem>
                  <SelectItem value="ANNULE">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_derniere_maintenance">Last Maintenance Date</Label>
              <Input
                id="date_derniere_maintenance"
                type="date"
                value={formData.date_derniere_maintenance}
                onChange={(e) => setFormData({ ...formData, date_derniere_maintenance: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_prochaine_maintenance">Next Maintenance Date</Label>
              <Input
                id="date_prochaine_maintenance"
                type="date"
                value={formData.date_prochaine_maintenance}
                onChange={(e) => setFormData({ ...formData, date_prochaine_maintenance: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="image_url">Image URL</Label>
              <Input
                id="image_url"
                value={formData.image_url}
                onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                placeholder="/images/ImageUpload.jpg"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingMachine ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingMachine?.nom}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}