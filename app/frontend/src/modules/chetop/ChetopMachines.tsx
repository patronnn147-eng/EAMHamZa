import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine } from '@/lib/types';

export default function ChetopMachines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const { subscribe } = useDataSync();

  useEffect(() => {
    fetchMachines();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (event.type === 'machine') {
        fetchMachines();
      }
    });
    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = machines.filter(
        (m) =>
          m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.identifiant_machine.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.emplacement.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.type.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const fetchMachines = async () => {
    try {
      const response = await client.entities.machines.query({
        query: {},
        sort: '-created_at',
        limit: 100
      });
      const machinesList = response.data.items || [];
      setMachines(machinesList);
      setFilteredMachines(machinesList);
    } catch (error) {
      console.error('Error fetching machines:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (statut: string) => {
    const statusConfig = {
      EN_ATTENTE: { label: 'Pending', className: 'bg-yellow-100 text-yellow-800' },
      EN_COURS: { label: 'In Progress', className: 'bg-blue-100 text-blue-800' },
      TERMINE: { label: 'Completed', className: 'bg-green-100 text-green-800' },
      ANNULE: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
    };
    const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
    return <Badge className={config.className}>{config.label}</Badge>;
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
          <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
          <p className="mt-1 text-sm text-gray-500">
            View machine information and status
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search machines by name, ID, location, or type..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMachines.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No machines found</p>
          </div>
        ) : (
          filteredMachines.map((machine) => (
            <Card key={machine.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{machine.nom}</CardTitle>
                    <p className="text-sm text-gray-500 mt-1">{machine.identifiant_machine}</p>
                  </div>
                  {getStatusBadge(machine.statut)}
                </div>
              </CardHeader>
              <CardContent>
                <img
                  src={machine.image_url || 'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'}
                  alt={machine.nom}
                  className="w-full h-48 object-cover rounded-md mb-4"
                />
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Type:</span>
                    <span className="font-medium">{machine.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Location:</span>
                    <span className="font-medium">{machine.emplacement}</span>
                  </div>
                  {machine.date_derniere_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Last Maintenance:</span>
                      <span className="font-medium">
                        {new Date(machine.date_derniere_maintenance).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  {machine.date_prochaine_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Next Maintenance:</span>
                      <span className="font-medium text-orange-600">
                        {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
