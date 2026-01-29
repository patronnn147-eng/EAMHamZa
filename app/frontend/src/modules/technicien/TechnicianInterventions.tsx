import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, Plus, Calendar, FileText, Save } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Intervention, OrdreTravail } from '@/lib/types';

export default function TechnicianInterventions() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [filteredInterventions, setFilteredInterventions] = useState<Intervention[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  const [formData, setFormData] = useState({
    ordre_travail_id: '',
    date_intervention: new Date().toISOString().split('T')[0],
    diagnostic: '',
    actions_effectuees: '',
    pieces_remplacees: '',
    observations: '',
  });

  useEffect(() => {
    fetchData();
    const ordreId = searchParams.get('ordre');
    if (ordreId) {
      setFormData((prev) => ({ ...prev, ordre_travail_id: ordreId }));
      setDialogOpen(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = interventions.filter(
        (i) =>
          i.id.toString().includes(searchTerm) ||
          i.rapport.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredInterventions(filtered);
    } else {
      setFilteredInterventions(interventions);
    }
  }, [searchTerm, interventions]);

  const fetchData = async () => {
    try {
      const user = await client.auth.me();
      if (!user.data) return;

      const [interventionsResponse, workOrdersResponse] = await Promise.all([
        client.entities.ordres_intervention.queryAll({
          query: {},
          sort: '-date_intervention',
          limit: 100,
        }),
        client.entities.ordres_travail.query({
          query: { utilisateur_id: user.data.id },
          limit: 100,
        }),
      ]);

      const interventionsList = interventionsResponse.data.items || [];
      const workOrdersList = workOrdersResponse.data.items || [];

      setInterventions(interventionsList);
      setFilteredInterventions(interventionsList);
      setWorkOrders(workOrdersList);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      if (!formData.ordre_travail_id || !formData.date_intervention) {
        toast({
          title: 'Erreur de Validation',
          description: 'Veuillez remplir tous les champs requis',
          variant: 'destructive',
        });
        return;
      }

      const rapport = `DIAGNOSTIC:\n${formData.diagnostic}\n\nACTIONS EFFECTUÉES:\n${formData.actions_effectuees}\n\nPIÈCES REMPLACÉES:\n${formData.pieces_remplacees}\n\nOBSERVATIONS:\n${formData.observations}`;

      const submitData = {
        date_intervention: formData.date_intervention,
        rapport,
        ordre_travail_id: parseInt(formData.ordre_travail_id),
      };

      await client.entities.ordres_intervention.create({
        data: submitData,
      });

      toast({
        title: 'Succès',
        description: 'Intervention créée avec succès',
      });

      setDialogOpen(false);
      setFormData({
        ordre_travail_id: '',
        date_intervention: new Date().toISOString().split('T')[0],
        diagnostic: '',
        actions_effectuees: '',
        pieces_remplacees: '',
        observations: '',
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
        description: detail || 'Échec de la création de l\'intervention',
        variant: 'destructive',
      });
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Mes Interventions</h2>
          <p className="mt-1 text-sm text-gray-500">Documentez vos interventions de maintenance</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle Intervention
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Rechercher par ID ou contenu du rapport..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filteredInterventions.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">Aucune intervention trouvée</p>
            </CardContent>
          </Card>
        ) : (
          filteredInterventions.map((intervention) => (
            <Card key={intervention.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      Intervention #{intervention.id}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      Ordre de Travail #{intervention.ordre_travail_id}
                    </p>
                  </div>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(intervention.date_intervention).toLocaleDateString()}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Rapport:</h4>
                  <p className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded-md line-clamp-4">
                    {intervention.rapport}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/technician/interventions/${intervention.id}`)}
                >
                  Voir Détails
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Créer une Nouvelle Intervention</DialogTitle>
            <DialogDescription>Documentez votre intervention de maintenance</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="ordre_travail_id">Ordre de Travail *</Label>
              <Select
                value={formData.ordre_travail_id}
                onValueChange={(value) => setFormData({ ...formData, ordre_travail_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un ordre de travail" />
                </SelectTrigger>
                <SelectContent>
                  {workOrders.map((wo) => (
                    <SelectItem key={wo.id} value={wo.id.toString()}>
                      Ordre #{wo.id} - {wo.statut}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_intervention">Date d'Intervention *</Label>
              <Input
                id="date_intervention"
                type="date"
                value={formData.date_intervention}
                onChange={(e) => setFormData({ ...formData, date_intervention: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="diagnostic">Diagnostic</Label>
              <Textarea
                id="diagnostic"
                value={formData.diagnostic}
                onChange={(e) => setFormData({ ...formData, diagnostic: e.target.value })}
                placeholder="Décrivez le problème identifié..."
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="actions_effectuees">Actions Effectuées</Label>
              <Textarea
                id="actions_effectuees"
                value={formData.actions_effectuees}
                onChange={(e) => setFormData({ ...formData, actions_effectuees: e.target.value })}
                placeholder="Décrivez les actions réalisées..."
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="pieces_remplacees">Pièces Remplacées</Label>
              <Textarea
                id="pieces_remplacees"
                value={formData.pieces_remplacees}
                onChange={(e) => setFormData({ ...formData, pieces_remplacees: e.target.value })}
                placeholder="Listez les pièces remplacées..."
                rows={2}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="observations">Observations</Label>
              <Textarea
                id="observations"
                value={formData.observations}
                onChange={(e) => setFormData({ ...formData, observations: e.target.value })}
                placeholder="Observations et recommandations..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleSubmit}>
              <Save className="mr-2 h-4 w-4" />
              Créer Intervention
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}