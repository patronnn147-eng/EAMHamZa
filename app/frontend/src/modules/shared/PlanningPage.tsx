import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Users, Eye } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';

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
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlannings();
  }, []);

  const fetchPlannings = async () => {
    try {
      const response = await client.apiCall.invoke({
        url: '/api/v1/plannings?skip=0&limit=100',
        method: 'GET',
      });
      setPlannings(response.data.items || []);
    } catch (error) {
      console.error('Error fetching plannings:', error);
      toast({
        title: 'Error',
        description: 'Failed to load plannings',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
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
          <h2 className="text-3xl font-bold text-gray-900">Planning Schedule</h2>
          <p className="mt-1 text-sm text-gray-500 flex items-center gap-2">
            <Eye className="h-4 w-4" />
            View work schedules and maintenance planning (Read-only)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No planning schedules available</p>
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
                <div className="space-y-3">
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
                        <p className="text-gray-500">Assigned Team</p>
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
                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/planning/${planning.id}`)}
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