import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/hooks/use-toast';
import { PermissionButton } from '@/components/ui/PermissionButton';
import { PermissionGuard } from '@/components/ui/PermissionGuard';
import { usePermissions } from '@/hooks/usePermissions';
import { 
  Users, 
  Wrench, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Activity,
  Settings,
  UserCheck,
  AlertCircle
} from 'lucide-react';

interface Intervention {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  machine_id: number;
  machine_nom?: string;
  technicien_id?: number;
  technicien_nom?: string;
  date_debut?: string;
  date_fin?: string;
  created_at: string;
}

interface WorkOrder {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  machine_id: number;
  machine_nom?: string;
  utilisateur_id?: number;
  utilisateur_nom?: string;
  date_echeance?: string;
  created_at: string;
}

interface Technician {
  id: number;
  nom: string;
  email: string;
  role: string;
  created_at: string;
}

interface Machine {
  id: number;
  identifiant_machine: string;
  nom: string;
  emplacement: string;
  statut: string;
  type: string;
  date_derniere_maintenance?: string;
  date_prochaine_maintenance?: string;
  image_url?: string;
}

interface DashboardStats {
  total_interventions: number;
  interventions_en_cours: number;
  interventions_termines: number;
  interventions_urgents: number;
  total_ordres_travail: number;
  ordres_en_attente: number;
  ordres_en_cours: number;
  total_techniciens: number;
  techniciens_disponibles: number;
  total_machines: number;
  machines_critiques: number;
}

const CheftechDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTechnician, setSelectedTechnician] = useState<number | null>(null);
  const [selectedIntervention, setSelectedIntervention] = useState<number | null>(null);

  const getAuthToken = () => localStorage.getItem('access_token');

  const fetchDashboardData = async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        throw new Error('Token non trouvé');
      }

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Erreur lors du chargement des statistiques');
      }

      const data = await response.json();
      setStats(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les statistiques',
        variant: 'destructive',
      });
    }
  };

  const fetchInterventions = async (filters?: { statut?: string; priorite?: string; technicien_id?: number }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.priorite) params.append('priorite', filters.priorite);
      if (filters?.technicien_id) params.append('technicien_id', filters.technicien_id.toString());

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/interventions?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Erreur lors du chargement des interventions');
      const data = await response.json();
      setInterventions(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les interventions',
        variant: 'destructive',
      });
    }
  };

  const fetchWorkOrders = async (filters?: { statut?: string; priorite?: string }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.priorite) params.append('priorite', filters.priorite);

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/ordres-travail?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Erreur lors du chargement des ordres de travail');
      const data = await response.json();
      setWorkOrders(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les ordres de travail',
        variant: 'destructive',
      });
    }
  };

  const fetchTechnicians = async (disponible?: boolean) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (disponible !== undefined) params.append('disponible', disponible.toString());

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/techniciens?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Erreur lors du chargement des techniciens');
      const data = await response.json();
      setTechnicians(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les techniciens',
        variant: 'destructive',
      });
    }
  };

  const fetchMachines = async (filters?: { statut?: string; maintenance_required?: boolean }) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (filters?.statut) params.append('statut', filters.statut);
      if (filters?.maintenance_required !== undefined) params.append('maintenance_required', filters.maintenance_required.toString());

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/machines?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Erreur lors du chargement des machines');
      const data = await response.json();
      setMachines(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les machines',
        variant: 'destructive',
      });
    }
  };

  const assignTechnician = async (interventionId: number, technicianId: number) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/interventions/${interventionId}/assign`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ technicien_id: technicianId }),
      });

      if (!response.ok) throw new Error('Erreur lors de l\'assignation');
      
      toast({
        title: 'Succès',
        description: 'Technicien assigné avec succès',
      });

      fetchInterventions();
      fetchTechnicians();
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible d\'assigner le technicien',
        variant: 'destructive',
      });
    }
  };

  const updateMachineStatus = async (machineId: number, status: string) => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/cheftech/machines/${machineId}/status`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ statut: status }),
      });

      if (!response.ok) throw new Error('Erreur lors de la mise à jour');
      
      toast({
        title: 'Succès',
        description: 'Statut de la machine mis à jour',
      });

      fetchMachines();
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de mettre à jour le statut',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchDashboardData(),
        fetchInterventions(),
        fetchWorkOrders(),
        fetchTechnicians(),
        fetchMachines(),
      ]);
      setLoading(false);
    };

    loadData();
  }, []);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'URGENTE': return 'bg-red-100 text-red-800';
      case 'ÉLEVÉE': return 'bg-orange-100 text-orange-800';
      case 'MOYENNE': return 'bg-yellow-100 text-yellow-800';
      case 'BASSE': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'EN_COURS': return 'bg-blue-100 text-blue-800';
      case 'TERMINÉ': return 'bg-green-100 text-green-800';
      case 'EN_ATTENTE': return 'bg-yellow-100 text-yellow-800';
      case 'CRITIQUE': return 'bg-red-100 text-red-800';
      case 'MAINTENANCE': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Chef Technique Dashboard</h1>
          <p className="text-gray-600 mt-2">Supervision technique et gestion des équipes</p>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Interventions</p>
                    <p className="text-2xl font-bold">{stats.total_interventions}</p>
                    <p className="text-xs text-gray-500">{stats.interventions_en_cours} en cours</p>
                  </div>
                  <Wrench className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Ordres de travail</p>
                    <p className="text-2xl font-bold">{stats.total_ordres_travail}</p>
                    <p className="text-xs text-gray-500">{stats.ordres_en_attente} en attente</p>
                  </div>
                  <Activity className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Techniciens</p>
                    <p className="text-2xl font-bold">{stats.total_techniciens}</p>
                    <p className="text-xs text-gray-500">{stats.techniciens_disponibles} disponibles</p>
                  </div>
                  <Users className="h-8 w-8 text-purple-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Machines</p>
                    <p className="text-2xl font-bold">{stats.total_machines}</p>
                    <p className="text-xs text-gray-500">{stats.machines_critiques} critiques</p>
                  </div>
                  <Settings className="h-8 w-8 text-orange-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content Tabs */}
        <Tabs defaultValue="interventions" className="space-y-6">
          <TabsList>
            <TabsTrigger value="interventions">Interventions</TabsTrigger>
            <TabsTrigger value="ordres">Ordres de travail</TabsTrigger>
            <TabsTrigger value="techniciens">Techniciens</TabsTrigger>
            <TabsTrigger value="machines">Machines</TabsTrigger>
          </TabsList>

          {/* Interventions Tab */}
          <TabsContent value="interventions">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wrench className="h-5 w-5" />
                  Interventions
                </CardTitle>
                <div className="flex gap-4">
                  <Select onValueChange={(value) => fetchInterventions({ statut: value })}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="Filtrer par statut" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EN_ATTENTE">En attente</SelectItem>
                      <SelectItem value="EN_COURS">En cours</SelectItem>
                      <SelectItem value="TERMINÉ">Terminé</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select onValueChange={(value) => fetchInterventions({ priorite: value })}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="Filtrer par priorité" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="URGENTE">Urgente</SelectItem>
                      <SelectItem value="ÉLEVÉE">Élevée</SelectItem>
                      <SelectItem value="MOYENNE">Moyenne</SelectItem>
                      <SelectItem value="BASSE">Basse</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {interventions.map((intervention) => (
                    <div key={intervention.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold">{intervention.titre}</h3>
                          <p className="text-sm text-gray-600">{intervention.description}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge className={getPriorityColor(intervention.priorite)}>
                              {intervention.priorite}
                            </Badge>
                            <Badge className={getStatusColor(intervention.statut)}>
                              {intervention.statut}
                            </Badge>
                            {intervention.machine_nom && (
                              <span className="text-sm text-gray-500">
                                Machine: {intervention.machine_nom}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {intervention.technicien_nom ? (
                            <div className="text-sm">
                              <span className="font-medium">{intervention.technicien_nom}</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <Select
                                value={selectedIntervention === intervention.id ? selectedTechnician?.toString() : ""}
                                onValueChange={(value) => {
                                  setSelectedIntervention(intervention.id);
                                  setSelectedTechnician(parseInt(value));
                                }}
                              >
                                <SelectTrigger className="w-40">
                                  <SelectValue placeholder="Assigner" />
                                </SelectTrigger>
                                <SelectContent>
                                  {technicians.map((tech) => (
                                    <SelectItem key={tech.id} value={tech.id.toString()}>
                                      {tech.nom}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {selectedIntervention === intervention.id && selectedTechnician && (
                                <Button
                                  size="sm"
                                  onClick={() => {
                                    assignTechnician(intervention.id, selectedTechnician);
                                    setSelectedIntervention(null);
                                    setSelectedTechnician(null);
                                  }}
                                >
                                  <UserCheck className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Work Orders Tab */}
          <TabsContent value="ordres">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Ordres de travail
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workOrders.map((order) => (
                    <div key={order.id} className="border rounded-lg p-4">
                      <h3 className="font-semibold">{order.titre}</h3>
                      <p className="text-sm text-gray-600">{order.description}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge className={getPriorityColor(order.priorite)}>
                          {order.priorite}
                        </Badge>
                        <Badge className={getStatusColor(order.statut)}>
                          {order.statut}
                        </Badge>
                        {order.machine_nom && (
                          <span className="text-sm text-gray-500">
                            Machine: {order.machine_nom}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Technicians Tab */}
          <TabsContent value="techniciens">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Techniciens
                </CardTitle>
                <div className="flex gap-4">
                  <Button
                    variant="outline"
                    onClick={() => fetchTechnicians()}
                  >
                    Tous
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => fetchTechnicians(true)}
                  >
                    Disponibles
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {technicians.map((technician) => (
                    <div key={technician.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{technician.nom}</h3>
                          <p className="text-sm text-gray-600">{technician.email}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className="bg-green-100 text-green-800">
                            Disponible
                          </Badge>
                          <PermissionGuard permission="update" resource="users" fallback={
                            <Badge className="bg-gray-100 text-gray-600">
                              Non modifiable
                            </Badge>
                          }>
                            <Button size="sm" variant="outline">
                              Assigner
                            </Button>
                          </PermissionGuard>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Machines Tab */}
          <TabsContent value="machines">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Machines
                </CardTitle>
                <div className="flex gap-4">
                  <Button
                    variant="outline"
                    onClick={() => fetchMachines()}
                  >
                    Toutes
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => fetchMachines({ maintenance_required: true })}
                  >
                    Maintenance requise
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {machines.map((machine) => (
                    <div key={machine.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{machine.nom}</h3>
                          <p className="text-sm text-gray-600">
                            {machine.type} • {machine.emplacement}
                          </p>
                          {machine.date_prochaine_maintenance && (
                            <p className="text-xs text-gray-500">
                              Prochaine maintenance: {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getStatusColor(machine.statut)}>
                            {machine.statut}
                          </Badge>
                          <PermissionButton
                            permission="update"
                            resource="machines"
                            className="w-32"
                            variant="outline"
                          >
                            <Select
                              onValueChange={(value) => updateMachineStatus(machine.id, value)}
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue placeholder="Statut" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="ACTIF">Actif</SelectItem>
                                <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                                <SelectItem value="CRITIQUE">Critique</SelectItem>
                                <SelectItem value="HORS_SERVICE">Hors service</SelectItem>
                              </SelectContent>
                            </Select>
                          </PermissionButton>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default CheftechDashboard;
