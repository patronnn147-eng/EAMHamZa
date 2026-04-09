import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Calendar, FileText, Play, CheckCircle, AlertTriangle, Download, Loader2, Plus } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Intervention } from '@/lib/types';
import { InterventionRequestDialog } from './components/InterventionRequestDialog';
import { FinishInterventionDialog } from './components/FinishInterventionDialog';
import { TechnicianNewInterventionModal } from '@/modules/technicien/components/TechnicianNewInterventionModal';
import { AppPagination } from '@/components/shared/AppPagination';
import { client } from '@/lib/api';

export default function TechnicianInterventions() {
  const { toast } = useToast();

  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [filteredInterventions, setFilteredInterventions] = useState<Intervention[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(100);
  const [requestOpen, setRequestOpen] = useState(false);
  const [requestIntervention, setRequestIntervention] = useState<Intervention | null>(null);
  const [finishDialogOpen, setFinishDialogOpen] = useState(false);
  const [finishIntervention, setFinishIntervention] = useState<Intervention | null>(null);
  const [newRequestOpen, setNewRequestOpen] = useState(false);

  const [now, setNow] = useState(() => Date.now());

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
    const startIso = i.date_debut || (status === 'APPROVED' ? i.approved_at : undefined);
    const start = startIso ? new Date(startIso).getTime() : null;
    if (!start) return 0;
    const end = i.date_fin ? new Date(i.date_fin).getTime() : now;
    return Math.max(0, end - start);
  };

  const hasChrono = (i: Intervention) => {
    const s = i.statut || 'EN_ATTENTE';
    return s === 'APPROVED' || s === 'EN_COURS' || s === 'TERMINÉ' || s === 'TERMINE' || s === 'BLOQUÉ';
  };

  const overdueInterventions = useMemo(
    () => interventions.filter((i) => i.is_overdue),
    [interventions],
  );

  const getStatusLabel = (statut?: string) => {
    const s = statut || 'EN_ATTENTE';
    if (s === 'PENDING_APPROVAL') return 'En attente d\'approbation';
    if (s === 'APPROVED') return 'Approuvée';
    if (s === 'DECLINED' || s === 'REJECTED') return 'Refusée';
    if (s === 'EN_COURS') return 'En cours';
    if (s === 'TERMINÉ' || s === 'TERMINE') return 'Terminée';
    if (s === 'BLOQUÉ') return 'Bloquée';
    if (s === 'EN_ATTENTE') return 'En attente';
    return s;
  };

  const getStatusColor = (statut?: string) => {
    const base = "rounded-full px-4 py-1.5 text-[11px] font-black uppercase tracking-widest border transition-all duration-300 ";
    const s = statut || 'EN_ATTENTE';
    switch (s) {
      case 'PENDING_APPROVAL':
        return base + 'text-orange-700 bg-orange-50/50 border-orange-200/50';
      case 'APPROVED':
        return base + 'text-green-700 bg-green-50/50 border-green-200/50 shadow-[0_0_10px_rgba(34,197,94,0.2)]';
      case 'DECLINED':
      case 'REJECTED':
        return base + 'text-red-700 bg-red-50/50 border-red-200/50';
      case 'EN_COURS':
        return base + 'text-blue-700 bg-blue-50/50 border-blue-200/50 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.2)]';
      case 'EN_ATTENTE':
        return base + 'text-yellow-700 bg-yellow-50/50 border-yellow-200/50';
      case 'TERMINÉ':
      case 'TERMINE':
        return base + 'text-emerald-800 bg-emerald-100/50 border-emerald-300/50';
      case 'BLOQUÉ':
        return base + 'text-red-700 bg-red-50/50 border-red-200/50';
      default:
        return base + 'text-blue-200 bg-slate-800/50 border-blue-700/50';
    }
  };

  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (key: string, filename: string) => {
    try {
      setDownloading(key);
      const token = localStorage.getItem('access_token');
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
          return <span key={idx} className="whitespace-pre-wrap">{part}</span>;
        })}
      </div>
    );
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  useEffect(() => {
    for (const i of overdueInterventions) {
      const key = `overdue_intervention_alert_${i.id}`;
      if (localStorage.getItem(key)) continue;
      localStorage.setItem(key, '1');
      toast({
        title: 'Échéance dépassée',
        description: `Intervention #${i.id} (OT #${i.ordre_travail_id}) a dépassé la date d'échéance.`,
        variant: 'destructive',
      });
    }
  }, [overdueInterventions, toast]);

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

  const submitRequest = async (data: {
    ordre_travail_id: number;
    machine_id: number | null;
    problem_description: string;
    priority: string;
    estimated_duration_minutes: number | null;
    required_materials: string | null;
  }) => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions/request`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Échec de la demande');
      }

      toast({
        title: 'Demande envoyée',
        description: 'En attente de validation ChefTech',
      });

      setRequestOpen(false);
      setRequestIntervention(null);
      fetchData();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Échec de la demande',
        variant: 'destructive',
      });
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/technicien/interventions?page=${page}&size=${pageSize}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch interventions');
      const res = await response.json();

      const items = res.items || [];
      setInterventions(items);
      setFilteredInterventions(items);
      setTotalPages(res.total_pages || 1);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les interventions',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (
    interventionId: number,
    statut: string,
    feedback?: { actual_failure_type: string; rapport?: string }
  ) => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions/${interventionId}/status`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          statut,
          ...feedback
        }),
      });
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
          <h2 className="text-4xl font-bold text-white">Mes Demandes d'Intervention</h2>
          <p className="mt-1 text-sm text-blue-300">Liste des demandes d'intervention que vous avez soumises</p>
        </div>
        <Button 
          onClick={() => setNewRequestOpen(true)}
          className="bg-gradient-premium hover:opacity-90 rounded-2xl font-bold px-6 py-6 shadow-lg shadow-violet-500/20 transition-all border-none"
        >
          <Plus className="mr-2 h-5 w-5" />
          Demander l'intervention
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-blue-400" />
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
          <Card className="bg-slate-800/80 backdrop-blur-md border border-blue-800/30 shadow-xl">
            <CardContent className="text-center py-12">
              <p className="text-blue-300">Aucune intervention trouvée</p>
            </CardContent>
          </Card>
        ) : (
          filteredInterventions.map((intervention) => (
            <Card key={intervention.id} className="bg-slate-800/80 backdrop-blur-md border border-blue-800/30 shadow-lg hover:shadow-xl hover:border-blue-700/50 transition-all">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      Intervention #{intervention.id}
                    </CardTitle>
                    <p className="text-sm text-blue-300 mt-1">
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
                <div className="flex items-center gap-2 mb-3">
                  <Badge className={getStatusColor(intervention.statut)}>{getStatusLabel(intervention.statut)}</Badge>
                  {intervention.is_overdue ? (
                    <Badge className="bg-red-100 text-red-800">Overdue</Badge>
                  ) : null}
                  {intervention.rejection_reason ? (
                    <span className="text-xs text-red-600">Motif: {intervention.rejection_reason}</span>
                  ) : null}
                  {intervention.priority && (
                    <Badge variant="outline">Priorité: {intervention.priority}</Badge>
                  )}
                </div>

                {hasChrono(intervention) ? (
                  <div className="mb-3 text-sm">
                    <span className="text-blue-300">Chrono:</span>{' '}
                    <span className="font-medium">{formatDuration(getElapsedMs(intervention))}</span>
                  </div>
                ) : null}

                {/* Machine & Category Info */}
                <div className="mb-4 grid grid-cols-2 gap-2 text-sm">
                  {intervention.machine_category && (
                    <div className="bg-blue-900/30 p-2 rounded-lg border border-blue-800/30">
                      <span className="text-blue-300">Catégorie:</span> {intervention.machine_category}
                    </div>
                  )}
                  {intervention.frequency && (
                    <div className="bg-blue-900/30 p-2 rounded-lg border border-blue-800/30">
                      <span className="text-blue-300">Fréquence:</span> {intervention.frequency}
                    </div>
                  )}
                  {intervention.operating_state && (
                    <div className="bg-blue-900/30 p-2 rounded-lg border border-blue-800/30">
                      <span className="text-blue-300">État:</span> {intervention.operating_state}
                    </div>
                  )}
                  {intervention.temperature && (
                    <div className="bg-blue-900/30 p-2 rounded-lg border border-blue-800/30">
                      <span className="text-blue-300">Température:</span> {intervention.temperature}
                    </div>
                  )}
                  {intervention.impact && (
                    <div className="bg-blue-900/30 p-2 rounded-lg border border-blue-800/30">
                      <span className="text-blue-300">Impact:</span> {intervention.impact}
                    </div>
                  )}
                </div>

                {/* Problem Details */}
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-blue-100 mb-2">Description du problème:</h4>
                  <div className="text-sm text-blue-200 bg-blue-900/30 p-3 rounded-lg border border-blue-800/30 line-clamp-4">
                    {renderContentWithFiles(intervention.problem_description)}
                  </div>
                </div>

                {/* Symptoms */}
                {intervention.symptoms && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-blue-100 mb-2">Symptômes:</h4>
                    <div className="text-sm text-blue-200 bg-blue-900/30 p-3 rounded-lg border border-blue-800/30">
                      {intervention.suggested_cause}
                    </div>
                  </div>
                )}

                {/* Suggested Details from AI */}
                {(intervention.suggested_cause || intervention.risk_score || intervention.suggested_priority) && (
                  <div className="mb-4 p-3 bg-violet-900/20 rounded-lg border border-violet-800/30">
                    <h4 className="text-sm font-medium text-violet-300 mb-2">Analyse IA:</h4>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      {intervention.suggested_priority && (
                        <div><span className="text-violet-400">Priorité suggérée:</span> {intervention.suggested_priority}</div>
                      )}
                      {intervention.risk_score && (
                        <div><span className="text-violet-400">Score risque:</span> {intervention.risk_score}</div>
                      )}
                      {intervention.suggested_cause && (
                        <div className="col-span-3"><span className="text-violet-400">Cause suggérée:</span> {intervention.suggested_cause}</div>
                      )}
                    </div>
                  </div>
                )}

                {/* Report (after completion) */}
                {intervention.rapport && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-blue-100 mb-2">Rapport d'intervention:</h4>
                    <div className="text-sm text-blue-200 bg-blue-900/30 p-3 rounded-lg border border-blue-800/30 line-clamp-4">
                      {renderContentWithFiles(intervention.rapport)}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  {(intervention.statut || 'EN_ATTENTE') === 'EN_ATTENTE' && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setRequestIntervention(intervention);
                        setRequestOpen(true);
                      }}
                    >
                      <Play className="mr-2 h-4 w-4" />
                      Demander démarrage
                    </Button>
                  )}

                  {(intervention.statut || 'EN_ATTENTE') === 'PENDING_APPROVAL' && (
                    <Button size="sm" variant="outline" disabled>
                      En attente approbation
                    </Button>
                  )}

                  {(intervention.statut || 'EN_ATTENTE') === 'APPROVED' && (
                    <Button size="sm" onClick={() => updateStatus(intervention.id, 'EN_COURS')}>
                      <Play className="mr-2 h-4 w-4" />
                      Démarrer
                    </Button>
                  )}

                  {(intervention.statut || 'EN_ATTENTE') === 'DECLINED' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setRequestIntervention(intervention);
                        setRequestOpen(true);
                      }}
                    >
                      Re-demander
                    </Button>
                  )}

                  {(intervention.statut || 'EN_ATTENTE') === 'REJECTED' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setRequestIntervention(intervention);
                        setRequestOpen(true);
                      }}
                    >
                      Re-demander
                    </Button>
                  )}

                  {(intervention.statut || 'EN_ATTENTE') === 'EN_COURS' && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setFinishIntervention(intervention);
                        setFinishDialogOpen(true);
                      }}
                      className="bg-green-600 hover:bg-green-700"
                    >
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

      <div className="flex justify-end mt-4">
        <AppPagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </div>

      <InterventionRequestDialog
        open={requestOpen}
        onOpenChange={setRequestOpen}
        initialOrdreTravailId={requestIntervention?.ordre_travail_id || 0}
        initialMachineId={requestIntervention?.machine_id ?? null}
        onSubmit={submitRequest}
      />

      {finishIntervention && (
        <FinishInterventionDialog
          open={finishDialogOpen}
          onOpenChange={setFinishDialogOpen}
          interventionId={finishIntervention.id}
          onConfirm={(feedback) => {
            updateStatus(finishIntervention.id, 'TERMINÉ', feedback);
            setFinishDialogOpen(false);
          }}
        />
      )}
      
      <TechnicianNewInterventionModal
        open={newRequestOpen}
        onOpenChange={setNewRequestOpen}
        onSuccess={() => {
          fetchData();
          toast({ title: 'Demande envoyée', description: 'Votre demande a été enregistrée avec succès.' });
        }}
      />
    </div>
  );
}