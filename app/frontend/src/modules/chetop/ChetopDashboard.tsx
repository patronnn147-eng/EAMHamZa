import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/hooks/use-toast';
import { Plus, Edit, Eye, Settings, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';

interface WorkOrder {
  id: number;
  titre: string;
  description: string;
  priorite: string;
  statut: string;
  date_echeance?: string;
  created_at: string;
  machine_id: number;
  machine_nom?: string;
  utilisateur_id?: number;
  utilisateur_nom?: string;
}

interface Machine {
  id: number;
  nom: string;
  emplacement?: string;
  type?: string;
  statut?: string;
}

interface DashboardStats {
  total_ordres: number;
  ordres_en_attente: number;
  ordres_en_cours: number;
  ordres_termines: number;
  ordres_urgents: number;
  total_machines: number;
  machines_en_maintenance: number;
  machines_hors_service: number;
}

const ChetopDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    titre: '',
    description: '',
    priorite: 'MOYENNE',
    machine_id: 0,
    utilisateur_id: null,
    date_echeance: ''
  });

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

      // Fetch dashboard stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const statsData = await statsResponse.json();
      setStats(statsData);

      // Fetch work orders
      const ordersResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/ordres`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const ordersData = await ordersResponse.json();
      setWorkOrders(ordersData);

      // Fetch machines
      const machinesResponse = await fetch(`${API_BASE_URL}/api/v1/chetop/machines`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const machinesData = await machinesResponse.json();
      setMachines(machinesData);

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les données du tableau de bord',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.titre || !formData.description || !formData.machine_id) {
      toast({
        title: 'Erreur',
        description: 'Veuillez remplir tous les champs obligatoires',
        variant: 'destructive'
      });
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/api/v1/chetop/ordres`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Échec de la création');
      }

      const newOrder = await response.json();
      setWorkOrders([newOrder, ...workOrders]);
      setShowCreateModal(false);
      setFormData({
        titre: '',
        description: '',
        priorite: 'MOYENNE',
        machine_id: 0,
        utilisateur_id: null,
        date_echeance: ''
      });

      toast({
        title: 'Succès',
        description: 'Ordre de travail créé avec succès',
      });

      // Refresh stats
      fetchDashboardData();

    } catch (error) {
      console.error('Error creating work order:', error);
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Échec de la création',
        variant: 'destructive'
      });
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'URGENTE': return 'bg-red-500';
      case 'ÉLEVÉE': return 'bg-orange-500';
      case 'MOYENNE': return 'bg-yellow-500';
      case 'BASSE': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'EN_ATTENTE': return <Clock className="h-4 w-4" />;
      case 'EN_COURS': return <AlertCircle className="h-4 w-4" />;
      case 'TERMINÉ': return <CheckCircle className="h-4 w-4" />;
      case 'ANNULÉ': return <XCircle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'EN_ATTENTE': return 'text-yellow-600 bg-yellow-50';
      case 'EN_COURS': return 'text-blue-600 bg-blue-50';
      case 'TERMINÉ': return 'text-green-600 bg-green-50';
      case 'ANNULÉ': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Tableau de Bord - Chef des Opérations</h1>
          <Button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Nouvel Ordre de Travail
          </Button>
        </div>

        {/* Dashboard Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Total Ordres</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_ordres}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">En Attente</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">{stats.ordres_en_attente}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">En Cours</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{stats.ordres_en_cours}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Urgents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{stats.ordres_urgents}</div>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="ordres" className="space-y-6">
          <TabsList>
            <TabsTrigger value="ordres">Ordres de Travail</TabsTrigger>
            <TabsTrigger value="machines">Machines</TabsTrigger>
          </TabsList>

          <TabsContent value="ordres">
            <Card>
              <CardHeader>
                <CardTitle>Ordres de Travail</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workOrders.map((order) => (
                    <div key={order.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold">{order.titre}</h3>
                            <Badge className={getPriorityColor(order.priorite)}>
                              {order.priorite}
                            </Badge>
                            <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${getStatusColor(order.statut)}`}>
                              {getStatusIcon(order.statut)}
                              <span>{order.statut.replace('_', ' ')}</span>
                            </div>
                          </div>
                          <p className="text-gray-600 text-sm mb-2">{order.description}</p>
                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>Machine: {order.machine_nom || `ID: ${order.machine_id}`}</span>
                            {order.utilisateur_nom && <span>Assigné à: {order.utilisateur_nom}</span>}
                            <span>Créé: {new Date(order.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => setSelectedOrder(order)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Edit className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="machines">
            <Card>
              <CardHeader>
                <CardTitle>Machines</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {machines.map((machine) => (
                    <div key={machine.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-semibold">{machine.nom}</h3>
                        {machine.statut && (
                          <Badge variant={machine.statut === 'hors_service' ? 'destructive' : 'secondary'}>
                            {machine.statut.replace('_', ' ')}
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        {machine.type && <p>Type: {machine.type}</p>}
                        {machine.emplacement && <p>Emplacement: {machine.emplacement}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Create Order Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <CardTitle>Nouvel Ordre de Travail</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateOrder} className="space-y-4">
                  <div>
                    <Label htmlFor="titre">Titre *</Label>
                    <Input
                      id="titre"
                      value={formData.titre}
                      onChange={(e) => setFormData({...formData, titre: e.target.value})}
                      placeholder="Titre de l'ordre de travail"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="description">Description *</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      placeholder="Description détaillée du travail à effectuer"
                      rows={4}
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="priorite">Priorité</Label>
                      <Select value={formData.priorite} onValueChange={(value) => setFormData({...formData, priorite: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="BASSE">Basse</SelectItem>
                          <SelectItem value="MOYENNE">Moyenne</SelectItem>
                          <SelectItem value="ÉLEVÉE">Élevée</SelectItem>
                          <SelectItem value="URGENTE">Urgente</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="machine">Machine *</Label>
                      <Select value={formData.machine_id.toString()} onValueChange={(value) => setFormData({...formData, machine_id: parseInt(value)})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionner une machine" />
                        </SelectTrigger>
                        <SelectContent>
                          {machines.map((machine) => (
                            <SelectItem key={machine.id} value={machine.id.toString()}>
                              {machine.nom}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                      Annuler
                    </Button>
                    <Button type="submit">
                      Créer l'Ordre
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChetopDashboard;
