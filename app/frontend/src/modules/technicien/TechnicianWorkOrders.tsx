import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, Calendar, AlertTriangle, CheckCircle, Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import type { Intervention, OrdreTravail, Machine } from '@/lib/types';

export default function TechnicianWorkOrders() {
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<OrdreTravail[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let filtered = workOrders;

    if (statusFilter !== 'ALL') {
      filtered = filtered.filter((o) => o.statut === statusFilter);
    }

    if (searchTerm) {
      filtered = filtered.filter(
        (o) =>
          o.id.toString().includes(searchTerm) ||
          machines.find((m) => m.id === o.machine_id)?.nom.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredOrders(filtered);
  }, [searchTerm, statusFilter, workOrders, machines]);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const interventionsRes = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!interventionsRes.ok) throw new Error('Erreur lors du chargement des interventions');
      const interventions: Intervention[] = await interventionsRes.json();

      const ordreIds = Array.from(new Set(interventions.map((i) => i.ordre_travail_id)));
      const workOrdersList = (
        await Promise.all(
          ordreIds.map(async (id) => {
            const res = await client.entities.ordres_travail.get({ id: id.toString() });
            return res.data;
          }),
        )
      ).filter(Boolean);

      const machinesResponse = await client.entities.machines.queryAll({ query: {}, limit: 100 });
      const machinesList = machinesResponse.data.items || [];

      // Fetch work orders assigned directly to the user
      let directWorkOrders: OrdreTravail[] = [];
      if (user?.id) {
        const directWOsRes = await client.entities.ordres_travail.queryAll({
          query: JSON.stringify({ utilisateur_id: parseInt(user.id, 10) }),
          limit: 100,
        });
        directWorkOrders = directWOsRes.data.items || [];
      }

      // Merge and deduplicate
      const allWorkOrders = [...workOrdersList];
      directWorkOrders.forEach((wo) => {
        if (!allWorkOrders.find((existing) => existing.id === wo.id)) {
          allWorkOrders.push(wo);
        }
      });

      setWorkOrders(allWorkOrders);
      setMachines(machinesList);
      setFilteredOrders(allWorkOrders);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (ordreId: number, newStatus: string) => {
    try {
      await client.entities.ordres_travail.update({
        id: ordreId.toString(),
        data: { statut: newStatus },
      });

      toast({
        title: 'Succès',
        description: `Statut mis à jour: ${newStatus}`,
      });

      fetchData();
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data
          ?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;
      toast({
        title: 'Erreur',
        description: detail || 'Échec de la mise à jour du statut',
        variant: 'destructive',
      });
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
      case 'ASSIGNÉ':
        return 'bg-purple-100 text-purple-800';
      case 'TERMINÉ':
        return 'bg-green-100 text-green-800';
      case 'BLOQUÉ':
        return 'bg-red-100 text-red-800';
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
        <h2 className="text-3xl font-bold text-gray-900">Mes Ordres de Travail</h2>
        <p className="mt-1 text-sm text-gray-500">Gérez vos interventions assignées</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Rechercher par ID ou machine..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filtrer par statut" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Tous les statuts</SelectItem>
            <SelectItem value="EN_ATTENTE">En Attente</SelectItem>
            <SelectItem value="ASSIGNÉ">Assigné</SelectItem>
            <SelectItem value="EN_COURS">En Cours</SelectItem>
            <SelectItem value="TERMINÉ">Terminé</SelectItem>
            <SelectItem value="BLOQUÉ">Bloqué</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Work Orders List */}
      <div className="grid grid-cols-1 gap-4">
        {filteredOrders.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">Aucun ordre de travail trouvé</p>
            </CardContent>
          </Card>
        ) : (
          filteredOrders.map((ordre) => {
            const machine = getMachineInfo(ordre.machine_id);
            return (
              <Card
                key={ordre.id}
                className={`hover:shadow-md transition-shadow ${ordre.priorite === 'URGENTE' ? 'border-l-4 border-l-red-500' : ''
                  }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg flex items-center gap-2">
                        Ordre de Travail #{ordre.id}
                        <Badge className={getPriorityColor(ordre.priorite)}>{ordre.priorite}</Badge>
                        <Badge className={getStatusColor(ordre.statut)}>{ordre.statut}</Badge>
                      </CardTitle>
                      {machine && (
                        <p className="text-sm text-gray-500 mt-1">
                          Machine: {machine.nom} (#{machine.id}) - {machine.emplacement}
                        </p>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        Échéance: {new Date(ordre.date_echeance).toLocaleDateString()}
                      </span>
                      {ordre.priorite === 'URGENTE' && (
                        <span className="flex items-center gap-1 text-red-600">
                          <AlertTriangle className="h-4 w-4" />
                          Intervention Urgente
                        </span>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => navigate(`/technician/work-orders/${ordre.id}`)}
                      >
                        Voir Détails
                      </Button>
                      {ordre.statut === 'EN_ATTENTE' && (
                        <Button
                          size="sm"
                          className="flex-1 bg-blue-600 hover:bg-blue-700"
                          onClick={() => handleStatusChange(ordre.id, 'EN_COURS')}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Démarrer
                        </Button>
                      )}
                      {ordre.statut === 'EN_COURS' && (
                        <Button
                          size="sm"
                          className="flex-1 bg-green-600 hover:bg-green-700"
                          onClick={() => handleStatusChange(ordre.id, 'TERMINÉ')}
                        >
                          <CheckCircle className="mr-2 h-4 w-4" />
                          Terminer
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}