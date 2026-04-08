import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  ClipboardList,
  Eye,
  Play,
  CheckCircle2,
  Clock,
  Loader2,
  Flag,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { AppPagination } from '@/components/shared/AppPagination';

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
  const [completingId, setCompletingId] = useState<number | null>(null);
  const [completeModalOpen, setCompleteModalOpen] = useState(false);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [rapport, setRapport] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(10);

  const fetchWorkOrders = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/work-orders?page=${page}&size=${pageSize}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setWorkOrders(data.items || []);
        setTotalPages(data.total_pages || 1);
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
  }, [page]);

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

  const openCompleteModal = (orderId: number) => {
    setSelectedOrderId(orderId);
    setRapport('');
    setCompleteModalOpen(true);
  };

  const handleComplete = async () => {
    if (!selectedOrderId || !rapport.trim()) return;
    setCompletingId(selectedOrderId);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/work-orders/${selectedOrderId}/complete`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ rapport }),
      });
      if (response.ok) {
        toast({ title: 'Succès', description: "L'intervention a été clôturée" });
        setCompleteModalOpen(false);
        fetchWorkOrders();
      } else {
        const err = await response.json();
        toast({ title: 'Erreur', description: err.detail || 'Impossible de terminer', variant: 'destructive' });
      }
    } catch {
      toast({ title: 'Erreur réseau', description: 'Veuillez réessayer', variant: 'destructive' });
    } finally {
      setCompletingId(null);
    }
  };

  const getStatusBadge = (statut: string) => {
    switch (statut) {
      case 'ASSIGNÉ':
      case 'EN_ATTENTE':
        return <Badge className="bg-amber-500/10 text-amber-600 border-amber-300"><Clock className="w-3 h-3 mr-1" />En attente</Badge>;
      case 'EN_COURS':
        return <Badge className="bg-blue-500/10 text-blue-600 border-blue-300"><Play className="w-3 h-3 mr-1" />En cours</Badge>;
      case 'TERMINE':
      case 'TERMINÉ':
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
                      {(wo.statut === 'ASSIGNÉ' || wo.statut === 'EN_ATTENTE') && (
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
                      {wo.statut === 'EN_COURS' && (
                        <Button
                          size="sm"
                          className="bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold shadow-md shadow-violet-500/20"
                          onClick={() => openCompleteModal(wo.id)}
                          disabled={completingId === wo.id}
                        >
                          {completingId === wo.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <Flag className="w-4 h-4 mr-1" />
                          )}
                          Terminer
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <div className="flex justify-end mt-4">
          <AppPagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
      </div>

      <Dialog open={completeModalOpen} onOpenChange={setCompleteModalOpen}>
        <DialogContent className="sm:max-w-[480px] rounded-[2rem] border-none shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-xl font-black tracking-tight flex items-center gap-2">
              <Flag className="h-5 w-5 text-violet-500" />
              Clôturer l'intervention
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="font-bold text-sm">Rapport de clôture *</Label>
              <Textarea
                placeholder="Décrivez les actions effectuées, le résultat et l'état final de la machine..."
                value={rapport}
                onChange={(e) => setRapport(e.target.value)}
                className="min-h-[120px] rounded-xl border-gray-200"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="ghost" onClick={() => setCompleteModalOpen(false)} className="rounded-xl font-bold">
              Annuler
            </Button>
            <Button
              onClick={handleComplete}
              disabled={!rapport.trim() || completingId !== null}
              className="bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-black px-8"
            >
              {completingId !== null ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Confirmer la clôture
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ChefOpWorkOrders;
