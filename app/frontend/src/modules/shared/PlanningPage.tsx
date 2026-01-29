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
import { Calendar, Plus, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Planning } from '@/lib/types';

export default function PlanningPage() {
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPlanning, setEditingPlanning] = useState<Planning | null>(null);
  const [deletingPlanning, setDeletingPlanning] = useState<Planning | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    identifiant_planning: '',
    date_debut: '',
    date_fin: '',
    type: 'MAINTENANCE',
  });

  useEffect(() => {
    fetchPlannings();
  }, []);

  const fetchPlannings = async () => {
    try {
      const response = await client.entities.plannings.query({
        query: {},
        sort: '-date_debut',
        limit: 100
      });
      const planningsList = response.data.items || [];
      setPlannings(planningsList);
    } catch (error) {
      console.error('Error fetching plannings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (planning?: Planning) => {
    if (planning) {
      setEditingPlanning(planning);
      setFormData({
        identifiant_planning: planning.identifiant_planning,
        date_debut: planning.date_debut.split('T')[0],
        date_fin: planning.date_fin.split('T')[0],
        type: planning.type,
      });
    } else {
      setEditingPlanning(null);
      const now = new Date();
      const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      setFormData({
        identifiant_planning: `PLAN-${Date.now()}`,
        date_debut: now.toISOString().split('T')[0],
        date_fin: nextWeek.toISOString().split('T')[0],
        type: 'MAINTENANCE',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (!formData.identifiant_planning.trim() || !formData.date_debut || !formData.date_fin) {
        toast({
          title: 'Validation Error',
          description: 'Please fill in all required fields',
          variant: 'destructive',
        });
        return;
      }

      if (new Date(formData.date_fin) < new Date(formData.date_debut)) {
        toast({
          title: 'Validation Error',
          description: 'End date must be after start date',
          variant: 'destructive',
        });
        return;
      }

      if (editingPlanning) {
        await client.entities.plannings.update({
          id: editingPlanning.id.toString(),
          data: formData,
        });
        toast({
          title: 'Success',
          description: 'Planning updated successfully',
        });
      } else {
        await client.entities.plannings.create({
          data: formData,
        });
        toast({
          title: 'Success',
          description: 'Planning created successfully',
        });
      }
      setDialogOpen(false);
      fetchPlannings();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to save planning',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingPlanning) return;
    
    try {
      await client.entities.plannings.delete({ id: deletingPlanning.id.toString() });
      toast({
        title: 'Success',
        description: 'Planning deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingPlanning(null);
      fetchPlannings();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete planning',
        variant: 'destructive',
      });
    }
  };

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      JOURNALIER: { label: 'Daily', className: 'bg-blue-100 text-blue-800' },
      HEBDOMADAIRE: { label: 'Weekly', className: 'bg-green-100 text-green-800' },
      MENSUEL: { label: 'Monthly', className: 'bg-purple-100 text-purple-800' },
      MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.MAINTENANCE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const isActive = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    return now >= start && now <= end;
  };

  const getDuration = (dateDebut: string, dateFin: string) => {
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
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
          <h2 className="text-3xl font-bold text-gray-900">Planning</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage work schedules and maintenance planning
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Create Planning
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No planning schedules found</p>
          </div>
        ) : (
          plannings.map((planning) => (
            <Card key={planning.id} className={`hover:shadow-lg transition-shadow ${isActive(planning.date_debut, planning.date_fin) ? 'border-green-500 border-2' : ''}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{planning.identifiant_planning}</CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {getDuration(planning.date_debut, planning.date_fin)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {getTypeBadge(planning.type)}
                    {isActive(planning.date_debut, planning.date_fin) && (
                      <Badge className="bg-green-100 text-green-800">Active</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 mb-4">
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-gray-500">Start Date</p>
                      <p className="font-medium">
                        {new Date(planning.date_debut).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-gray-500">End Date</p>
                      <p className="font-medium">
                        {new Date(planning.date_fin).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleOpenDialog(planning)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-red-600 hover:text-red-700"
                    onClick={() => {
                      setDeletingPlanning(planning);
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
            <DialogTitle>{editingPlanning ? 'Edit Planning' : 'Create Planning'}</DialogTitle>
            <DialogDescription>
              {editingPlanning ? 'Update planning schedule' : 'Create a new planning schedule'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="identifiant_planning">Planning ID *</Label>
              <Input
                id="identifiant_planning"
                value={formData.identifiant_planning}
                onChange={(e) => setFormData({ ...formData, identifiant_planning: e.target.value })}
                placeholder="e.g., PLAN-2026-01"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="type">Type *</Label>
              <Select value={formData.type} onValueChange={(value) => setFormData({ ...formData, type: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="JOURNALIER">Daily</SelectItem>
                  <SelectItem value="HEBDOMADAIRE">Weekly</SelectItem>
                  <SelectItem value="MENSUEL">Monthly</SelectItem>
                  <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_debut">Start Date *</Label>
              <Input
                id="date_debut"
                type="date"
                value={formData.date_debut}
                onChange={(e) => setFormData({ ...formData, date_debut: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_fin">End Date *</Label>
              <Input
                id="date_fin"
                type="date"
                value={formData.date_fin}
                onChange={(e) => setFormData({ ...formData, date_fin: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingPlanning ? 'Update' : 'Create'}
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
              Are you sure you want to delete "{deletingPlanning?.identifiant_planning}"? This action cannot be undone.
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