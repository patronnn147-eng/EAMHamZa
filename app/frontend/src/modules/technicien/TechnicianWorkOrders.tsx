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
  StopCircle,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { TechnicianNewInterventionModal } from '@/modules/technicien/components/TechnicianNewInterventionModal';
import { WorkOrderCompleteDialog, WorkOrderCompletePayload } from '@/modules/technicien/components/WorkOrderCompleteDialog';
import { WorkOrderTechnicien } from '../../lib/types';

const PRIORITY_ORDER: Record<string, number> = { URGENTE: 0, 'ÉLEVÉE': 1, MOYENNE: 2, BASSE: 3 };

function sortWorkOrders(items: WorkOrderTechnicien[]): WorkOrderTechnicien[] {
  return [...items].sort((a, b) => {
    const pa = PRIORITY_ORDER[a.priorite] ?? 4;
    const pb = PRIORITY_ORDER[b.priorite] ?? 4;
    if (pa !== pb) return pa - pb;
    if (!a.date_echeance && !b.date_echeance) return 0;
    if (!a.date_echeance) return 1;
    if (!b.date_echeance) return -1;
    return new Date(a.date_echeance).getTime() - new Date(b.date_echeance).getTime();
  });
}

function getDueDateInfo(date_echeance?: string): { label: string; colorClass: string; badge: string | null } | null {
  if (!date_echeance) return null;
  const due = new Date(date_echeance);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  const label = 'Échéance : ' + due.toLocaleDateString('fr-FR');
  if (diffMs < 0) return { label, colorClass: 'text-red-400', badge: 'EN RETARD' };
  if (diffDays <= 2) return { label, colorClass: 'text-amber-400', badge: 'URGENT' };
  return { label, colorClass: 'text-blue-300', badge: null };
}

