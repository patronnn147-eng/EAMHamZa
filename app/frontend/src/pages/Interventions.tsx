import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Plus, FileText } from 'lucide-react';
import type { OrdreIntervention, OrdreTravail } from '@/lib/types';

export default function Interventions() {
  const [interventions, setInterventions] = useState<OrdreIntervention[]>([]);
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [filteredInterventions, setFilteredInterventions] = useState<OrdreIntervention[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = interventions.filter((i) =>
        i.id.toString().includes(searchTerm) ||
        i.ordre_travail_id.toString().includes(searchTerm) ||
        (i.rapport && i.rapport.toLowerCase().includes(searchTerm.toLowerCase()))
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

  const getWorkOrderInfo = (workOrderId: number) => {
    const wo = workOrders.find((w) => w.id === workOrderId);
    return wo ? `Work Order #${wo.id}` : `Work Order #${workOrderId}`;
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
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Record Intervention
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search interventions by ID, work order, or report content..."
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
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {new Date(intervention.date_intervention).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(intervention.date_intervention).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {intervention.rapport ? (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Intervention Report:</p>
                    <p className="text-sm text-gray-600 whitespace-pre-wrap">
                      {intervention.rapport}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No report available</p>
                )}
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