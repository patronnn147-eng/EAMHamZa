import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { Search, Plus, Calendar, FileText, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Intervention, OrdreTravail } from '@/lib/types';

export default function Interventions() {
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
  const { user } = useAuth();
  const { notifyChange, subscribe } = useDataSync();

  const [formData, setFormData] = useState({
    date_intervention: '',
    rapport: '',
    ordre_travail_id: '',
  });

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
          i.id.toString().includes(searchTerm)
      );
      setFilteredInterventions(filtered);
    } else {
      setFilteredInterventions(interventions);
    }
  }, [searchTerm, interventions]);

  const fetchData = async () => {
    try {
      const [interventionsResponse, workOrdersResponse] = await Promise.all([
        client.entities.ordres_intervention.query({
          query: {},
          sort: '-date_intervention',
          limit: 100
        }),
        client.entities.ordres_travail.query({
          query: {},
          limit: 100
        })
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

  const handleOpenDialog = (intervention?: Intervention) => {
    if (intervention) {
      setEditingIntervention(intervention);
      setFormData({
        date_intervention: intervention.date_intervention.split('T')[0],
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
          id: editingIntervention.id
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
          id: response.data.id
        });
        toast({
          title: 'Success',
          description: 'Intervention recorded successfully',
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
        id: deletingIntervention.id
      });
      toast({
        title: 'Success',
        description: 'Intervention deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingIntervention(null);
      fetchData();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete intervention',
        variant: 'destructive',
      });
    }
  };

  const getWorkOrderInfo = (ordreId: number) => {
    const workOrder = workOrders.find((wo) => wo.id === ordreId);
    return workOrder ? `Work Order #${workOrder.id}` : `Work Order #${ordreId}`;
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
          <h2 className="text-3xl font-bold text-gray-900">Interventions</h2>
          <p className="mt-1 text-sm text-gray-500">
            Track and document all maintenance interventions
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Record Intervention
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search interventions by ID or report content..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filteredInterventions.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">No interventions found</p>
            </CardContent>
          </Card>
        ) : (
          filteredInterventions.map((intervention) => (
            <Card key={intervention.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      Intervention #{intervention.id}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {getWorkOrderInfo(intervention.ordre_travail_id)}
                    </p>
                  </div>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(intervention.date_intervention).toLocaleDateString()}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Report:</h4>
                  <p className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                    {intervention.rapport}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleOpenDialog(intervention)}
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
                        setDeletingIntervention(intervention);
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingIntervention ? 'Edit Intervention' : 'Record Intervention'}</DialogTitle>
            <DialogDescription>
              {editingIntervention ? 'Update intervention details' : 'Document a new maintenance intervention'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="ordre_travail_id">Work Order *</Label>
              <Select value={formData.ordre_travail_id} onValueChange={(value) => setFormData({ ...formData, ordre_travail_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a work order" />
                </SelectTrigger>
                <SelectContent>
                  {workOrders.map((wo) => (
                    <SelectItem key={wo.id} value={wo.id.toString()}>
                      Work Order #{wo.id} - {wo.statut}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_intervention">Intervention Date *</Label>
              <Input
                id="date_intervention"
                type="date"
                value={formData.date_intervention}
                onChange={(e) => setFormData({ ...formData, date_intervention: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="rapport">Report *</Label>
              <Textarea
                id="rapport"
                value={formData.rapport}
                onChange={(e) => setFormData({ ...formData, rapport: e.target.value })}
                placeholder="Describe the intervention performed, issues found, and actions taken..."
                rows={8}
                className="resize-none"
              />
              <p className="text-xs text-gray-500">
                {formData.rapport.length} characters
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingIntervention ? 'Update' : 'Record'}
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
              Are you sure you want to delete Intervention #{deletingIntervention?.id}? This action cannot be undone.
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