const TechnicianWorkOrders: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [workOrders, setWorkOrders] = useState<WorkOrderTechnicien[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestOpen, setRequestOpen] = useState(false);
  const [selectedWoId] = useState<number | null>(null);
  const [completeModalOpen, setCompleteModalOpen] = useState(false);
  const [completingWoId, setCompletingWoId] = useState<number | null>(null);

  const fetchWorkOrders = async () => {
    setError(null);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/technicien/work-orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        let items: WorkOrderTechnicien[] = [];
        // Handle both paginated response and array response
        if (data && typeof data === 'object' && 'items' in data) {
          items = data.items || [];
        } else if (Array.isArray(data)) {
          items = data;
        }
        setWorkOrders(sortWorkOrders(items));
      } else {
        const text = await response.text();
        console.error('Failed to fetch work orders:', text);
        setError('Impossible de charger les ordres de travail.');
        setWorkOrders([]);
      }
    } catch (err) {
      console.error('Error fetching work orders:', err);
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
      setWorkOrders([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkOrders();
  }, []);

  const getStatusBadge = (statut: string) => {
    const base = "rounded-full px-4 py-1.5 text-[11px] font-black uppercase tracking-widest border transition-all duration-300 ";
    switch (statut) {
      case 'EN_ATTENTE':
      case 'ASSIGNÉ':
      case 'ASSIGNED':
        return <Badge className={base + "text-amber-700 bg-amber-50/50 border-amber-200/50"}><Clock className="w-3 h-3 mr-1" />En attente</Badge>;
      case 'EN_COURS':
      case 'IN_PROGRESS':
        return <Badge className={base + "text-blue-700 bg-blue-50/50 border-blue-200/50 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.2)]"}><Play className="w-3 h-3 mr-1" />En cours</Badge>;
      case 'TERMINE':
      case 'TERMINÉ':
      case 'COMPLETED':
        return <Badge className={base + "text-emerald-800 bg-emerald-100/50 border-emerald-300/50"}><CheckCircle2 className="w-3 h-3 mr-1" />Terminé</Badge>;
      default:
        return <Badge className={base + "text-blue-200 bg-slate-800/50 border-blue-700/50"}>{statut}</Badge>;
    }
  };

  const getPriorityBadge = (priorite: string) => {
    switch (priorite) {
      case 'URGENTE': return <Badge className="bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-[0_2px_8px_rgba(225,29,72,0.3)] border-none px-3 py-1">URGENTE</Badge>;
      case 'ÉLEVÉE': return <Badge className="bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-[0_2px_8px_rgba(245,158,11,0.3)] border-none px-3 py-1">ÉLEVÉE</Badge>;
      case 'MOYENNE': return <Badge className="bg-gradient-to-r from-yellow-400 to-orange-400 text-white border-none px-3 py-1">MOYENNE</Badge>;
      default: return <Badge className="bg-gray-200 text-blue-100 font-bold px-3 py-1">{priorite}</Badge>;
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
          <h1 className="text-3xl font-black text-white dark:text-white tracking-tight">
            Mes Ordres de Travail
          </h1>
          <p className="text-blue-300 font-medium mt-1">
            Ordres de travail qui vous sont assignés
          </p>
        </div>

        {error && (
          <div className="bg-red-600/90 text-white rounded-xl px-5 py-3 text-sm font-semibold shadow-lg">
            {error}
          </div>
        )}

        {workOrders.length === 0 ? (
          <Card className="bg-slate-800/80 backdrop-blur-md border border-blue-800/30 shadow-xl">
            <CardContent className="flex flex-col items-center justify-center py-20 text-center">
              <ClipboardList className="w-16 h-16 text-blue-400/50 mb-4" />
              <h3 className="text-xl font-bold text-blue-200 mb-2">Aucun ordre de travail</h3>
              <p className="text-blue-400 max-w-sm">
                Vos ordres de travail apparaîtront ici une fois qu'ils vous seront assignés.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {workOrders.map((wo) => (
              <Card key={wo.id} className="bg-slate-800/80 backdrop-blur-md border border-blue-800/30 shadow-lg hover:shadow-xl hover:border-blue-700/50 transition-all duration-200">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <h3 className="text-lg font-bold text-white truncate">{wo.titre}</h3>
                        {getStatusBadge(wo.statut)}
                        {getPriorityBadge(wo.priorite)}
                        {wo.source === 'ML_ALERT' && (
                          <Badge className="bg-purple-600 text-white border-none px-2 py-0.5 text-[10px] font-black tracking-widest">IA</Badge>
                        )}
                      </div>
                      {wo.description && (
                        <p className="text-sm text-blue-300 line-clamp-2 mb-3">{wo.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-blue-400 font-medium">
                        <span>Machine: <span className="text-blue-200 font-bold">{wo.machine_nom || `#${wo.machine_id}`}</span></span>
                        <span>Créé le: <span className="text-blue-200">{new Date(wo.created_at).toLocaleDateString('fr-FR')}</span></span>
                        <span>OT #{wo.id}</span>
                      </div>
                      {(() => {
                        const due = getDueDateInfo(wo.date_echeance);
                        if (!due) return null;
                        return (
                          <div className={`flex items-center gap-2 mt-1 text-xs font-semibold ${due.colorClass}`}>
                            <span>{due.label}</span>
                            {due.badge && (
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-black tracking-widest ${due.badge === 'EN RETARD' ? 'bg-red-600/80 text-white' : 'bg-amber-500/80 text-white'}`}>
                                {due.badge}
                              </span>
                            )}
                          </div>
                        );
                      })()}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl border-blue-700/50 font-bold bg-slate-800/50 text-blue-100 hover:bg-blue-800/40 hover:text-white"
                        onClick={() => navigate(`/technician/work-orders/${wo.id}`)}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Voir
                      </Button>
                      {(wo.statut === 'EN_ATTENTE' || wo.statut === 'ASSIGNÉ' || wo.statut === 'ASSIGNED') && (
                        <Button
                          size="sm"
                          className="bg-gradient-premium hover:opacity-90 rounded-xl font-bold shadow-lg shadow-violet-500/20 transition-all border-none"
                          onClick={async () => {
                            try {
                              const token = localStorage.getItem('access_token');
                              const apiBase = import.meta.env.VITE_API_BASE_URL || '';
                              const response = await fetch(`${apiBase}/api/v1/technicien/work-orders/${wo.id}/start`, {
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
                            }
                          }}
                        >
                          <Play className="w-4 h-4 mr-1" />
                          Commencer
                        </Button>
                      )}
                      {(wo.statut === 'EN_COURS' || wo.statut === 'IN_PROGRESS') && (
                        <Button
                          size="sm"
                          className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl font-bold shadow-lg shadow-green-500/20 transition-all border-none"
                          onClick={() => {
                            setCompletingWoId(wo.id);
                            setCompleteModalOpen(true);
                          }}
                        >
                          <StopCircle className="w-4 h-4 mr-1" />
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
      </div>

      <TechnicianNewInterventionModal
        open={requestOpen}
        onOpenChange={setRequestOpen}
        initialOrdreTravailId={selectedWoId}
        onSuccess={() => {
          fetchWorkOrders();
          toast({ title: 'Demande envoyée', description: 'Votre demande a été enregistrée avec succès.' });
        }}
      />

      {completingWoId && (
        <WorkOrderCompleteDialog
          open={completeModalOpen}
          onOpenChange={setCompleteModalOpen}
          workOrderId={completingWoId}
          workOrderTitle={workOrders.find(w => w.id === completingWoId)?.titre || ''}
          machineName={workOrders.find(w => w.id === completingWoId)?.machine_nom}
          machineId={workOrders.find(w => w.id === completingWoId)?.machine_id ?? null}
          onConfirm={async (data: WorkOrderCompletePayload) => {
            try {
              const token = localStorage.getItem('access_token');
              const apiBase = import.meta.env.VITE_API_BASE_URL || '';
              const response = await fetch(`${apiBase}/api/v1/technicien/work-orders/${completingWoId}/complete`, {
                method: 'PATCH',
                headers: {
                  Authorization: `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
              });
              if (response.ok) {
                toast({ title: 'Succès', description: 'Ordre de travail terminé avec succès!' });
                setCompleteModalOpen(false);
                setCompletingWoId(null);
                fetchWorkOrders();
              } else {
                const err = await response.json();
                toast({ title: 'Erreur', description: err.detail || 'Impossible de terminer', variant: 'destructive' });
              }
            } catch {
              toast({ title: 'Erreur réseau', description: 'Veuillez réessayer', variant: 'destructive' });
            }
          }}
        />
      )}
    </div>
  );
};

export default TechnicianWorkOrders;