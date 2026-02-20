import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { toDateTimeLocalInputValue } from '@/lib/date';
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
import { Calendar, Plus, Edit, Trash2, Users, Bell, Eye, Mail } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';
import { useNavigate } from 'react-router-dom';
import type { Machine } from '@/lib/types';

import { ZONE_OPTIONS, SOUS_ZONE_OPTIONS_BY_ZONE, ORDRE_TEMPLATES } from '@/lib/constants';

interface User {
  id: number;
  nom: string;
  email: string;
  role: string;
  shift_type?: string | null;
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
  zone_travail?: string;
  assigned_users: User[];
  machine_ids?: number[];
  created_at?: string;
}

export default function PlanningManagement() {
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [resendingPlanningId, setResendingPlanningId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPlanning, setEditingPlanning] = useState<Planning | null>(null);
  const [deletingPlanning, setDeletingPlanning] = useState<Planning | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  // User lists for dropdowns
  const [chefOperations, setChefOperations] = useState<User[]>([]);
  const [chefTechniques, setChefTechniques] = useState<User[]>([]);
  const [techniciens, setTechniciens] = useState<User[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);

  const [formData, setFormData] = useState({
    identifiant_planning: '',
    date_debut: '',
    date_fin: '',
    type: 'MAINTENANCE' as 'MAINTENANCE' | 'SHIFT',
    shift_type: undefined as 'MORNING' | 'NIGHT' | undefined,
    chef_operation_id: undefined as number | undefined,
    chef_technique_id: undefined as number | undefined,
    zone_travail: '',
    sous_zone: '',
    ordre: '',
    technicien_ids: [] as number[],
    machine_ids: [] as number[],
  });

  const getUserShiftBadge = (shiftType?: string | null) => {
    if (!shiftType) return null;
    const shiftConfig = {
      MORNING: { label: 'Morning', className: 'bg-yellow-100 text-yellow-800' },
      NIGHT: { label: 'Night', className: 'bg-indigo-100 text-indigo-800' },
    };
    const config = shiftConfig[shiftType as keyof typeof shiftConfig];
    return config ? <Badge className={config.className}>{config.label}</Badge> : null;
  };

  const filterUsersByPlanningShift = (users: User[]) => {
    if (formData.type !== 'SHIFT' || !formData.shift_type) return users;
    return users.filter(u => (u.shift_type || 'MORNING') === formData.shift_type);
  };

  const handleShiftTypeChange = (shiftType: 'MORNING' | 'NIGHT') => {
    setFormData(prev => {
      const next = { ...prev, shift_type: shiftType };

      const allowedChefOps = new Set(filterUsersByPlanningShift(chefOperations).map(u => u.id));
      const allowedChefTechs = new Set(filterUsersByPlanningShift(chefTechniques).map(u => u.id));
      const allowedTechs = new Set(filterUsersByPlanningShift(techniciens).map(u => u.id));

      if (next.chef_operation_id && !allowedChefOps.has(next.chef_operation_id)) {
        next.chef_operation_id = undefined;
      }
      if (next.chef_technique_id && !allowedChefTechs.has(next.chef_technique_id)) {
        next.chef_technique_id = undefined;
      }

      next.technicien_ids = next.technicien_ids.filter(id => allowedTechs.has(id));
      return next;
    });
  };

  const toggleMachine = (machineId: number) => {
    setFormData((prev) => ({
      ...prev,
      machine_ids: prev.machine_ids.includes(machineId)
        ? prev.machine_ids.filter((id) => id !== machineId)
        : [...prev.machine_ids, machineId],
    }));
  };

  useEffect(() => {
    fetchPlannings();
  }, []);

  const fetchPlannings = async () => {
    try {
      const response = await client.apiCall.invoke({
        url: '/api/v1/plannings',
        method: 'GET',
        query: { skip: 0, limit: 100 },
      });

      const rawData = response?.data || response;
      const items = rawData?.items || (Array.isArray(rawData) ? rawData : []);

      setPlannings(items);
    } catch (error: any) {
      console.error('Error fetching plannings:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to load plannings';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
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
      toast({
        title: 'Error',
        description: `Failed to load ${role} users`,
        variant: 'destructive',
      });
      return [];
    }
  };

  const handleOpenDialog = async (planning?: Planning) => {
    // Fetch users for dropdowns
    const [chefOps, chefTechs, techs, machinesResponse] = await Promise.all([
      fetchUsersByRole('CHETOP'),
      fetchUsersByRole('CHEFTECH'),
      fetchUsersByRole('TECHNICIEN'),
      client.entities.machines.query({ query: {}, sort: '-created_at', limit: 200 }),
    ]);

    setChefOperations(chefOps);
    setChefTechniques(chefTechs);
    setTechniciens(techs);
    setMachines(machinesResponse.data.items || []);

    if (planning) {
      setEditingPlanning(planning);
      setFormData({
        identifiant_planning: planning.identifiant_planning,
        date_debut: toDateTimeLocalInputValue(planning.date_debut),
        date_fin: toDateTimeLocalInputValue(planning.date_fin),
        type: planning.type as 'MAINTENANCE' | 'SHIFT',
        shift_type: planning.shift_type as 'MORNING' | 'NIGHT' | undefined,
        chef_operation_id: planning.chef_operation_id,
        chef_technique_id: planning.chef_technique_id,
        zone_travail: planning.zone_travail || '',
        sous_zone: (planning as any).sous_zone || '',
        ordre: (planning as any).ordre || '',
        technicien_ids: Array.from(
          new Set(
            planning.assigned_users
              .filter(u => u.role === 'TECHNICIEN')
              .map(u => u.id)
          )
        ),
        machine_ids: Array.from(new Set(planning.machine_ids || [])),
      });
    } else {
      setEditingPlanning(null);
      const now = new Date();
      const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      setFormData({
        identifiant_planning: `PLAN-${Date.now()}`,
        date_debut: toDateTimeLocalInputValue(now.toISOString()),
        date_fin: toDateTimeLocalInputValue(nextWeek.toISOString()),
        type: 'MAINTENANCE',
        shift_type: undefined,
        chef_operation_id: undefined,
        chef_technique_id: undefined,
        zone_travail: '',
        sous_zone: '',
        ordre: '',
        technicien_ids: [],
        machine_ids: [],
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

  const handleZoneChange = (zone: string) => {
    setFormData((prev) => ({
      ...prev,
      zone_travail: zone,
      sous_zone: '',
      ordre: '',
      machine_ids: [], // Clear machines when zone changes
    }));
  };

  const handleSubZoneChange = (sous_zone: string) => {
    setFormData((prev) => ({
      ...prev,
      sous_zone,
      ordre: '',
      machine_ids: [],
    }));
  };

  const handleOrderChange = (ordre: string) => {
    setFormData((prev) => ({
      ...prev,
      ordre,
      machine_ids: [],
    }));
  };

  const filteredMachines = machines.filter((m) => {
    // If no zone selected, show no machines
    if (!formData.zone_travail) return false;

    // Filter by zone (exact match)
    const zoneMatch = m.zone === formData.zone_travail;

    // Filter by sub-zone (if selected)
    const subZoneMatch = !formData.sous_zone || m.sous_zone === formData.sous_zone;

    // Filter by order (if selected)
    const orderMatch = !formData.ordre || String(m.ordre) === String(formData.ordre);

    // Filter by availability (support both 'disponible' and 'available')
    const isAvailable = m.statut?.toLowerCase() === 'disponible' || m.statut?.toLowerCase() === 'available' || !m.statut;

    // Always keep already selected machines in the list
    const isSelected = formData.machine_ids.includes(m.id);

    return (zoneMatch && subZoneMatch && orderMatch && isAvailable) || isSelected;
  });

  const handleSubmit = async () => {
    try {
      // Validation
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

      if (formData.type === 'SHIFT' && !formData.chef_operation_id) {
        toast({
          title: 'Validation Error',
          description: 'Chef Operation is required for SHIFT planning',
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
        zone_travail: formData.zone_travail?.trim() ? formData.zone_travail : null,
        sous_zone: formData.sous_zone?.trim() ? formData.sous_zone : null,
        ordre: formData.ordre?.trim() ? formData.ordre : null,
        technicien_ids: Array.from(new Set(formData.technicien_ids)),
        machine_ids: Array.from(new Set(formData.machine_ids)),
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

  const handleResendEmails = async (planningId: number) => {
    try {
      setResendingPlanningId(planningId);
      const response = await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/resend-emails`,
        method: 'POST',
      });

      const queued = (response as { data?: { queued?: number } } | undefined)?.data?.queued;
      toast({
        title: 'Success',
        description: `Emails queued: ${queued ?? 0}`,
      });
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
        || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to resend emails',
        variant: 'destructive',
      });
    } finally {
      setResendingPlanningId(null);
    }
  };

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
      SHIFT: { label: 'Shift', className: 'bg-blue-100 text-blue-800' },
      HEBDOMADAIRE: { label: 'Weekly', className: 'bg-purple-100 text-purple-800' },
      MENSUEL: { label: 'Monthly', className: 'bg-indigo-100 text-indigo-800' },
      JOURNALIER: { label: 'Daily', className: 'bg-teal-100 text-teal-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || { label: type, className: 'bg-gray-100 text-gray-800' };
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
          <h2 className="text-3xl font-bold text-gray-900">Planning Management</h2>
          <p className="mt-1 text-sm text-gray-500">
            Create and manage work schedules, shifts, and maintenance planning
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
            <Button onClick={() => handleOpenDialog()} className="mt-4">
              Create Your First Planning
            </Button>
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
                      <p className="text-gray-500">Start Date & Time</p>
                      <p className="font-medium">
                        {new Date(planning.date_debut).toLocaleString('fr-FR', {
                          year: 'numeric', month: 'long', day: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-gray-500">End Date & Time</p>
                      <p className="font-medium">
                        {new Date(planning.date_fin).toLocaleString('fr-FR', {
                          year: 'numeric', month: 'long', day: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                  {planning.zone_travail && (
                    <div className="flex items-center gap-2 text-sm">
                      <div className="h-4 w-4 text-gray-400">📍</div>
                      <div className="flex-1">
                        <p className="text-gray-500">Localisation</p>
                        <p className="font-medium">
                          {planning.zone_travail}
                          {(planning as any).sous_zone && ` > ${(planning as any).sous_zone}`}
                          {(planning as any).ordre && ` (Ordre: ${(planning as any).ordre})`}
                        </p>
                      </div>
                    </div>
                  )}
                  {planning.assigned_users.length > 0 && (
                    <div className="flex items-start gap-2 text-sm">
                      <Users className="h-4 w-4 text-gray-400 mt-1" />
                      <div className="flex-1">
                        <p className="text-gray-500 flex items-center gap-1">
                          Assigned Users
                          <Bell className="h-3 w-3 text-green-600" title="Notified" />
                        </p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Array.from(new Map(planning.assigned_users.map(user => [user.id, user])).values()).map(user => (
                            <Badge key={user.id} variant="outline" className="text-xs">
                              {user.nom} ({user.role})
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
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
                    className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={() => {
                      setDeletingPlanning(planning);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/admin/planning/${planning.id}`)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    View Details
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    disabled={resendingPlanningId === planning.id}
                    onClick={() => handleResendEmails(planning.id)}
                  >
                    <Mail className="mr-2 h-4 w-4" />
                    {resendingPlanningId === planning.id ? 'Resending...' : 'Resend Emails'}
                  </Button>
                </div>
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
              {editingPlanning
                ? 'Update planning schedule and team assignments. All assigned users will be notified.'
                : 'Create a new planning schedule with team assignments. All assigned users will be notified.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="identifiant_planning">Planning ID *</Label>
              <Input
                id="identifiant_planning"
                value={formData.identifiant_planning}
                onChange={(e) => setFormData({ ...formData, identifiant_planning: e.target.value })}
                placeholder="e.g., PLAN-2026-02"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="type">Planning Type *</Label>
              <Select value={formData.type} onValueChange={(value) => handleTypeChange(value as 'MAINTENANCE' | 'SHIFT')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                  <SelectItem value="SHIFT">Shift (Day/Night Operations)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                {formData.type === 'MAINTENANCE'
                  ? 'Maintenance planning for equipment servicing and repairs'
                  : 'Shift planning for day/night team operations'}
              </p>
            </div>

            {formData.type === 'SHIFT' && (
              <div className="grid gap-2">
                <Label htmlFor="shift_type">Shift Type * (Required for SHIFT)</Label>
                <Select value={formData.shift_type} onValueChange={(value) => handleShiftTypeChange(value as 'MORNING' | 'NIGHT')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select shift type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MORNING">Morning Shift</SelectItem>
                    <SelectItem value="NIGHT">Night Shift</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="date_debut">Start Date *</Label>
                <Input
                  id="date_debut"
                  type="datetime-local"
                  value={formData.date_debut}
                  onChange={(e) => setFormData({ ...formData, date_debut: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="date_fin">End Date *</Label>
                <Input
                  id="date_fin"
                  type="datetime-local"
                  value={formData.date_fin}
                  onChange={(e) => setFormData({ ...formData, date_fin: e.target.value })}
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="zone_travail">Zone de Travail</Label>
              <Select
                value={formData.zone_travail}
                onValueChange={handleZoneChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner une zone de travail" />
                </SelectTrigger>
                <SelectContent>
                  {ZONE_OPTIONS.map((zone) => (
                    <SelectItem key={zone} value={zone}>
                      {zone}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Sub-Zone Selection */}
            {formData.zone_travail && SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone_travail]?.length > 0 && (
              <div className="space-y-2">
                <Label>Sous-Zone</Label>
                <Select
                  value={formData.sous_zone}
                  onValueChange={handleSubZoneChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner une sous-zone" />
                  </SelectTrigger>
                  <SelectContent>
                    {SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone_travail].map((subZone) => (
                      <SelectItem key={subZone} value={subZone}>
                        {subZone}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Order Selection */}
            {formData.zone_travail && formData.sous_zone && ORDRE_TEMPLATES[formData.zone_travail]?.[formData.sous_zone] && (
              <div className="space-y-2">
                <Label>Ordre (Position dans la ligne)</Label>
                <Select
                  value={formData.ordre}
                  onValueChange={handleOrderChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un ordre/position" />
                  </SelectTrigger>
                  <SelectContent>
                    {ORDRE_TEMPLATES[formData.zone_travail][formData.sous_zone].map((template) => (
                      <SelectItem key={template.ordre} value={String(template.ordre)}>
                        {template.ordre} - {template.nom}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Machines</Label>
              <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
                {filteredMachines.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    {formData.zone_travail
                      ? 'Aucune machine disponible dans cette zone'
                      : 'Veuillez sélectionner une zone de travail d\'abord'}
                  </p>
                ) : (
                  filteredMachines.map((m) => (
                    <div key={m.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                      <Checkbox
                        id={`machine-${m.id}`}
                        checked={formData.machine_ids.includes(m.id)}
                        onCheckedChange={() => toggleMachine(m.id)}
                      />
                      <label
                        htmlFor={`machine-${m.id}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex-1"
                      >
                        {m.nom} (#{m.id}) - {m.statut}
                      </label>
                    </div>
                  ))
                )}
              </div>
              <p className="text-xs text-gray-500">Selected: {formData.machine_ids.length} machine(s)</p>
            </div>

            <div className="grid gap-2">
              <Label>Team Assignment</Label>
              <Badge variant="outline" className="text-xs">Step-by-step</Badge>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              {formData.type === 'SHIFT'
                ? '1. Select Chef Operation → 2. Select Chef Technique → 3. Select Technicians → 4. Choose Shift Type'
                : '1. Select Chef Operation → 2. Select Chef Technique → 3. Select Technicians'}
            </p>

            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="chef_operation">
                  Step 1: Chef Operation (CHETOP) {formData.type === 'SHIFT' && '*'}
                </Label>
                <Select
                  value={formData.chef_operation_id?.toString()}
                  onValueChange={(value) => setFormData({ ...formData, chef_operation_id: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Chef Operation" />
                  </SelectTrigger>
                  <SelectContent>
                    {filterUsersByPlanningShift(chefOperations).length === 0 ? (
                      <SelectItem value="none" disabled>
                        No CHETOP users available
                      </SelectItem>
                    ) : (
                      filterUsersByPlanningShift(chefOperations).map((user) => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          <div className="flex items-center justify-between gap-2 w-full">
                            <span>
                              {user.nom} - {user.email}
                            </span>
                            {getUserShiftBadge(user.shift_type)}
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="chef_technique">Step 2: Chef Technique (CHEFTECH)</Label>
                <Select
                  value={formData.chef_technique_id?.toString()}
                  onValueChange={(value) => setFormData({ ...formData, chef_technique_id: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Chef Technique" />
                  </SelectTrigger>
                  <SelectContent>
                    {filterUsersByPlanningShift(chefTechniques).length === 0 ? (
                      <SelectItem value="none" disabled>
                        No CHEFTECH users available
                      </SelectItem>
                    ) : (
                      filterUsersByPlanningShift(chefTechniques).map((user) => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          <div className="flex items-center justify-between gap-2 w-full">
                            <span>
                              {user.nom} - {user.email}
                            </span>
                            {getUserShiftBadge(user.shift_type)}
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Step 3: Technicians (TECHNICIEN)</Label>
                <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
                  {filterUsersByPlanningShift(techniciens).length === 0 ? (
                    <p className="text-sm text-gray-500">No technicians available</p>
                  ) : (
                    filterUsersByPlanningShift(techniciens).map((tech) => (
                      <div key={tech.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                        <Checkbox
                          id={`tech-${tech.id}`}
                          checked={formData.technicien_ids.includes(tech.id)}
                          onCheckedChange={() => toggleTechnicien(tech.id)}
                        />
                        <label
                          htmlFor={`tech-${tech.id}`}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex-1"
                        >
                          {tech.nom} - {tech.email}
                        </label>
                        {getUserShiftBadge(tech.shift_type)}
                      </div>
                    ))
                  )}
                </div>
                <p className="text-xs text-gray-500">Selected: {formData.technicien_ids.length} technician(s)</p>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} className="gap-2">
              <Bell className="h-4 w-4" />
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
              Are you sure you want to delete planning "{deletingPlanning?.identifiant_planning}"?
              This will remove all user assignments and cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete Planning
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}