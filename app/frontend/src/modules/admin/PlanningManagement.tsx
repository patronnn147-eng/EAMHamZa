import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Calendar, Plus, Edit, Trash2, Users, Bell, Eye, Mail, Send, Check, X } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { AppPagination } from '@/components/shared/AppPagination';
import PlanningWizard from './PlanningWizard';

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
  sous_zone?: string;
  ordre?: string;
  assigned_users: User[];
  machine_ids?: number[];
  created_at?: string;
  planning_statut?: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
}

export default function PlanningManagement() {
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(12);
  const [resendingPlanningId, setResendingPlanningId] = useState<number | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingPlanning, setEditingPlanning] = useState<Planning | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingPlanning, setDeletingPlanning] = useState<Planning | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const isChefTech = user?.role === 'CHEFTECH';

  const [submittingPlanningId, setSubmittingPlanningId] = useState<number | null>(null);
  const [approvingPlanningId, setApprovingPlanningId] = useState<number | null>(null);
  const [rejectingPlanningId, setRejectingPlanningId] = useState<number | null>(null);

  useEffect(() => {
    fetchPlannings();
  }, [page]);

  const fetchPlannings = async () => {
    try {
      setLoading(true);
      const response = await client.apiCall.invoke({
        url: `/api/v1/plannings?page=${page}&size=${pageSize}`,
        method: 'GET',
      });

      const data = response?.data || response;
      const items = data?.items || (Array.isArray(data) ? data : []);

      setPlannings(items);
      setTotalPages(data?.total_pages || 1);
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

  const handleOpenDialog = (planning?: Planning) => {
    setEditingPlanning(planning ?? null);
    setWizardOpen(true);
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

  const handleSubmitForApprovalHandler = async (planningId: number) => {
    try {
      setSubmittingPlanningId(planningId);
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/submit`,
        method: 'POST',
      });
      toast({
        title: 'Success',
        description: 'Planning submitted for approval',
      });
      fetchPlannings();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
        || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to submit planning',
        variant: 'destructive',
      });
    } finally {
      setSubmittingPlanningId(null);
    }
  };

  const isActive = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    return now >= start && now <= end;
  };

  const handleApprove = async (planningId: number) => {
    try {
      setApprovingPlanningId(planningId);
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/approve`,
        method: 'POST',
      });
      toast({
        title: 'Success',
        description: 'Planning approved',
      });
      fetchPlannings();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
        || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to approve planning',
        variant: 'destructive',
      });
    } finally {
      setApprovingPlanningId(null);
    }
  };

  const handleReject = async (planningId: number) => {
    try {
      setRejectingPlanningId(planningId);
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/reject`,
        method: 'POST',
      });
      toast({
        title: 'Success',
        description: 'Planning rejected',
      });
      fetchPlannings();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
        || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to reject planning',
        variant: 'destructive',
      });
    } finally {
      setRejectingPlanningId(null);
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
    const config = typeConfig[type as keyof typeof typeConfig] || { label: type, className: 'bg-gray-100 text-blue-50' };
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

  const getStatusBadge = (statut?: string) => {
    if (!statut) return null;
    const statusConfig: Record<string, { label: string; className: string }> = {
      DRAFT: { label: 'Brouillon', className: 'bg-gray-100 text-gray-800' },
      SUBMITTED: { label: 'Soumis', className: 'bg-yellow-100 text-yellow-800' },
      APPROVED: { label: 'Approuvé', className: 'bg-green-100 text-green-800' },
      REJECTED: { label: 'Rejeté', className: 'bg-red-100 text-red-800' },
    };
    const config = statusConfig[statut];
    return config ? <Badge className={config.className}>{config.label}</Badge> : null;
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
          <h2 className="text-4xl font-bold text-white">Planning Management</h2>
          <p className="mt-1 text-sm text-blue-300">
            Create and manage work schedules, shifts, and maintenance planning
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} className="bg-blue-600 hover:bg-blue-700 text-white">
          <Plus className="mr-2 h-4 w-4" />
          Create Planning
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-blue-300">No planning schedules found</p>
            <Button onClick={() => handleOpenDialog()} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">
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
                    <p className="text-sm text-blue-300 mt-1">
                      {getDuration(planning.date_debut, planning.date_fin)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {getTypeBadge(planning.type)}
                    {getShiftBadge(planning.shift_type)}
                    {getStatusBadge(planning.planning_statut)}
                    {isActive(planning.date_debut, planning.date_fin) && (
                      <Badge className="bg-green-100 text-green-800">Active</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 mb-4">
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-blue-400" />
                    <div>
                      <p className="text-blue-300">Start Date & Time</p>
                      <p className="font-medium">
                        {new Date(planning.date_debut).toLocaleString('fr-FR', {
                          year: 'numeric', month: 'long', day: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-blue-400" />
                    <div>
                      <p className="text-blue-300">End Date & Time</p>
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
                      <div className="h-4 w-4 text-blue-400">📍</div>
                      <div className="flex-1">
                        <p className="text-blue-300">Localisation</p>
                        <p className="font-medium">
                          {planning.zone_travail}
                          {planning.sous_zone && ` > ${planning.sous_zone}`}
                          {planning.ordre && ` (Ordre: ${planning.ordre})`}
                        </p>
                      </div>
                    </div>
                  )}
                  {planning.assigned_users?.length > 0 && (
                    <div className="flex items-start gap-2 text-sm">
                      <Users className="h-4 w-4 text-blue-400 mt-1" />
                      <div className="flex-1">
                        <p className="text-blue-300 flex items-center gap-1">
                          Assigned Users
                          <Bell className="h-3 w-3 text-green-600" />
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
                {/* ADMIN: Edit + Delete buttons */}
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
                )}
                {/* Submit for approval - CHEFTECH only for DRAFT */}
                {(isChefTech && planning.planning_statut === 'DRAFT') && (
                  <div className="flex gap-2 pt-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 bg-yellow-50 text-yellow-700 hover:bg-yellow-100 border-yellow-300"
                      disabled={submittingPlanningId === planning.id}
                      onClick={() => handleSubmitForApprovalHandler(planning.id)}
                    >
                      <Send className="mr-2 h-4 w-4" />
                      {submittingPlanningId === planning.id ? 'Submitting...' : 'Soumettre pour approbation'}
                    </Button>
                  </div>
                )}
                {/* Approve/Reject - ADMIN only for SUBMITTED */}
                {(isAdmin && planning.planning_statut === 'SUBMITTED') && (
                  <div className="flex gap-2 pt-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 bg-green-50 text-green-700 hover:bg-green-100 border-green-300"
                      disabled={approvingPlanningId === planning.id}
                      onClick={() => handleApprove(planning.id)}
                    >
                      <Check className="mr-2 h-4 w-4" />
                      {approvingPlanningId === planning.id ? 'Approving...' : 'Approuver'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 bg-red-50 text-red-700 hover:bg-red-100 border-red-300"
                      disabled={rejectingPlanningId === planning.id}
                      onClick={() => handleReject(planning.id)}
                    >
                      <X className="mr-2 h-4 w-4" />
                      {rejectingPlanningId === planning.id ? 'Rejecting...' : 'Rejeter'}
                    </Button>
                  </div>
                )}
                {/* View Details - Always show */}
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
                  {/* Resend Emails - ADMIN only */}
                  {isAdmin && (
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
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <AppPagination
        currentPage={page}
        totalPages={totalPages}
        onPageChange={setPage}
      />

      <PlanningWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        planning={editingPlanning}
        onSuccess={fetchPlannings}
      />

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
