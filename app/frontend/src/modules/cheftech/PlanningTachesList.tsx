import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Eye, List } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';

interface PlanningWithTasks {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  planning_statut: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  task_count: number;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  DRAFT: { label: 'Brouillon', className: 'bg-gray-100 text-gray-800' },
  SUBMITTED: { label: 'Soumis', className: 'bg-yellow-100 text-yellow-800' },
  APPROVED: { label: 'Approuvé', className: 'bg-green-100 text-green-800' },
  REJECTED: { label: 'Rejeté', className: 'bg-red-100 text-red-800' },
};

export default function PlanningTachesList() {
  const [plannings, setPlannings] = useState<PlanningWithTasks[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlannings();
  }, []);

  const fetchPlannings = async () => {
    try {
      setLoading(true);
      const response = await client.apiCall.invoke({
        url: '/api/v1/plannings/all-with-taches',
        method: 'GET',
      });
      const data = response?.data || response;
      setPlannings(Array.isArray(data) ? data : (data?.items || []));
    } catch {
      toast({ title: 'Error', description: 'Failed to load task plannings', variant: 'destructive' });
    } finally {
      setLoading(false);
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
    return `${days} day${days === 1 ? '' : 's'}`;
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
        <h2 className="text-4xl font-bold text-white">Tâches de Planning</h2>
        <p className="mt-1 text-sm text-blue-300">View all planning task executions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-blue-300">No task plannings found</p>
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
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <List className="h-4 w-4 text-blue-400" />
                    <span className="text-blue-300">Tasks:</span>
                    <span className="font-medium">{planning.task_count}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-blue-400" />
                    <div>
                      <p className="text-blue-300">Period</p>
                      <p className="font-medium">
                        {new Date(planning.date_debut).toLocaleDateString('fr-FR')} - {new Date(planning.date_fin).toLocaleDateString('fr-FR')}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/cheftech/planning/${planning.id}/tasks`)}
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
    </div>
  );
}