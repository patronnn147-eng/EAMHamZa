import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  ClipboardList,
  Eye,
  Play,
  CheckCircle2,
  Clock,
  Loader2,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface WorkOrder {
  id: number;
  titre: string;
  description?: string;
  priorite: string;
  statut: string;
  machine_id: number;
  machine_nom?: string;
  created_at: string;
}

const ChefOpWorkOrders: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState<number | null>(null);

  const fetchWorkOrders = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/work-orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setWorkOrders(data);
      } else {
        console.error('Failed to fetch work orders:', await response.text());
      }
    } catch (error) {
      console.error('Error fetching work orders:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkOrders();
  }, []);

  const handleStart = async (orderId: number) => {
    setStartingId(orderId);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/work-orders/${orderId}/start`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        toast({ title: 'Succès', description: "L'intervention a commencé" });
        fetchWorkOrders();
      } else {
        const err = await response.json();
        toast({ title: 'Erreur', description: err.detail || 'Impossible de démarrer', variant: 'destructive' });
      }
    } catch {
      toast({ title: 'Erreur réseau', description: 'Veuillez réessayer', variant: 'destructive' });
    } finally {
      setStartingId(null);
    }
  };

  const getStatusBadge = (statut: string) => {
    switch (statut) {
      case 'EN_ATTENTE':
        return <Badge className="bg-amber-500/10 text-amber-600 border-amber-300"><Clock className="w-3 h-3 mr-1" />En attente</Badge>;
      case 'EN_COURS':
        return <Badge className="bg-blue-500/10 text-blue-600 border-blue-300"><Play className="w-3 h-3 mr-1" />En cours</Badge>;
      case 'TERMINE':
        return <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-300"><CheckCircle2 className="w-3 h-3 mr-1" />Terminé</Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  const getPriorityBadge = (priorite: string) => {
    switch (priorite) {
      case 'URGENTE': return <Badge variant="destructive">URGENTE</Badge>;
      case 'ÉLEVÉE': return <Badge className="bg-orange-500 text-white border-none">ÉLEVÉE</Badge>;
      case 'MOYENNE': return <Badge className="bg-yellow-500/10 text-yellow-700 border-yellow-300">MOYENNE</Badge>;
      default: return <Badge variant="secondary">{priorite}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="p-8 animate-premium-fade-in">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
            Mes Ordres de Travail
          </h1>
          <p className="text-gray-500 font-medium mt-1">
            Ordres générés suite à vos demandes approuvées
          </p>
        </div>

        {workOrders.length === 0 ? (
          <Card className="bg-white/70 backdrop-blur-md border border-white/20 shadow-xl">
            <CardContent className="flex flex-col items-center justify-center py-20 text-center">
              <ClipboardList className="w-16 h-16 text-gray-300 mb-4" />
              <h3 className="text-xl font-bold text-gray-600 mb-2">Aucun ordre de travail</h3>
              <p className="text-gray-400 max-w-sm">
                Vos ordres de travail apparaîtront ici une fois que vos demandes d'intervention auront été approuvées par l'administrateur.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {workOrders.map((wo) => (
              <Card key={wo.id} className="bg-white/70 backdrop-blur-md border border-white/20 shadow-lg hover:shadow-xl transition-all duration-200">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <h3 className="text-lg font-bold text-gray-900 truncate">{wo.titre}</h3>
                        {getStatusBadge(wo.statut)}
                        {getPriorityBadge(wo.priorite)}
                      </div>
                      {wo.description && (
                        <p className="text-sm text-gray-500 line-clamp-2 mb-3">{wo.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-400 font-medium">
                        <span>Machine: <span className="text-gray-600 font-bold">{wo.machine_nom || `#${wo.machine_id}`}</span></span>
                        <span>Créé le: <span className="text-gray-600">{new Date(wo.created_at).toLocaleDateString('fr-FR')}</span></span>
                        <span>OT #{wo.id}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl border-gray-200 font-bold"
                        onClick={() => navigate(`/chetop/work-orders/${wo.id}`)}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Voir
                      </Button>
                      {wo.statut === 'EN_ATTENTE' && (
                        <Button
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-md shadow-emerald-500/20"
                          onClick={() => handleStart(wo.id)}
                          disabled={startingId === wo.id}
                        >
                          {startingId === wo.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <Play className="w-4 h-4 mr-1" />
                          )}
                          Commencer
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChefOpWorkOrders;
