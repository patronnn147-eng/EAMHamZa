import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, MapPin, Wrench } from 'lucide-react';
import type { Machine } from '@/lib/types';

export default function TechnicianMachines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = machines.filter(
        (m) =>
          m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.identifiant_machine.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.emplacement.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const fetchData = async () => {
    try {
      const response = await client.entities.machines.queryAll({
        query: {},
        sort: 'nom',
        limit: 100,
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

  const getStatusColor = (statut: string) => {
    switch (statut) {
      case 'OPERATIONNELLE':
        return 'bg-green-100 text-green-800';
      case 'EN_MAINTENANCE':
        return 'bg-yellow-100 text-yellow-800';
      case 'EN_PANNE':
        return 'bg-red-100 text-red-800';
      case 'HORS_SERVICE':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
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
        <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
        <p className="mt-1 text-sm text-gray-500">Consultez les informations des équipements</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Rechercher par nom, identifiant ou emplacement..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredMachines.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="text-center py-12">
              <p className="text-gray-500">Aucune machine trouvée</p>
            </CardContent>
          </Card>
        ) : (
          filteredMachines.map((machine) => (
            <Card key={machine.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{machine.nom}</CardTitle>
                    <p className="text-sm text-gray-500 mt-1">{machine.identifiant_machine}</p>
                  </div>
                  <Badge className={getStatusColor(machine.statut)}>{machine.statut}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <MapPin className="h-4 w-4" />
                    <span>{machine.emplacement}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Wrench className="h-4 w-4" />
                    <span>{machine.type}</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => navigate(`/technician/machines/${machine.id}`)}
                  >
                    Voir Détails
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