import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Plus } from 'lucide-react';
import type { Planning } from '@/lib/types';

export default function PlanningPage() {
  const [plannings, setplannings] = useState<Planning[]>([]);
  const [loading, setLoading] = useState(true);

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
      setplannings(planningsList);
    } catch (error) {
      console.error('Error fetching plannings:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      JOURNALIER: { label: 'Daily', className: 'bg-blue-100 text-blue-800' },
      HEBDOMADAIRE: { label: 'Weekly', className: 'bg-green-100 text-green-800' },
      MENSUEL: { label: 'Monthly', className: 'bg-purple-100 text-purple-800' },
      MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.JOURNALIER;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const isActive = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    return now >= start && now <= end;
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
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Planning
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {plannings.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No planning schedules found</p>
          </div>
        ) : (
          plannings.map((planning) => (
            <Card key={planning.id} className={`hover:shadow-md transition-shadow ${isActive(planning.date_debut, planning.date_fin) ? 'border-blue-500 border-2' : ''}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Calendar className="h-5 w-5 text-blue-600" />
                      {planning.identifiant_planning}
                    </CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    {getTypeBadge(planning.type)}
                    {isActive(planning.date_debut, planning.date_fin) && (
                      <Badge className="bg-green-100 text-green-800">Active</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Start Date:</span>
                    <span className="font-medium">
                      {new Date(planning.date_debut).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">End Date:</span>
                    <span className="font-medium">
                      {new Date(planning.date_fin).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Duration:</span>
                    <span className="font-medium">
                      {Math.ceil((new Date(planning.date_fin).getTime() - new Date(planning.date_debut).getTime()) / (1000 * 60 * 60 * 24))} days
                    </span>
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <Button variant="outline" size="sm">
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