import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Calendar, FileText, Play, CheckCircle, AlertTriangle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Intervention } from '@/lib/types';

export default function TechnicianInterventions() {
  const { toast } = useToast();
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [filteredInterventions, setFilteredInterventions] = useState<Intervention[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

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
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erreur lors du chargement');
      }
      const data = await res.json();
      setInterventions(data);
      setFilteredInterventions(data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (interventionId: number, statut: string) => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions/${interventionId}/status`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ statut }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Échec de la mise à jour');
      }
      toast({
        title: 'Succès',
        description: `Statut mis à jour: ${statut}`,
      });
      fetchData();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Échec de la mise à jour',
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
          <p className="mt-1 text-sm text-gray-500">Mettez à jour le statut en un clic</p>
        </div>
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

                <div className="flex flex-wrap gap-2">
                  {(intervention.statut || 'EN_ATTENTE') === 'EN_ATTENTE' && (
                    <Button size="sm" onClick={() => updateStatus(intervention.id, 'EN_COURS')}>
                      <Play className="mr-2 h-4 w-4" />
                      Démarrer
                    </Button>
                  )}
                  {(intervention.statut || 'EN_ATTENTE') === 'EN_COURS' && (
                    <Button size="sm" onClick={() => updateStatus(intervention.id, 'TERMINÉ')}>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      Terminer
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => updateStatus(intervention.id, 'BLOQUÉ')}
                  >
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    Bloquer
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