import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Eye, AlertTriangle } from 'lucide-react';
import { useDataSync } from '@/contexts/DataSyncContext';
import type { Machine } from '@/lib/types';
import MachineHealthBar from '@/modules/shared/machines/components/MachineHealthBar';
import { computeHealthScore } from '@/modules/shared/machines/utils/healthScore';

function getMachineStatusConfig(statut = '') {
  const map: Record<string, { label: string; dot: string }> = {
    OPERATIONNELLE: { label: 'Opérationnelle', dot: 'bg-emerald-500' },
    EN_MAINTENANCE: { label: 'En Maintenance', dot: 'bg-amber-500' },
    EN_PANNE: { label: 'En Panne', dot: 'bg-red-500 animate-pulse' },
    HORS_SERVICE: { label: 'Hors Service', dot: 'bg-gray-400' },
  };
  return map[statut] ?? { label: statut || 'Inconnu', dot: 'bg-gray-300' };
}

export default function ChetopMachines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const { subscribe } = useDataSync();
  const navigate = useNavigate();

  useEffect(() => { fetchMachines(); }, []);

  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (event.type === 'machine') fetchMachines();
    });
    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = machines.filter(
        (m) =>
          m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.emplacement || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.zone || '').toLowerCase().includes(searchTerm.toLowerCase())
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
          <p className="mt-1 text-sm text-gray-500">
            Vue d'ensemble des machines et de leur état de santé
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Rechercher par nom, zone, emplacement, ou type..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMachines.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">Aucune machine trouvée</p>
          </div>
        ) : (
          filteredMachines.map((machine) => {
            const statusConfig = getMachineStatusConfig(machine.statut);
            const health = computeHealthScore(machine);
            const isCritical = health.score < 60;

            return (
              <Card
                key={machine.id}
                className={`hover:shadow-xl transition-all duration-200 overflow-hidden ${isCritical ? 'ring-1 ring-red-200' : ''
                  }`}
              >
                <div className={`h-1 w-full bg-gradient-to-r ${health.colorClass}`} />

                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base truncate">{machine.nom}</CardTitle>
                      <p className="text-xs text-gray-400 mt-0.5">#{machine.id}</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`inline-block w-2 h-2 rounded-full ${statusConfig.dot}`} />
                      <span className="text-xs text-gray-500">{statusConfig.label}</span>
                      {isCritical && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <img
                    src={machine.image_url || 'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'}
                    alt={machine.nom}
                    className="w-full h-40 object-cover rounded-lg"
                  />
                  <div className="space-y-1.5 text-sm">
                    {machine.type && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Type</span>
                        <span className="font-medium text-gray-800">{machine.type}</span>
                      </div>
                    )}
                    {machine.emplacement && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Emplacement</span>
                        <span className="font-medium text-gray-800">{machine.emplacement}</span>
                      </div>
                    )}
                    {machine.date_prochaine_maintenance && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Prochaine maint.</span>
                        <span className={`font-medium ${new Date(machine.date_prochaine_maintenance) < new Date() ? 'text-red-600' : 'text-amber-600'}`}>
                          {new Date(machine.date_prochaine_maintenance).toLocaleDateString('fr-FR')}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="pt-1 border-t border-gray-50">
                    <MachineHealthBar health={health} compact />
                  </div>

                  <Button
                    variant="default"
                    size="sm"
                    className="w-full"
                    onClick={() => navigate(`/machines/${machine.id}`)}
                  >
                    <Eye className="mr-1.5 h-4 w-4" />
                    Voir les détails
                  </Button>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
