import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, MapPin, Wrench, Eye, AlertTriangle, Calendar, Gauge } from 'lucide-react';
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
          (m.emplacement || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.zone || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.sous_zone || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.type || '').toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/technicien/machines`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch machines');
      const machinesList = await response.json();
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-4xl font-bold text-white">Machines</h2>
          <p className="mt-1 text-sm text-blue-300">Consultez les informations des équipements</p>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-blue-400" />
          <Input
            type="text"
            placeholder="Rechercher par nom, emplacement, zone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-slate-800/80 border-blue-800/30 text-white placeholder:text-blue-400/50"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredMachines.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-blue-300">Aucune machine trouvée</p>
          </div>
        ) : (
          filteredMachines.map((machine) => {
            const statusConfig = getMachineStatusConfig(machine.statut);
            const health = computeHealthScore(machine);
            const isCritical = health.score < 60;

            return (
              <Card
                key={machine.id}
                className={`bg-gradient-to-br from-slate-800 to-blue-900 border-blue-700/50 hover:shadow-xl hover:shadow-blue-500/20 hover:border-blue-600 transition-all duration-300 overflow-hidden group ${isCritical ? 'ring-1 ring-red-500/50' : ''}`}
              >
                <div className={`h-1 w-full bg-gradient-to-r ${health.colorClass}`} />

                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base truncate text-white group-hover:text-blue-200 transition-colors">
                        {machine.nom}
                      </CardTitle>
                      {machine.ordre && (
                        <p className="text-xs text-blue-400 mt-0.5">Ordre: {machine.ordre}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`inline-block w-2 h-2 rounded-full ${statusConfig.dot}`} />
                      <span className="text-xs text-blue-300">{statusConfig.label}</span>
                      {isCritical && <AlertTriangle className="h-3.5 w-3.5 text-red-500 animate-pulse" />}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <div className="relative overflow-hidden rounded-lg">
                    <img
                      src={
                        machine.image_url ||
                        'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'
                      }
                      alt={machine.nom}
                      className="w-full h-36 object-cover transform group-hover:scale-105 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent" />
                  </div>

                  <div className="space-y-2.5 text-sm">
                    {machine.type && (
                      <div className="flex items-center gap-2">
                        <Wrench className="h-4 w-4 text-blue-400" />
                        <span className="text-blue-300">Type:</span>
                        <span className="font-medium text-white truncate">{machine.type}</span>
                      </div>
                    )}
                    
                    {machine.emplacement && (
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-blue-400" />
                        <span className="text-blue-300">Emplacement:</span>
                        <span className="font-medium text-white truncate">{machine.emplacement}</span>
                      </div>
                    )}

                    {(machine.zone || machine.sous_zone) && (
                      <div className="flex items-center gap-2">
                        <Gauge className="h-4 w-4 text-blue-400" />
                        <span className="text-blue-300">Zone:</span>
                        <span className="font-medium text-blue-100">
                          {[machine.zone, machine.sous_zone].filter(Boolean).join(' / ')}
                        </span>
                      </div>
                    )}

                    {machine.date_prochaine_maintenance && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-blue-400" />
                        <span className="text-blue-300">Prochaine maint.:</span>
                        <span className={`font-medium ${
                          new Date(machine.date_prochaine_maintenance) < new Date() 
                            ? 'text-red-400' 
                            : 'text-amber-400'
                        }`}>
                          {new Date(machine.date_prochaine_maintenance).toLocaleDateString('fr-FR')}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-blue-700/30">
                    <MachineHealthBar health={health} compact />
                  </div>

                  <Button
                    variant="default"
                    size="sm"
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white group-hover:bg-blue-500"
                    onClick={() => navigate(`/machines/${machine.id}`)}
                  >
                    <Eye className="mr-1.5 h-4 w-4" />
                    Voir Détails
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