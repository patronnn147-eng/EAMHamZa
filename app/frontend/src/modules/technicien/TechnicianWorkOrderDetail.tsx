import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  Calendar,
  AlertTriangle,
  FileText,
  History,
  MessageSquare,
  Play,
  CheckCircle,
  Wrench,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { OrdreTravail, Machine, Intervention } from '@/lib/types';

export default function TechnicianWorkOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [ordre, setOrdre] = useState<OrdreTravail | null>(null);
  const [machine, setMachine] = useState<Machine | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchData();
    }
  }, [id]);

  const fetchData = async () => {
    try {
      const ordreResponse = await client.entities.ordres_travail.get({ id: id! });
      const ordreData = ordreResponse.data;
      setOrdre(ordreData);

      if (ordreData.machine_id) {
        const machineResponse = await client.entities.machines.get({ id: ordreData.machine_id.toString() });
        setMachine(machineResponse.data);

        // Fetch intervention history for this machine
        const interventionsResponse = await client.entities.ordres_intervention.queryAll({
          query: {},
          sort: '-date_intervention',
          limit: 50,
        });
        const allInterventions = interventionsResponse.data.items || [];
        // Filter interventions related to work orders for this machine
        const machineInterventions = allInterventions.filter((i) => {
          // This is a simplified filter - in production, you'd join through work orders
          return true; // Show all for now
        });
        setInterventions(machineInterventions);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les détails',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!ordre) return;

    try {
      await client.entities.ordres_travail.update({
        id: ordre.id.toString(),
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
        description: detail || 'Échec de la mise à jour',
        variant: 'destructive',
      });
    }
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

  if (!ordre) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Ordre de travail non trouvé</p>
        <Button onClick={() => navigate('/technician/work-orders')} className="mt-4">
          Retour à la liste
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/technician/work-orders')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour
        </Button>
        <div className="flex-1">
          <h2 className="text-3xl font-bold text-gray-900">Ordre de Travail #{ordre.id}</h2>
          <div className="flex items-center gap-2 mt-2">
            <Badge className={getPriorityColor(ordre.priorite)}>{ordre.priorite}</Badge>
            <Badge className={getStatusColor(ordre.statut)}>{ordre.statut}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          {ordre.statut === 'EN_ATTENTE' && (
            <Button onClick={() => handleStatusChange('EN_COURS')} className="bg-blue-600 hover:bg-blue-700">
              <Play className="mr-2 h-4 w-4" />
              Démarrer
            </Button>
          )}
          {ordre.statut === 'EN_COURS' && (
            <Button onClick={() => handleStatusChange('TERMINE')} className="bg-green-600 hover:bg-green-700">
              <CheckCircle className="mr-2 h-4 w-4" />
              Terminer
            </Button>
          )}
          <Button onClick={() => navigate(`/technician/interventions/new?ordre=${ordre.id}`)}>
            <Wrench className="mr-2 h-4 w-4" />
            Créer Intervention
          </Button>
        </div>
      </div>

      <Tabs defaultValue="details" className="w-full">
        <TabsList>
          <TabsTrigger value="details">Détails</TabsTrigger>
          <TabsTrigger value="machine">Machine</TabsTrigger>
          <TabsTrigger value="history">Historique</TabsTrigger>
          <TabsTrigger value="comments">Commentaires</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Informations de l'Ordre
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Date d'Échéance</p>
                  <p className="text-base flex items-center gap-2 mt-1">
                    <Calendar className="h-4 w-4" />
                    {new Date(ordre.date_echeance).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Priorité</p>
                  <p className="text-base mt-1">{ordre.priorite}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Statut</p>
                  <p className="text-base mt-1">{ordre.statut}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Date de Création</p>
                  <p className="text-base mt-1">{new Date(ordre.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              {ordre.priorite === 'URGENTE' && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2 text-red-800">
                    <AlertTriangle className="h-5 w-5" />
                    <p className="font-semibold">Intervention Urgente</p>
                  </div>
                  <p className="text-sm text-red-700 mt-1">Cette intervention nécessite une attention immédiate.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="machine" className="space-y-4">
          {machine && (
            <Card>
              <CardHeader>
                <CardTitle>Informations de la Machine</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Nom</p>
                    <p className="text-base mt-1">{machine.nom}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Identifiant</p>
                    <p className="text-base mt-1">{machine.identifiant_machine}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Type</p>
                    <p className="text-base mt-1">{machine.type}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Emplacement</p>
                    <p className="text-base mt-1">{machine.emplacement}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Statut</p>
                    <Badge>{machine.statut}</Badge>
                  </div>
                </div>
                <Separator />
                <div>
                  <Button variant="outline" onClick={() => navigate(`/technician/machines/${machine.id}`)}>
                    Voir Détails Complets
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Historique des Interventions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {interventions.length === 0 ? (
                <p className="text-center text-gray-500 py-8">Aucune intervention précédente</p>
              ) : (
                <div className="space-y-3">
                  {interventions.slice(0, 5).map((intervention) => (
                    <div key={intervention.id} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium">Intervention #{intervention.id}</p>
                        <p className="text-sm text-gray-500">
                          {new Date(intervention.date_intervention).toLocaleDateString()}
                        </p>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">{intervention.rapport}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="comments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Commentaires
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Textarea
                  placeholder="Ajouter un commentaire ou une observation..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={4}
                />
                <Button className="mt-2" disabled={!comment.trim()}>
                  Ajouter Commentaire
                </Button>
              </div>
              <Separator />
              <p className="text-sm text-gray-500 text-center py-4">Aucun commentaire pour le moment</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}