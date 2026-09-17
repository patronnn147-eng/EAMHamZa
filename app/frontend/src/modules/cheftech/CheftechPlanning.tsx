import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Users, Eye, Send } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { AppPagination } from '@/components/shared/AppPagination';

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
  zone_travail?: string;
  sous_zone?: string;
  ordre?: string | number;
  assigned_users: User[];
  planning_statut?: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  DRAFT: { label: 'Brouillon', className: 'bg-gray-100 text-gray-800' },
  SUBMITTED: { label: 'Soumis', className: 'bg-yellow-100 text-yellow-800' },
  APPROVED: { label: 'Approuvé', className: 'bg-green-100 text-green-800' },
  REJECTED: { label: 'Rejeté', className: 'bg-red-100 text-red-800' },
};

export default function CheftechPlanning() {
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();
  const pageSize = 12;

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
      const detail = error?.response?.data?.detail || error?.message || 'Failed to load plannings';
      toast({ title: 'Error', description: detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForApproval = async (planningId: number) => {
    setSubmittingId(planningId);
    try {
      await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}/submit`,
        method: 'POST',
      });
      toast({ title: 'Success', description: 'Planning submitted for approval' });
      fetchPlannings();
    } catch (error: any) {
      const detail = error?.data?.detail || error?.response?.data?.detail || error?.message;
      toast({
        title: 'Error',
        description: detail || 'Failed to submit planning',
        variant: 'destructive',
      });
    } finally {
      setSubmittingId(null);
    }
  };

  const getStatusBadge = (status?: string) => {
    if (!status) return null;
    const config = STATUS_CONFIG[status] || { label: status, className: 'bg-blue-100 text-blue-800' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getDuration = (dateDebut: string, dateFin: string) => {
    const diff = Math.abs(new Date(dateFin).getTime() - new Date(dateDebut).getTime());
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    return `${days} day${days !== 1 ? 's' : ''}`;
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
      <div>
        <h2 className="text-4xl font-bold text-white">Planning Management</h2>
        <p className="mt-1 text-sm text-blue-300">Review and submit plannings for approval</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-blue-300">No planning schedules found</p>
          </div>
        ) : (
          plannings.map((planning) => (
            <Card key={planning.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{planning.identifiant_planning}</CardTitle>
                    <p className="text-sm text-blue-300 mt-1">
                      {getDuration(planning.date_debut, planning.date_fin)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {getStatusBadge(planning.planning_statut)}
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
                          hour: '2-digit', minute: '2-digit',
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
                          hour: '2-digit', minute: '2-digit',
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
                        <p className="text-blue-300">Assigned Team</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Array.from(
                            new Map(planning.assigned_users.map((u) => [u.id, u])).values()
                          ).map((u) => (
                            <Badge key={u.id} variant="outline" className="text-xs">
                              {u.nom} ({u.role})
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {planning.planning_statut === 'DRAFT' && (
                  <div className="flex gap-2 pt-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 bg-yellow-50 text-yellow-700 hover:bg-yellow-100 border-yellow-300"
                      disabled={submittingId === planning.id}
                      onClick={() => navigate(`/cheftech/planning/${planning.id}/tasks`)}
                    >
                      <Send className="mr-2 h-4 w-4" />
                      {submittingId === planning.id ? 'Submitting...' : 'Créer les tâches'}
                    </Button>
                  </div>
                )}

                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/cheftech/planning/${planning.id}`)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    View Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <AppPagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
