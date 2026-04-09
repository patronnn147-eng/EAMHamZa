import React, { useEffect, useState, useCallback } from 'react';
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
import { CheckCircle2, MessageSquare, Clock, AlertTriangle, Search } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface CompletedWO {
  id: number;
  titre: string;
  description: string;
  statut: string;
  priorite: string;
  machine_id: number;
  machine_nom?: string;
  utilisateur_id?: number;
  technician_nom?: string;
  date_debut?: string;
  date_fin?: string;
  rapport?: string;
  failure_type?: string;
  cheftech_feedback?: string;
  duration_minutes?: number;
  created_at: string;
}

interface KPI {
  total_completed: number;
  avg_duration_minutes: number;
  failures_by_type: Record<string, number>;
  feedback_count: number;
  feedback_coverage_pct: number;
}

const FAILURE_LABELS: Record<string, string> = {
  NONE: 'Aucune panne',
  TWF: 'TWF — Usure outil',
  HDF: 'HDF — Thermique',
  PWF: 'PWF — Électrique',
  OSF: 'OSF — Surcharge',
  RNF: 'RNF — Aléatoire',
};

export const CompletedWorkOrdersTab: React.FC = () => {
  const { toast } = useToast();
  const [workOrders, setWorkOrders] = useState<CompletedWO[]>([]);
  const [kpi, setKpi] = useState<KPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTech, setSearchTech] = useState('');
  const [filterFailure, setFilterFailure] = useState('ALL');

  // Feedback dialog
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackWO, setFeedbackWO] = useState<CompletedWO | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [savingFeedback, setSavingFeedback] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const token = getToken();
      const [woRes, kpiRes] = await Promise.all([
        fetch(`${API}/api/v1/cheftech/completed-work-orders`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API}/api/v1/cheftech/reports/kpi`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (woRes.ok) setWorkOrders(await woRes.json());
      if (kpiRes.ok) setKpi(await kpiRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const openFeedbackDialog = (wo: CompletedWO) => {
    setFeedbackWO(wo);
    setFeedbackText(wo.cheftech_feedback || '');
    setFeedbackOpen(true);
  };

  const handleSaveFeedback = async () => {
    if (!feedbackWO) return;
    setSavingFeedback(true);
    try {
      const token = getToken();
      const res = await fetch(`${API}/api/v1/cheftech/work-orders/${feedbackWO.id}/feedback`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedbackText }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erreur lors de la sauvegarde');
      }
      toast({ title: 'Succès', description: 'Feedback enregistré.' });
      setFeedbackOpen(false);
      fetchData();
    } catch (e: any) {
      toast({ title: 'Erreur', description: e.message, variant: 'destructive' });
    } finally {
      setSavingFeedback(false);
    }
  };

  const filtered = workOrders.filter((wo) => {
    const techMatch = !searchTech || (wo.technician_nom || '').toLowerCase().includes(searchTech.toLowerCase());
    const failureMatch = filterFailure === 'ALL' || wo.failure_type === filterFailure;
    return techMatch && failureMatch;
  });

  const formatDuration = (mins?: number) => {
    if (!mins) return '—';
    if (mins < 60) return `${mins} min`;
    return `${Math.floor(mins / 60)}h ${mins % 60}min`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Summary */}
      {kpi && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-none shadow bg-green-50">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs font-bold text-green-600 uppercase tracking-wider">Complétés</p>
              <p className="text-3xl font-black text-green-700 mt-1">{kpi.total_completed}</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-blue-50">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs font-bold text-blue-600 uppercase tracking-wider">Durée Moy.</p>
              <p className="text-3xl font-black text-blue-700 mt-1">{formatDuration(kpi.avg_duration_minutes)}</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-amber-50">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs font-bold text-amber-600 uppercase tracking-wider">Feedbacks</p>
              <p className="text-3xl font-black text-amber-700 mt-1">{kpi.feedback_count}</p>
              <p className="text-xs text-amber-500">{kpi.feedback_coverage_pct}% couverture</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-slate-800/50">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Pannes / Type</p>
              <div className="mt-1 space-y-0.5">
                {Object.entries(kpi.failures_by_type).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-blue-200">{FAILURE_LABELS[k] || k}</span>
                    <span className="font-bold text-blue-50">{v}</span>
                  </div>
                ))}
                {Object.keys(kpi.failures_by_type).length === 0 && (
                  <p className="text-xs text-blue-400">Aucune donnée</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-blue-400" />
          <Input
            placeholder="Rechercher par technicien..."
            value={searchTech}
            onChange={(e) => setSearchTech(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterFailure} onValueChange={setFilterFailure}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Type de panne" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Tous les types</SelectItem>
            {Object.entries(FAILURE_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            Ordres de Travail Complétés ({filtered.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-blue-400">
              <CheckCircle2 className="h-10 w-10 mx-auto mb-3 opacity-40" />
              <p>Aucun ordre complété trouvé</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs font-bold text-blue-300 uppercase tracking-wider">
                    <th className="py-3 pr-4">ID</th>
                    <th className="py-3 pr-4">Machine</th>
                    <th className="py-3 pr-4">Technicien</th>
                    <th className="py-3 pr-4">Début / Fin</th>
                    <th className="py-3 pr-4">Durée</th>
                    <th className="py-3 pr-4">Panne</th>
                    <th className="py-3 pr-4">Rapport</th>
                    <th className="py-3 pr-4">Feedback CT</th>
                    <th className="py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filtered.map((wo) => (
                    <tr key={wo.id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 pr-4 font-mono font-bold text-blue-100">#{wo.id}</td>
                      <td className="py-3 pr-4 text-blue-100">{wo.machine_nom || `#${wo.machine_id}`}</td>
                      <td className="py-3 pr-4 text-blue-100">{wo.technician_nom || '—'}</td>
                      <td className="py-3 pr-4 text-blue-300 text-xs whitespace-nowrap">
                        {wo.date_debut ? new Date(wo.date_debut).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        <br />
                        {wo.date_fin ? new Date(wo.date_fin).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                      </td>
                      <td className="py-3 pr-4">
                        <span className="flex items-center gap-1 text-blue-200">
                          <Clock className="h-3 w-3" />
                          {formatDuration(wo.duration_minutes)}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        {wo.failure_type ? (
                          <Badge variant="outline" className={wo.failure_type === 'NONE' ? 'text-blue-300' : 'text-amber-700 border-amber-300 bg-amber-50'}>
                            {FAILURE_LABELS[wo.failure_type] || wo.failure_type}
                          </Badge>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="py-3 pr-4 max-w-[200px]">
                        {wo.rapport ? (
                          <p className="text-xs text-blue-200 line-clamp-2 leading-relaxed">{wo.rapport}</p>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="py-3 pr-4 max-w-[160px]">
                        {wo.cheftech_feedback ? (
                          <p className="text-xs text-indigo-700 bg-indigo-50 px-2 py-1 rounded line-clamp-2">{wo.cheftech_feedback}</p>
                        ) : (
                          <span className="text-xs text-gray-300 italic">Pas de feedback</span>
                        )}
                      </td>
                      <td className="py-3">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openFeedbackDialog(wo)}
                          className="flex items-center gap-1 text-xs"
                        >
                          <MessageSquare className="h-3 w-3" />
                          Feedback
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feedback Dialog */}
      <Dialog open={feedbackOpen} onOpenChange={setFeedbackOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-indigo-600" />
              Feedback ChefTech — OT #{feedbackWO?.id}
            </DialogTitle>
            <DialogDescription>
              Ajoutez ou modifiez votre feedback sur cette intervention. Les données d'exécution ne seront pas modifiées.
            </DialogDescription>
          </DialogHeader>

          {feedbackWO && (
            <div className="text-xs text-blue-300 bg-slate-800/50 rounded p-3 space-y-1">
              <p><strong>Technicien:</strong> {feedbackWO.technician_nom || '—'}</p>
              <p><strong>Machine:</strong> {feedbackWO.machine_nom || `#${feedbackWO.machine_id}`}</p>
              <p><strong>Durée:</strong> {formatDuration(feedbackWO.duration_minutes)}</p>
              {feedbackWO.failure_type && (
                <p><strong>Panne:</strong> {FAILURE_LABELS[feedbackWO.failure_type] || feedbackWO.failure_type}</p>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="feedback-text" className="text-sm font-semibold">Votre Feedback</Label>
            <Textarea
              id="feedback-text"
              placeholder="Ex: Travail bien exécuté. Rapport clair. À surveiller pour la prochaine maintenance..."
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              rows={4}
              className="resize-none"
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setFeedbackOpen(false)}>Annuler</Button>
            <Button
              onClick={handleSaveFeedback}
              disabled={savingFeedback || !feedbackText.trim()}
              className="bg-indigo-600 hover:bg-indigo-700"
            >
              {savingFeedback ? 'Enregistrement...' : 'Enregistrer'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
