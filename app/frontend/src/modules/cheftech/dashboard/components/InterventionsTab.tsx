import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
} from '@/components/ui/select';
import { Wrench, Download, FileText, Loader2, Zap, Activity, History, AlertCircle } from 'lucide-react';
import { Separator as UISeparator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { getStatusColor } from '../utils/badges';
import type { Intervention } from '../types';

const getAuthToken = () => localStorage.getItem('access_token');

interface InterventionsTabProps {
  interventions: Intervention[];
  fetchInterventions: (filters?: { statut?: string; page?: number; size?: number }) => Promise<void>;
  approveIntervention?: (interventionId: number) => Promise<void>;
  rejectIntervention?: (interventionId: number, reason?: string) => Promise<void>;
  noGrouping?: boolean;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  interventions,
  approveIntervention,
  rejectIntervention,
  noGrouping = false,
}) => {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selected, setSelected] = useState<Intervention | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const [downloading, setDownloading] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const handleDownload = async (key: string, filename: string) => {
    try {
      setDownloading(key);
      const token = getAuthToken();
      if (!token) return;

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/storage/download-url`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          bucket_name: 'interventions',
          object_key: key
        })
      });

      if (!res.ok) throw new Error('Failed to get download URL');
      const { download_url } = await res.json();

      // Trigger download
      const a = document.createElement('a');
      a.href = download_url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
    } finally {
      setDownloading(null);
    }
  };

  const renderContentWithFiles = (content?: string) => {
    if (!content) return null;

    const parts = content.split(/(\[FILE:[^|]+\|[^\]]+\])/);
    return (
      <div className="space-y-1">
        {parts.map((part, idx) => {
          const match = part.match(/\[FILE:([^|]+)\|([^\]]+)\]/);
          if (match) {
            const [, key, name] = match;
            return (
              <div key={idx} className="flex items-center gap-2 mt-1">
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-7 text-[10px] gap-1 px-2"
                  onClick={() => handleDownload(key, name)}
                  disabled={!!downloading}
                >
                  {downloading === key ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Download className="h-3 w-3" />
                  )}
                  {name}
                </Button>
              </div>
            );
          }
          return <p key={idx} className="whitespace-pre-wrap">{part}</p>;
        })}
      </div>
    );
  };

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const formatDuration = (ms: number) => {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  };

  const getElapsedMs = (i: Intervention) => {
    const status = i.statut || 'EN_ATTENTE';
    if (!['APPROVED', 'VALIDE', 'EN_COURS', 'TERMINÉ', 'TERMINE', 'BLOQUÉ'].includes(status)) return 0;
    const startIso = i.date_debut || (['APPROVED', 'VALIDE'].includes(status) ? i.approved_at : undefined);
    const start = startIso ? new Date(startIso).getTime() : null;
    if (!start) return 0;
    const end = i.date_fin ? new Date(i.date_fin).getTime() : now;
    return Math.max(0, end - start);
  };

  const hasChrono = (i: Intervention) => {
    const s = i.statut || 'EN_ATTENTE';
    return s === 'APPROVED' || s === 'VALIDE' || s === 'EN_COURS' || s === 'TERMINÉ' || s === 'TERMINE' || s === 'BLOQUÉ';
  };

  const displayList = useMemo(
    () => {
      let list = [...(interventions || [])];
      if (!noGrouping) {
        list = list.filter((i) => {
          const s = i.statut || 'EN_ATTENTE';
          return s === 'EN_ATTENTE' || s === 'PENDING_APPROVAL';
        });
      }
      return list.sort((a, b) => new Date(b.date_intervention).getTime() - new Date(a.date_intervention).getTime());
    },
    [interventions, noGrouping],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench className="h-5 w-5" />
          Demandes d'Intervention en Attente
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-amber-600">Demandes trouvées: {displayList.length}</div>
          </div>

          <div className="space-y-4">
            {displayList.map((intervention) => {
              return (
                <div key={`req-${intervention.id}`} className="border rounded-lg p-4 bg-slate-800 shadow-sm hover:shadow transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className={`${getStatusColor(intervention.statut || 'EN_ATTENTE')} border-none`}>
                          {intervention.statut || 'EN_ATTENTE'}
                        </Badge>
                        <span className="text-sm text-blue-300">Demande: #{intervention.id}</span>
                        {typeof intervention.machine_id === 'number' && (
                          <span className="text-sm text-blue-300">Machine: #{intervention.machine_id}</span>
                        )}
                        <span className="text-sm font-medium text-blue-600">
                          Par: {intervention.technicien_id ? `Tech #${intervention.technicien_id}` : 'ChefOp'}
                        </span>
                        <span className="text-sm text-blue-300">
                          {new Date(intervention.date_intervention).toLocaleDateString()}
                        </span>
                      </div>

                      {intervention.problem_description && (
                        <div className="text-sm text-blue-100 mt-2 line-clamp-3">
                          {renderContentWithFiles(intervention.problem_description)}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelected(intervention);
                          setDetailsOpen(true);
                        }}
                      >
                        Détails
                      </Button>

                      {approveIntervention && (intervention.statut === 'EN_ATTENTE' || intervention.statut === 'PENDING_APPROVAL') && (
                        <Button 
                          size="sm" 
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => {
                            approveIntervention(intervention.id);
                          }}
                        >
                          ✅ Accepter
                        </Button>
                      )}
                      
                      {rejectIntervention && (intervention.statut === 'EN_ATTENTE' || intervention.statut === 'PENDING_APPROVAL') && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            setSelected(intervention);
                            setRejectReason('');
                            setRejectOpen(true);
                          }}
                        >
                          ❌ Rejeter
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}

            {displayList.length === 0 && <div className="text-sm text-blue-300 text-center py-8">Aucune demande trouvée.</div>}
          </div>
        </div>

        <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col p-0 rounded-3xl border-none shadow-2xl">
            {selected && (
              <>
                <DialogHeader className="px-8 pt-8 pb-4 bg-slate-800 dark:bg-slate-900">
                  <DialogTitle className="text-2xl font-black flex items-center gap-2">
                    <FileText className="h-6 w-6 text-primary" />
                    Détails de l'Intervention #{selected.id}
                  </DialogTitle>
                  <DialogDescription className="text-blue-300 font-medium">Revue complète de la demande d'intervention.</DialogDescription>
                </DialogHeader>
                
                <ScrollArea className="flex-1 px-8">
                  <div className="space-y-6 py-4 text-sm">
                    {/* --- Section 1: Statut & Priorité --- */}
                    <div className="grid grid-cols-2 gap-6 bg-slate-800/50 dark:bg-slate-800/50 p-4 rounded-2xl border border-blue-800/50 dark:border-gray-800">
                      <div className="space-y-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-blue-400">Statut actuel</div>
                        <Badge className={`${getStatusColor(selected.statut || 'EN_ATTENTE')} border-none px-3 py-1 font-bold`}>
                          {selected.statut || 'EN_ATTENTE'}
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-blue-400">Priorité</div>
                        <div className="font-bold text-white dark:text-gray-100 flex items-center gap-1.5">
                          <AlertCircle className={`h-4 w-4 ${selected.priority === 'URGENTE' ? 'text-red-500' : 'text-orange-500'}`} />
                          {selected.priority || 'NON DÉFINIE'}
                        </div>
                      </div>
                    </div>

                    {/* --- Section 2: Machine & OT --- */}
                    <div className="space-y-4">
                      <h3 className="text-[11px] font-black uppercase tracking-widest text-primary flex items-center gap-2">
                        <Zap className="h-4 w-4" /> Machine & Contexte
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-800 dark:bg-slate-900 p-3 rounded-xl border border-blue-800/50 dark:border-gray-800 shadow-sm">
                          <div className="text-blue-400 text-xs mb-1">Ordre de Travail</div>
                          <div className="font-black text-white dark:text-gray-100">#{selected.ordre_travail_id}</div>
                        </div>
                        <div className="bg-slate-800 dark:bg-slate-900 p-3 rounded-xl border border-blue-800/50 dark:border-gray-800 shadow-sm">
                          <div className="text-blue-400 text-xs mb-1">Machine</div>
                          <div className="font-black text-white dark:text-gray-100">#{selected.machine_id}</div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Catégorie</div>
                          <div className="font-bold">{(selected as any).machine_category || 'Non-critique'}</div>
                        </div>
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Fréquence Problème</div>
                          <div className="font-bold">{(selected as any).frequency || 'Première fois'}</div>
                        </div>
                      </div>
                    </div>

                    <UISeparator />

                    {/* --- Section 3: Analyse du Problème --- */}
                    <div className="space-y-4">
                      <h3 className="text-[11px] font-black uppercase tracking-widest text-primary flex items-center gap-2">
                        <Activity className="h-4 w-4" /> Analyse Technique
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Début incident</div>
                          <div className="font-bold">
                            {(selected as any).problem_start_time ? new Date((selected as any).problem_start_time).toLocaleString() : 'Non spécifié'}
                          </div>
                        </div>
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Déjà rencontré?</div>
                          <div className="font-bold">{(selected as any).similar_issue_before ? 'OUI' : 'NON'}</div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="text-blue-400 text-xs mb-1">Symptômes</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {(selected as any).symptoms ? (selected as any).symptoms.split(', ').map((s: string) => (
                            <Badge key={s} variant="outline" className="text-[10px] font-bold bg-muted/50">{s}</Badge>
                          )) : <span className="text-blue-400 italic">Aucun symptôme déclaré</span>}
                        </div>
                      </div>

                      <div>
                        <div className="text-blue-400 text-xs mb-1">Description détaillée</div>
                        <div className="mt-1 p-3 bg-slate-800/50 dark:bg-slate-800/80 rounded-xl border border-blue-700/50 dark:border-gray-800 text-blue-100 dark:text-gray-300 leading-relaxed font-medium">
                          {renderContentWithFiles(selected.problem_description)}
                        </div>
                      </div>
                    </div>

                    <UISeparator />

                    {/* --- Section 4: État & Impact --- */}
                    <div className="space-y-4">
                      <h3 className="text-[11px] font-black uppercase tracking-widest text-primary flex items-center gap-2">
                        <Activity className="h-4 w-4" /> État & Impact Production
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-blue-400 text-xs mb-1">État Opérationnel</div>
                          <div className="font-bold">{(selected as any).operating_state || 'N/A'}</div>
                        </div>
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Température</div>
                          <div className="font-bold">{(selected as any).temperature || 'N/A'}</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-blue-400 text-xs mb-1">Impact sur production</div>
                        <div className="font-bold text-white dark:text-gray-100">{(selected as any).impact || 'Aucun impact déclaré'}</div>
                      </div>
                    </div>

                    <UISeparator />

                    {/* --- Section 5: Planification --- */}
                    <div className="space-y-4 pb-6">
                      <h3 className="text-[11px] font-black uppercase tracking-widest text-primary flex items-center gap-2">
                        <History className="h-4 w-4" /> Planification & Ressources
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Durée estimée</div>
                          <div className="font-bold">{selected.estimated_duration_minutes ? `${selected.estimated_duration_minutes} min` : 'Non estimée'}</div>
                        </div>
                        <div>
                          <div className="text-blue-400 text-xs mb-1">Matériels</div>
                          <div className="font-bold truncate">{selected.required_materials || 'Aucun'}</div>
                        </div>
                      </div>
                      {selected.rejection_reason && (
                        <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-900/50 rounded-2xl">
                          <div className="text-rose-500 text-xs font-black uppercase tracking-widest mb-1 flex items-center gap-1.5">
                            <AlertCircle className="h-3 w-3" /> Motif du Rejet
                          </div>
                          <div className="text-rose-800 dark:text-rose-200 font-bold leading-relaxed">{selected.rejection_reason}</div>
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>

                <DialogFooter className="p-6 bg-slate-800/50 dark:bg-slate-800/50 border-t border-blue-800/50 dark:border-gray-800 flex items-center justify-between gap-4">
                  <div className="flex-1 text-[10px] text-blue-400 flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <History className="h-3 w-3" /> Chrono: {formatDuration(getElapsedMs(selected))}
                    </div>
                    {selected.requested_at && (
                      <div className="flex items-center gap-1">
                        <Zap className="h-3 w-3" /> Demandé le: {new Date(selected.requested_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                  <Button variant="ghost" onClick={() => setDetailsOpen(false)} className="rounded-xl font-bold px-6">
                    Fermer
                  </Button>
                </DialogFooter>
              </>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setDetailsOpen(false)}>
                Fermer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Decline l'intervention</DialogTitle>
              <DialogDescription>Ajoute un motif (optionnel).</DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label>Motif</Label>
              <Input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRejectOpen(false)}>
                Annuler
              </Button>
              <Button
                variant="destructive"
                onClick={async () => {
                  if (!selected) return;
                  await rejectIntervention(selected.id, rejectReason || undefined);
                  setRejectOpen(false);
                }}
              >
                Decline
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};
