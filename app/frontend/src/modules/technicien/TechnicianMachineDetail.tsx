import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, MapPin, Wrench, History, FileText, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Machine, Intervention } from '@/lib/types';

export default function TechnicianMachineDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [machine, setMachine] = useState<Machine | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [newStatus, setNewStatus] = useState('');
  const [statusComment, setStatusComment] = useState('');

  useEffect(() => {
    if (id) {
      fetchData();
    }
  }, [id]);

  const fetchData = async () => {
    try {
      const machineResponse = await client.entities.machines.get({ id: id! });
      setMachine(machineResponse.data);

      // Fetch intervention history
      const interventionsResponse = await client.entities.ordres_intervention.queryAll({
        query: {},
        sort: '-date_intervention',
        limit: 50,
      });
      setInterventions(interventionsResponse.data.items || []);
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

  const handleStatusUpdate = async () => {
    if (!machine || !newStatus || !statusComment.trim()) {
      toast({
        title: 'Erreur',
        description: 'Veuillez remplir tous les champs',
        variant: 'destructive',
      });
      return;
    }

    try {
      await client.entities.machines.update({
        id: machine.id.toString(),
        data: { statut: newStatus },
      });

      toast({
        title: 'Succès',
        description: 'Statut de la machine mis à jour',
      });

      setStatusDialogOpen(false);
      setNewStatus('');
      setStatusComment('');
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

  if (!machine) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Machine non trouvée</p>
        <Button onClick={() => navigate('/technician/machines')} className="mt-4">
          Retour à la liste
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/technician/machines')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour
        </Button>
        <div className="flex-1">
          <h2 className="text-3xl font-bold text-gray-900">{machine.nom}</h2>
          <p className="text-sm text-gray-500 mt-1">{machine.identifiant_machine}</p>
        </div>
        <Badge className={getStatusColor(machine.statut)}>{machine.statut}</Badge>
        <Button onClick={() => setStatusDialogOpen(true)}>
          <AlertCircle className="mr-2 h-4 w-4" />
          Changer Statut
        </Button>
      </div>

      <Tabs defaultValue="details" className="w-full">
        <TabsList>
          <TabsTrigger value="details">Détails</TabsTrigger>
          <TabsTrigger value="history">Historique</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Informations Techniques</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Identifiant</p>
                  <p className="text-base mt-1">{machine.identifiant_machine}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Type</p>
                  <p className="text-base mt-1 flex items-center gap-2">
                    <Wrench className="h-4 w-4" />
                    {machine.type}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Emplacement</p>
                  <p className="text-base mt-1 flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {machine.emplacement}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Statut</p>
                  <Badge className={`${getStatusColor(machine.statut)} mt-1`}>{machine.statut}</Badge>
                </div>
                {machine.date_derniere_maintenance && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Dernière Maintenance</p>
                    <p className="text-base mt-1">
                      {new Date(machine.date_derniere_maintenance).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {machine.date_prochaine_maintenance && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Prochaine Maintenance</p>
                    <p className="text-base mt-1">
                      {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Historique de Maintenance
              </CardTitle>
            </CardHeader>
            <CardContent>
              {interventions.length === 0 ? (
                <p className="text-center text-gray-500 py-8">Aucune intervention enregistrée</p>
              ) : (
                <div className="space-y-3">
                  {interventions.map((intervention) => (
                    <div key={intervention.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-blue-600" />
                          <p className="font-medium">Intervention #{intervention.id}</p>
                        </div>
                        <p className="text-sm text-gray-500">
                          {new Date(intervention.date_intervention).toLocaleDateString()}
                        </p>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-3 whitespace-pre-wrap">
                        {intervention.rapport}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Status Update Dialog */}
      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Changer le Statut de la Machine</DialogTitle>
            <DialogDescription>
              Mettez à jour le statut de {machine.nom} avec une justification
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="status">Nouveau Statut *</Label>
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="OPERATIONNELLE">Opérationnelle</SelectItem>
                  <SelectItem value="EN_MAINTENANCE">En Maintenance</SelectItem>
                  <SelectItem value="EN_PANNE">En Panne</SelectItem>
                  <SelectItem value="HORS_SERVICE">Hors Service</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="comment">Commentaire de Justification *</Label>
              <Textarea
                id="comment"
                value={statusComment}
                onChange={(e) => setStatusComment(e.target.value)}
                placeholder="Expliquez la raison du changement de statut..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusDialogOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleStatusUpdate}>Mettre à Jour</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}