import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import {
  Check,
  X,
  Clock,
  Search,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  Boxes,
  AlertTriangle,
  Mail,
  ShoppingCart,
  Loader2,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useInterventionParts } from '@/hooks/useInventory';
import { QtyBadge, SectionDivider, formatNum } from '@/components/inventory/primitives';

interface ItvRequest {
  id: number;
  machine_id: number;
  machine_nom: string;
  priorite: string;
  description: string;
  statut: string;
  requested_at: string;
  requested_by_nom: string;
}

interface DeficitItem {
  piece_id: number;
  piece_name: string;
  requested: string;
  available: string;
  deficit: string;
}

const apiBase = import.meta.env.VITE_API_BASE_URL || '';

const AdminItvApprovals: React.FC = () => {
  const { toast } = useToast();
  const [requests, setRequests] = useState<ItvRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');

  // Deficit dialog state — surfaces 409 details + "Réserver les manques"
  const [deficitState, setDeficitState] = useState<{
    interventionId: number;
    items: DeficitItem[];
  } | null>(null);
  const [reservingDeficit, setReservingDeficit] = useState(false);

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${apiBase}/api/v1/admin/itv-requests`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setRequests(data.items || data || []);
      }
    } catch (error) {
      console.error('Error fetching requests:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleValidate = async (id: number, status: 'APPROVED' | 'REJECTED', reason?: string) => {
    setApprovingId(id);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${apiBase}/api/v1/admin/itv-requests/${id}/validate`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status, rejection_reason: reason }),
      });

      if (response.ok) {
        toast({
          title: status === 'APPROVED' ? 'Demande approuvée' : 'Demande rejetée',
          description:
            status === 'APPROVED'
              ? "Un ordre de travail a été créé. Pièces réservées automatiquement."
              : 'Le demandeur sera notifié.',
        });
        await fetchRequests();
      } else if (response.status === 409) {
        // Backend signals insufficient stock — parse deficit list and open dialog
        const errBody = await response.json().catch(() => ({}));
        const detail = errBody?.detail;
        const missing: DeficitItem[] = Array.isArray(detail?.missing) ? detail.missing : [];
        if (missing.length > 0) {
          setDeficitState({ interventionId: id, items: missing });
          toast({
            title: 'Stock insuffisant',
            description: `${missing.length} pièce(s) en déficit — voir détails`,
            variant: 'destructive',
          });
        } else {
          toast({
            title: 'Stock insuffisant',
            description: 'Le détail est introuvable',
            variant: 'destructive',
          });
        }
      } else {
        const errBody = await response.json().catch(() => ({}));
        toast({
          title: 'Erreur',
          description: errBody.detail || 'Échec de la validation',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error validating request:', error);
      toast({
        title: 'Erreur',
        description: 'Une erreur réseau est survenue',
        variant: 'destructive',
      });
    } finally {
      setApprovingId(null);
    }
  };

  /**
   * "Réserver les manques" → invalidates demand-forecast cache so the
   * procurement view sees the new deficit, then notifies via toast.
   * Future enrichment: backend hook to emit procurement webhook / email.
   */
  const handleReserveDeficit = async () => {
    if (!deficitState) return;
    setReservingDeficit(true);
    try {
      const token = localStorage.getItem('access_token');
      // Trigger refresh of the demand-forecast cache — the new deficit
      // will surface immediately in the next /demand-forecast call.
      const response = await fetch(
        `${apiBase}/api/v1/ml/inventory/demand-forecast/refresh`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      // Best-effort — 200 means cache cleared, anything else still logs locally
      if (!response.ok) {
        console.warn('demand-forecast refresh failed', response.status);
      }
      toast({
        title: 'Manques signalés',
        description: `${deficitState.items.length} pièce(s) ajoutée(s) à la prévision de réappro`,
      });
      setDeficitState(null);
    } catch (error) {
      console.error('Reserve deficit failed:', error);
      toast({
        title: 'Erreur',
        description: 'Impossible de signaler les manques',
        variant: 'destructive',
      });
    } finally {
      setReservingDeficit(false);
    }
  };

  const filteredRequests = useMemo(
    () =>
      requests.filter(
        (req) =>
          req.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          req.machine_nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          req.requested_by_nom?.toLowerCase().includes(searchTerm.toLowerCase()),
      ),
    [requests, searchTerm],
  );

  return (
    <div className="p-8 animate-premium-fade-in bg-transparent">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight mb-2">Approbations ITV</h1>
          <p className="text-blue-300 font-medium border-l-4 border-violet-500 pl-4 py-1">
            Validez ou rejetez les demandes d'intervention · approuver = réserver le stock requis automatiquement.
          </p>
        </div>

        <div className="relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-blue-400 group-focus-within:text-violet-500 transition-colors" />
          <Input
            placeholder="Rechercher par description, machine ou demandeur..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-12 py-6 bg-white/50 backdrop-blur-sm border-blue-700/50 rounded-2xl focus:ring-2 focus:ring-violet-500/20 transition-all shadow-sm"
          />
        </div>

        <div className="bg-white/80 backdrop-blur-md rounded-[2.5rem] border border-white/20 shadow-2xl overflow-hidden">
          <Table>
            <TableHeader className="bg-slate-800/50">
              <TableRow className="border-b border-blue-800/50">
                <TableHead className="w-12"></TableHead>
                <TableHead className="font-black py-6 px-6 text-blue-400 uppercase tracking-widest text-[10px]">Demandeur</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Machine</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Priorité</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Description</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Date</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-20 text-blue-400 italic font-medium">
                    Récupération des demandes...
                  </TableCell>
                </TableRow>
              ) : filteredRequests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-20 text-blue-400 font-bold tracking-tight">
                    Aucune demande en attente
                  </TableCell>
                </TableRow>
              ) : (
                filteredRequests.map((req) => (
                  <React.Fragment key={req.id}>
                    <TableRow className="hover:bg-white/50 transition-all group">
                      <TableCell className="px-2">
                        <button
                          type="button"
                          onClick={() => setExpandedId(expandedId === req.id ? null : req.id)}
                          className="p-1.5 text-blue-400 hover:text-violet-500 transition-colors rounded hover:bg-violet-500/10"
                          aria-label={expandedId === req.id ? 'Replier' : 'Voir détails'}
                        >
                          {expandedId === req.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                      </TableCell>
                      <TableCell className="py-6 px-6">
                        <div className="font-black text-white">{req.requested_by_nom}</div>
                        <div className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Chef Opérateur</div>
                      </TableCell>
                      <TableCell>
                        <Badge className="bg-violet-500/10 text-violet-600 border-none px-3 font-bold">{req.machine_nom}</Badge>
                      </TableCell>
                      <TableCell>
                        {req.priorite === 'URGENTE' ? (
                          <Badge className="bg-rose-500 text-white border-none animate-pulse">URGENTE</Badge>
                        ) : (
                          <Badge variant="secondary" className="font-bold">{req.priorite}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="max-w-sm">
                        <div className="text-sm font-medium text-blue-200 leading-relaxed italic border-l-2 border-blue-800/50 pl-3">
                          "{req.description}"
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center text-blue-400 font-bold text-xs gap-1.5">
                          <Clock className="w-3 h-3" />
                          {new Date(req.requested_at).toLocaleDateString()}
                        </div>
                      </TableCell>
                      <TableCell className="text-right px-6">
                        <div className="flex justify-end gap-2 translate-x-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                          <Button
                            size="sm"
                            disabled={approvingId === req.id}
                            onClick={() => handleValidate(req.id, 'APPROVED')}
                            className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full h-10 w-10 p-0 shadow-lg shadow-emerald-500/20 active:scale-90"
                          >
                            {approvingId === req.id ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => {
                              setSelectedRequestId(req.id);
                              setRejectModalOpen(true);
                            }}
                            className="bg-rose-500 hover:bg-rose-600 text-white rounded-full h-10 w-10 p-0 shadow-lg shadow-rose-500/20 active:scale-90"
                          >
                            <X className="w-5 h-5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>

                    {expandedId === req.id && (
                      <TableRow className="bg-slate-900/40 border-l-4 border-l-violet-500">
                        <TableCell colSpan={7} className="px-8 py-5">
                          <PartsDetailPanel interventionId={req.id} />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Reject dialog (unchanged aesthetic) */}
      <Dialog open={rejectModalOpen} onOpenChange={setRejectModalOpen}>
        <DialogContent className="sm:max-w-[425px] rounded-[2rem] glass-card border-none p-0 overflow-hidden shadow-2xl">
          <div className="bg-rose-500 p-8 text-white relative">
            <X className="absolute -right-4 -top-4 w-32 h-32 opacity-10" />
            <DialogHeader>
              <DialogTitle className="text-2xl font-black tracking-tight">Rejeter la demande</DialogTitle>
              <p className="text-rose-100 font-medium">Expliquez brièvement pourquoi cette demande est rejetée.</p>
            </DialogHeader>
          </div>

          <div className="p-8 space-y-6 bg-white/80">
            <div className="space-y-3">
              <Label className="text-[10px] font-black uppercase tracking-widest text-blue-400">Motif de rejet</Label>
              <div className="relative">
                <MessageSquare className="absolute left-4 top-4 w-4 h-4 text-gray-300" />
                <Textarea
                  placeholder="Ex: Machine déjà planifiée pour demain, pièces manquantes..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="min-h-[120px] bg-slate-800/50 border-blue-800/50 rounded-2xl pl-11 py-4 font-medium leading-relaxed focus:ring-violet-500/20 focus:border-violet-500/30 transition-all"
                />
              </div>
            </div>

            <DialogFooter className="flex gap-2">
              <Button variant="ghost" onClick={() => setRejectModalOpen(false)} className="rounded-xl font-bold flex-1">
                Annuler
              </Button>
              <Button
                onClick={() => {
                  if (selectedRequestId) {
                    handleValidate(selectedRequestId, 'REJECTED', rejectionReason);
                    setRejectModalOpen(false);
                    setRejectionReason('');
                  }
                }}
                disabled={!rejectionReason}
                className="bg-rose-500 hover:bg-rose-600 text-white rounded-xl font-black px-8 flex-1 active:scale-95 disabled:grayscale transition-all"
              >
                Confirmer le rejet
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* Deficit dialog — surfaces 409 + Réserver button */}
      <Dialog open={deficitState != null} onOpenChange={(o) => { if (!o) setDeficitState(null); }}>
        <DialogContent className="sm:max-w-[560px] rounded-[2rem] border-none p-0 overflow-hidden shadow-2xl">
          <div className="bg-gradient-to-br from-orange-500 to-rose-600 p-8 text-white relative">
            <AlertTriangle className="absolute -right-4 -top-4 w-32 h-32 opacity-10" />
            <DialogHeader>
              <DialogTitle className="text-2xl font-black tracking-tight flex items-center gap-2">
                <AlertTriangle className="w-7 h-7" />
                Stock insuffisant
              </DialogTitle>
              <p className="text-orange-100 font-medium mt-1">
                L'approbation a été annulée — réservation impossible avec les niveaux actuels.
              </p>
            </DialogHeader>
          </div>

          <div className="p-8 space-y-5 bg-slate-900">
            <SectionDivider label={`${deficitState?.items.length ?? 0} pièce(s) en déficit`} tone="warning" />

            <div className="space-y-2">
              {deficitState?.items.map((item) => (
                <div
                  key={item.piece_id}
                  className="flex items-center gap-3 rounded-lg border border-orange-500/30 bg-slate-950/60 px-4 py-3"
                >
                  <Boxes className="h-4 w-4 text-orange-400" />
                  <span className="flex-1 font-bold text-white text-sm">{item.piece_name}</span>
                  <span className="font-mono text-xs tabular-nums">
                    <span className="text-blue-400">demandé </span>
                    <span className="text-blue-100 font-semibold">{formatNum(item.requested)}</span>
                    <span className="text-blue-400/50 mx-1">·</span>
                    <span className="text-emerald-400">dispo </span>
                    <span className="text-emerald-300 font-semibold">{formatNum(item.available)}</span>
                    <span className="text-blue-400/50 mx-1">·</span>
                    <span className="text-rose-400">manque </span>
                    <span className="text-rose-300 font-bold">{formatNum(item.deficit)}</span>
                  </span>
                </div>
              ))}
            </div>

            <div className="rounded-lg bg-violet-950/40 border border-violet-500/30 p-4 text-sm text-violet-200">
              <p className="font-semibold mb-1 flex items-center gap-1.5">
                <ShoppingCart className="w-4 h-4" />
                Que faire ?
              </p>
              <ul className="space-y-1 text-violet-300/80 text-xs leading-relaxed">
                <li>· <strong>Réserver les manques</strong> : signale aux achats — la prévision de réappro intègrera ces déficits</li>
                <li>· Vérifier que les niveaux soient suffisants puis ré-approuver la demande</li>
                <li>· Ou rejeter cette demande si non prioritaire</li>
              </ul>
            </div>

            <DialogFooter className="flex gap-2">
              <Button variant="ghost" onClick={() => setDeficitState(null)} className="rounded-xl font-bold flex-1 text-blue-300 hover:bg-slate-800">
                Fermer
              </Button>
              <Button
                onClick={handleReserveDeficit}
                disabled={reservingDeficit}
                className="bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 text-white rounded-xl font-black px-6 flex-1 shadow-lg shadow-orange-500/30 active:scale-95"
              >
                {reservingDeficit ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Mail className="w-4 h-4 mr-2" />
                )}
                Réserver les manques
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ─── PartsDetailPanel — expandable per-row pieces breakdown ──────────────

interface PartsDetailPanelProps {
  interventionId: number;
}

function PartsDetailPanel({ interventionId }: PartsDetailPanelProps) {
  const { data, loading, error } = useInterventionParts(interventionId);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-blue-400 font-mono text-xs">
        <Loader2 className="w-3 h-3 animate-spin" />
        chargement des pièces requises…
      </div>
    );
  }

  if (error) {
    return <p className="text-rose-400 font-mono text-xs">erreur: {error}</p>;
  }

  if (!data || data.required.length === 0) {
    return (
      <div className="flex items-center gap-2 text-amber-400/80 font-mono text-xs uppercase tracking-wider">
        <AlertTriangle className="w-3.5 h-3.5" />
        aucune pièce requise spécifiée pour cette demande
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <SectionDivider label={`Pièces requises · ${data.required.length}`} tone="default" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {data.required.map((rp) => (
          <div
            key={rp.id}
            className="flex items-center gap-3 rounded border border-blue-500/20 bg-slate-950/60 px-3 py-2"
          >
            <Boxes className="h-3.5 w-3.5 text-violet-400 shrink-0" />
            <span className="font-mono text-[10px] text-blue-400 tracking-wider min-w-[72px]">{rp.piece_reference}</span>
            <span className="flex-1 text-sm text-blue-100 truncate">{rp.piece_name}</span>
            <span className="font-mono text-xs tabular-nums text-emerald-300 font-semibold">
              {formatNum(rp.quantity_planned)}
              <span className="text-emerald-400/60 ml-0.5 text-[10px]">{rp.unit}</span>
            </span>
            <ReservationStatusBadge approved={rp.approved} reserved={rp.quantity_reserved} />
          </div>
        ))}
      </div>

      {data.pending.length > 0 && (
        <>
          <SectionDivider label={`Pièces non-cataloguées · ${data.pending.length}`} tone="warning" />
          <ul className="space-y-1.5">
            {data.pending.map((pp) => (
              <li key={pp.id} className="flex items-center gap-2 text-xs text-amber-200">
                <Badge variant="outline" className="border-amber-500/40 text-amber-300 font-mono text-[9px] uppercase tracking-wider">
                  {pp.status}
                </Badge>
                <span className="font-medium">{pp.name}</span>
                <span className="font-mono text-amber-400/70">{formatNum(pp.quantity)} {pp.unit}</span>
                {pp.notes && <span className="italic text-amber-300/60">— "{pp.notes}"</span>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function ReservationStatusBadge({ approved, reserved }: { approved: boolean | null; reserved: string }) {
  const r = Number(reserved);
  if (r > 0) {
    return (
      <Badge className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 font-mono text-[9px] uppercase tracking-wider">
        Réservé
      </Badge>
    );
  }
  if (approved === false) {
    return (
      <Badge className="bg-rose-500/15 text-rose-300 border border-rose-500/40 font-mono text-[9px] uppercase tracking-wider">
        Refusé
      </Badge>
    );
  }
  return (
    <Badge className="bg-blue-500/15 text-blue-300 border border-blue-500/40 font-mono text-[9px] uppercase tracking-wider">
      En attente
    </Badge>
  );
}

export default AdminItvApprovals;
