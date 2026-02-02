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
import { Calendar, Plus, Edit, Trash2, Users } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';

interface User {
  id: number;
  nom: string;
  email: string;
  role: string;
}

interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: string;
  shift_type?: string;
  chef_operation_id?: number;
  chef_technique_id?: number;
  assigned_users: User[];
  created_at?: string;
}

export default function PlanningPage() {
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPlanning, setEditingPlanning] = useState<Planning | null>(null);
  const [deletingPlanning, setDeletingPlanning] = useState<Planning | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const { toast } = useToast();

  // User lists for dropdowns
  const [chefOperations, setChefOperations] = useState<User[]>([]);
  const [chefTechniques, setChefTechniques] = useState<User[]>([]);
  const [techniciens, setTechniciens] = useState<User[]>([]);

  const [formData, setFormData] = useState({
    identifiant_planning: '',
    date_debut: '',
    date_fin: '',
    type: 'MAINTENANCE' as 'MAINTENANCE' | 'SHIFT',
    shift_type: undefined as 'MORNING' | 'NIGHT' | undefined,
    chef_operation_id: undefined as number | undefined,
    chef_technique_id: undefined as number | undefined,
    technicien_ids: [] as number[],
  });

  useEffect(() => {
    checkAuth();
    fetchPlannings();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await client.auth.me();
      setCurrentUser(user.data);
    } catch (error) {
      console.error('Auth error:', error);
    }
  };

  const fetchPlannings = async () => {
    try {
      const response = await client.apiCall.invoke({
        url: '/api/v1/plannings',
        method: 'GET',
        data: { skip: 0, limit: 100 },
      });
      setPlannings(response.data.items || []);
    } catch (error) {
      console.error('Error fetching plannings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsersByRole = async (role: string) => {
    try {
      const response = await client.apiCall.invoke({
        url: `/api/v1/plannings/users/by-role/${role}`,
        method: 'GET',
      });
      return response.data || [];
    } catch (error) {
      console.error(`Error fetching ${role} users:`, error);
      return [];
    }
  };

  const handleOpenDialog = async (planning?: Planning) => {
    if (currentUser?.role !== 'ADMIN') {
      toast({
        title: 'Access Denied',
        description: 'Only administrators can create or edit plannings',
        variant: 'destructive',
      });
      return;
    }

    // Fetch users for dropdowns
    const [chefOps, chefTechs, techs] = await Promise.all([
      fetchUsersByRole('CHETOP'),
      fetchUsersByRole('CHEFTECH'),
      fetchUsersByRole('TECHNICIEN'),
    ]);

    setChefOperations(chefOps);
    setChefTechniques(chefTechs);
    setTechniciens(techs);

    if (planning) {
      setEditingPlanning(planning);
      setFormData({
        identifiant_planning: planning.identifiant_planning,
        date_debut: planning.date_debut.split('T')[0],
        date_fin: planning.date_fin.split('T')[0],
        type: planning.type as 'MAINTENANCE' | 'SHIFT',
        shift_type: planning.shift_type as 'MORNING' | 'NIGHT' | undefined,
        chef_operation_id: planning.chef_operation_id,
        chef_technique_id: planning.chef_technique_id,
        technicien_ids: planning.assigned_users
          .filter(u => u.role === 'TECHNICIEN')
          .map(u => u.id),
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
        shift_type: undefined,
        chef_operation_id: undefined,
        chef_technique_id: undefined,
        technicien_ids: [],
      });
    }
    setDialogOpen(true);
  };

  const handleTypeChange = (type: 'MAINTENANCE' | 'SHIFT') => {
    setFormData({
      ...formData,
      type,
      shift_type: type === 'SHIFT' ? 'MORNING' : undefined,
    });
  };

  const toggleTechnicien = (techId: number) => {
    setFormData(prev => ({
      ...prev,
      technicien_ids: prev.technicien_ids.includes(techId)
        ? prev.technicien_ids.filter(id => id !== techId)
        : [...prev.technicien_ids, techId],
    }));
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

      if (formData.type === 'SHIFT' && !formData.shift_type) {
        toast({
          title: 'Validation Error',
          description: 'Please select shift type for SHIFT planning',
          variant: 'destructive',
        });
        return;
      }

      const payload = {
        identifiant_planning: formData.identifiant_planning,
        date_debut: new Date(formData.date_debut).toISOString(),
        date_fin: new Date(formData.date_fin).toISOString(),
        type: formData.type,
        shift_type: formData.shift_type || null,
        chef_operation_id: formData.chef_operation_id || null,
        chef_technique_id: formData.chef_technique_id || null,
        technicien_ids: formData.technicien_ids,
      };

      if (editingPlanning) {
        await client.apiCall.invoke({
          url: `/api/v1/plannings/${editingPlanning.id}`,
          method: 'PUT',
          data: payload,
        });
        toast({
          title: 'Success',
          description: 'Planning updated successfully. Notifications sent to assigned users.',
        });
      } else {
        await client.apiCall.invoke({
          url: '/api/v1/plannings',
          method: 'POST',
          data: payload,
        });
        toast({
          title: 'Success',
          description: 'Planning created successfully. Notifications sent to assigned users.',
        });
      }
      setDialogOpen(false);
      fetchPlannings();
    } catch (error: any) {
      const detail = error?.data?.detail || error?.response?.data?.detail || error?.message;
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
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${deletingPlanning.id}`,
        method: 'DELETE',
      });
      toast({
        title: 'Success',
        description: 'Planning deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingPlanning(null);
      fetchPlannings();
    } catch (error: any) {
      const detail = error?.data?.detail || error?.response?.data?.detail || error?.message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete planning',
        variant: 'destructive',
      });
    }
  };

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
      SHIFT: { label: 'Shift', className: 'bg-blue-100 text-blue-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.MAINTENANCE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getShiftBadge = (shiftType?: string) => {
    if (!shiftType) return null;
    const shiftConfig = {
      MORNING: { label: 'Morning', className: 'bg-yellow-100 text-yellow-800' },
      NIGHT: { label: 'Night', className: 'bg-indigo-100 text-indigo-800' },
    };
    const config = shiftConfig[shiftType as keyof typeof shiftConfig];
    return config ? <Badge className={config.className}>{config.label}</Badge> : null;
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

  const isAdmin = currentUser?.role === 'ADMIN';

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
            {isAdmin ? 'Manage work schedules and maintenance planning' : 'View work schedules and maintenance planning'}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => handleOpenDialog()}>
            <Plus className="mr-2 h-4 w-4" />
            Create Planning
          </Button>
        )}
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
                    {getShiftBadge(planning.shift_type)}
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
                  {planning.assigned_users.length > 0 && (
                    <div className="flex items-start gap-2 text-sm">
                      <Users className="h-4 w-4 text-gray-400 mt-1" />
                      <div className="flex-1">
                        <p className="text-gray-500">Assigned Users</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {planning.assigned_users.map(user => (
                            <Badge key={user.id} variant="outline" className="text-xs">
                              {user.nom} ({user.role})
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                {isAdmin && (
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
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingPlanning ? 'Edit Planning' : 'Create Planning'}</DialogTitle>
            <DialogDescription>
              {editingPlanning ? 'Update planning schedule and assignments' : 'Create a new planning schedule with team assignments'}
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
              <Select value={formData.type} onValueChange={(value) => handleTypeChange(value as 'MAINTENANCE' | 'SHIFT')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                  <SelectItem value="SHIFT">Shift (Day/Night)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.type === 'SHIFT' && (
              <div className="grid gap-2">
                <Label htmlFor="shift_type">Shift Type *</Label>
                <Select value={formData.shift_type} onValueChange={(value) => setFormData({ ...formData, shift_type: value as 'MORNING' | 'NIGHT' })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select shift type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MORNING">Morning</SelectItem>
                    <SelectItem value="NIGHT">Night</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
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

            <div className="border-t pt-4 mt-2">
              <h3 className="font-semibold mb-3">Team Assignment</h3>
              
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="chef_operation">Chef Operation (CHETOP)</Label>
                  <Select 
                    value={formData.chef_operation_id?.toString()} 
                    onValueChange={(value) => setFormData({ ...formData, chef_operation_id: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Chef Operation" />
                    </SelectTrigger>
                    <SelectContent>
                      {chefOperations.map(user => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.nom} ({user.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="chef_technique">Chef Technique (CHEFTECH)</Label>
                  <Select 
                    value={formData.chef_technique_id?.toString()} 
                    onValueChange={(value) => setFormData({ ...formData, chef_technique_id: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Chef Technique" />
                    </SelectTrigger>
                    <SelectContent>
                      {chefTechniques.map(user => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.nom} ({user.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label>Technicians (TECHNICIEN)</Label>
                  <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2">
                    {techniciens.length === 0 ? (
                      <p className="text-sm text-gray-500">No technicians available</p>
                    ) : (
                      techniciens.map(tech => (
                        <div key={tech.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`tech-${tech.id}`}
                            checked={formData.technicien_ids.includes(tech.id)}
                            onCheckedChange={() => toggleTechnicien(tech.id)}
                          />
                          <label
                            htmlFor={`tech-${tech.id}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            {tech.nom} ({tech.email})
                          </label>
                        </div>
                      ))
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    Selected: {formData.technicien_ids.length} technician(s)
                  </p>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingPlanning ? 'Update' : 'Create'} & Notify Users
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