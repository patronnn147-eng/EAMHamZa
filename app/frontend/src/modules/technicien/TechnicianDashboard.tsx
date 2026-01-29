import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, AlertTriangle, CheckCircle, Clock, Wrench } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { OrdreTravail, Machine } from '@/lib/types';

export default function TechnicianDashboard() {
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    enCours: 0,
    enAttente: 0,
    termine: 0,
    urgent: 0,
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const user = await client.auth.me();
      if (!user.data) return;

      // Fetch work orders assigned to current technician
      const [ordresResponse, machinesResponse] = await Promise.all([
        client.entities.ordres_travail.query({
          query: { utilisateur_id: user.data.id },
          sort: '-priorite,-date_echeance',
          limit: 100,
        }),
        client.entities.machines.queryAll({
          query: {},
          limit: 100,
        }),
      ]);

      const ordresList = ordresResponse.data.items || [];
      const machinesList = machinesResponse.data.items || [];

      setWorkOrders(ordresList);
      setMachines(machinesList);

      // Calculate stats
      const statsData = {
        total: ordresList.length,
        enCours: ordresList.filter((o) => o.statut === 'EN_COURS').length,
        enAttente: ordresList.filter((o) => o.statut === 'EN_ATTENTE').length,
        termine: ordresList.filter((o) => o.statut === 'TERMINE').length,
        urgent: ordresList.filter((o) => o.priorite === 'URGENTE').length,
      };
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMachineInfo = (machineId: number) => {
    return machines.find((m) => m.id === machineId);
  };

  const getPriorityColor = (priorite: string) => {
    switch (priorite) {
      case 'URGENTE':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'HAUTE':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'MOYENNE':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusColor = (statut: string) => {
    switch (statut) {
      case 'EN_COURS':
        return 'bg-blue-100 text-blue-800';
      case 'EN_ATTENTE':
        return 'bg-yellow-100 text-yellow-800';
      case 'TERMINE':
        return 'bg-green-100 text-green-800';
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
        <h2 className="text-3xl font-bold text-gray-900">Tableau de Bord Technicien</h2>
        <p className="mt-1 text-sm text-gray-500">Vue d'ensemble de vos tâches et interventions</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-gray-500">Ordres de travail</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">En Cours</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.enCours}</div>
            <p className="text-xs text-gray-500">Interventions actives</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">En Attente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats.enAttente}</div>
            <p className="text-xs text-gray-500">À démarrer</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Terminés</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.termine}</div>
            <p className="text-xs text-gray-500">Complétés</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Urgent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.urgent}</div>
            <p className="text-xs text-gray-500">Priorité haute</p>
          </CardContent>
        </Card>
      </div>

      {/* Work Orders List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Mes Ordres de Travail</CardTitle>
            <Button onClick={() => navigate('/technician/work-orders')}>Voir Tout</Button>
          </div>
        </CardHeader>
        <CardContent>
          {workOrders.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Wrench className="mx-auto h-12 w-12 mb-2 opacity-50" />
              <p>Aucun ordre de travail assigné</p>
            </div>
          ) : (
            <div className="space-y-3">
              {workOrders.slice(0, 5).map((ordre) => {
                const machine = getMachineInfo(ordre.machine_id);
                return (
                  <div
                    key={ordre.id}
                    className={`p-4 border rounded-lg hover:shadow-md transition-shadow cursor-pointer ${
                      ordre.priorite === 'URGENTE' ? 'border-red-300 bg-red-50' : 'border-gray-200'
                    }`}
                    onClick={() => navigate(`/technician/work-orders/${ordre.id}`)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-gray-900">Ordre #{ordre.id}</h3>
                          <Badge className={getPriorityColor(ordre.priorite)}>{ordre.priorite}</Badge>
                          <Badge className={getStatusColor(ordre.statut)}>{ordre.statut}</Badge>
                        </div>
                        {machine && (
                          <p className="text-sm text-gray-600 mb-1">
                            Machine: {machine.nom} ({machine.identifiant_machine})
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Échéance: {new Date(ordre.date_echeance).toLocaleDateString()}
                          </span>
                          {ordre.priorite === 'URGENTE' && (
                            <span className="flex items-center gap-1 text-red-600">
                              <AlertTriangle className="h-3 w-3" />
                              Urgent
                            </span>
                          )}
                        </div>
                      </div>
                      {ordre.statut === 'EN_COURS' && (
                        <Clock className="h-5 w-5 text-blue-600 animate-pulse" />
                      )}
                      {ordre.statut === 'TERMINE' && <CheckCircle className="h-5 w-5 text-green-600" />}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}