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
import { Search, Plus, Calendar, AlertCircle, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { OrdreTravail, Machine } from '@/lib/types';

export default function WorkOrders() {
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

  const [formData, setFormData] = useState({
    machine_id: '',
    utilisateur_id: '',
    date_echeance: '',
    priorite: 'MOYENNE',
    statut: 'EN_ATTENTE',
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let filtered = workOrders;

    if (searchTerm) {
      filtered = filtered.filter((wo) =>
        wo.id.toString().includes(searchTerm)
      );
    }

    if (statusFilter !== 'ALL') {
      filtered = filtered.filter((wo) => wo.statut === statusFilter);
    }

    if (priorityFilter !== 'ALL') {
      filtered = filtered.filter((wo) => wo.priorite === priorityFilter);
    }

    setFilteredWorkOrders(filtered);
  }, [searchTerm, statusFilter, priorityFilter, workOrders]);

  const fetchData = async () => {
    try {
      const [workOrdersResponse, machinesResponse] = await Promise.all([
        client.entities.ordres_travail.query({
          query: {},
          sort: '-created_at',
          limit: 100
        }),
        client.entities.machines.query({
          query: {},
          limit: 100
        })
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

  const handleOpenDialog = (workOrder?: OrdreTravail) => {
    if (workOrder) {
      setEditingWorkOrder(workOrder);
      setFormData({
        machine_id: workOrder.machine_id.toString(),
        utilisateur_id: workOrder.utilisateur_id?.toString() || '',
        date_echeance: workOrder.date_echeance.split('T')[0],
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
        toast({
          title: 'Success',
          description: 'Work order updated successfully',
        });
      } else {
        await client.entities.ordres_travail.create({
          data: submitData,
        });
        toast({
          title: 'Success',
          description: 'Work order created successfully',
        });
      }
      setDialogOpen(false);
      fetchData();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
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
      toast({
        title: 'Success',
        description: 'Work order deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingWorkOrder(null);
      fetchData();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete work order',
        variant: 'destructive',
      });
    }
  };

  const getMachineName = (machineId: number) => {
    const machine = machines.find((m) => m.id === machineId);
    return machine ? machine.nom : `Machine #${machineId}`;
  };

  const getStatusBadge = (statut: string) => {
    const statusConfig = {
      EN_ATTENTE: { label: 'Pending', variant: 'secondary' as const },
      EN_COURS: { label: 'In Progress', variant: 'default' as const },
      TERMINE: { label: 'Completed', variant: 'outline' as const },
      ANNULE: { label: 'Cancelled', variant: 'destructive' as const },
    };
    const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getPriorityBadge = (priorite: string) => {
    const priorityConfig = {
      BASSE: { label: 'Low', className: 'bg-gray-100 text-gray-800' },
      MOYENNE: { label: 'Medium', className: 'bg-blue-100 text-blue-800' },
      ELEVEE: { label: 'High', className: 'bg-orange-100 text-orange-800' },
      URGENTE: { label: 'Urgent', className: 'bg-red-100 text-red-800' },
    };
    const config = priorityConfig[priorite as keyof typeof priorityConfig] || priorityConfig.MOYENNE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const isOverdue = (dueDate: string, status: string) => {
    if (status === 'TERMINE' || status === 'ANNULE') return false;
    return new Date(dueDate) < new Date();
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
          <h2 className="text-3xl font-bold text-gray-900">Work Orders</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage and track all maintenance work orders
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Create Work Order
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by work order ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Status</SelectItem>
            <SelectItem value="EN_ATTENTE">Pending</SelectItem>
            <SelectItem value="EN_COURS">In Progress</SelectItem>
            <SelectItem value="TERMINE">Completed</SelectItem>
            <SelectItem value="ANNULE">Cancelled</SelectItem>
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Priority</SelectItem>
            <SelectItem value="BASSE">Low</SelectItem>
            <SelectItem value="MOYENNE">Medium</SelectItem>
            <SelectItem value="ELEVEE">High</SelectItem>
            <SelectItem value="URGENTE">Urgent</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filteredWorkOrders.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">No work orders found</p>
            </CardContent>
          </Card>
        ) : (
          filteredWorkOrders.map((wo) => (
            <Card key={wo.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      Work Order #{wo.id}
                      {isOverdue(wo.date_echeance, wo.statut) && (
                        <AlertCircle className="h-5 w-5 text-red-500" />
                      )}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {getMachineName(wo.machine_id)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getPriorityBadge(wo.priorite)}
                    {getStatusBadge(wo.statut)}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm mb-4">
                  <div>
                    <p className="text-gray-500 flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      Due Date
                    </p>
                    <p className={`font-medium mt-1 ${isOverdue(wo.date_echeance, wo.statut) ? 'text-red-600' : ''}`}>
                      {new Date(wo.date_echeance).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Created</p>
                    <p className="font-medium mt-1">
                      {new Date(wo.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Assigned To</p>
                    <p className="font-medium mt-1">
                      {wo.utilisateur_id ? `User #${wo.utilisateur_id}` : 'Unassigned'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleOpenDialog(wo)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-red-600 hover:text-red-700"
                    onClick={() => {
                      setDeletingWorkOrder(wo);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingWorkOrder ? 'Edit Work Order' : 'Create Work Order'}</DialogTitle>
            <DialogDescription>
              {editingWorkOrder ? 'Update work order information' : 'Enter the details for the new work order'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="machine_id">Machine</Label>
              <Select value={formData.machine_id} onValueChange={(value) => setFormData({ ...formData, machine_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a machine" />
                </SelectTrigger>
                <SelectContent>
                  {machines.map((machine) => (
                    <SelectItem key={machine.id} value={machine.id.toString()}>
                      {machine.nom} ({machine.identifiant_machine})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_echeance">Due Date</Label>
              <Input
                id="date_echeance"
                type="date"
                value={formData.date_echeance}
                onChange={(e) => setFormData({ ...formData, date_echeance: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="priorite">Priority</Label>
              <Select value={formData.priorite} onValueChange={(value) => setFormData({ ...formData, priorite: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BASSE">Low</SelectItem>
                  <SelectItem value="MOYENNE">Medium</SelectItem>
                  <SelectItem value="ELEVEE">High</SelectItem>
                  <SelectItem value="URGENTE">Urgent</SelectItem>
                </SelectContent>
              </Select>
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
              <Label htmlFor="utilisateur_id">Assign To User ID (Optional)</Label>
              <Input
                id="utilisateur_id"
                type="number"
                value={formData.utilisateur_id}
                onChange={(e) => setFormData({ ...formData, utilisateur_id: e.target.value })}
                placeholder="Enter user ID"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingWorkOrder ? 'Update' : 'Create'}
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
              Are you sure you want to delete Work Order #{deletingWorkOrder?.id}? This action cannot be undone.
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