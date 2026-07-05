import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CheckCircle2, Clock, Search, BarChart3 } from 'lucide-react';

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
  technician_email?: string;
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

export default function AdminCompletedWorkOrders() {
  const [workOrders, setWorkOrders] = useState<CompletedWO[]>([]);
  const [kpi, setKpi] = useState<KPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTech, setSearchTech] = useState('');
  const [filterFailure, setFilterFailure] = useState('ALL');

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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-4xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="h-7 w-7 text-indigo-600" />
          Supervision Système — Ordres Complétés
        </h2>
        <p className="text-sm text-blue-300 mt-1">Vue lecture seule. Aucune modification n'est possible depuis cet écran.</p>
      </div>

      {/* KPI Bar */}
      {kpi && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="border-none shadow bg-green-50">
            <CardContent className="pt-4 pb-3 text-center">
              <p className="text-xs font-bold text-green-600 uppercase tracking-wider">Total Complétés</p>
              <p className="text-3xl font-black text-green-700 mt-1">{kpi.total_completed}</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-blue-50">
            <CardContent className="pt-4 pb-3 text-center">
              <p className="text-xs font-bold text-blue-600 uppercase tracking-wider">Durée Moy.</p>
              <p className="text-xl font-black text-blue-700 mt-1">{formatDuration(kpi.avg_duration_minutes)}</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-amber-50">
            <CardContent className="pt-4 pb-3 text-center">
              <p className="text-xs font-bold text-amber-600 uppercase tracking-wider">Feedbacks CT</p>
              <p className="text-3xl font-black text-amber-700 mt-1">{kpi.feedback_count}</p>
              <p className="text-xs text-amber-500">{kpi.feedback_coverage_pct}% couverture</p>
            </CardContent>
          </Card>
          <Card className="border-none shadow bg-red-50 col-span-2">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2">Pannes par Type</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {Object.entries(kpi.failures_by_type).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-blue-200 truncate">{FAILURE_LABELS[k] || k}</span>
                    <span className="font-bold text-blue-50 ml-1">{v}</span>
                  </div>
                ))}
                {Object.keys(kpi.failures_by_type).length === 0 && (
                  <p className="text-xs text-blue-400 col-span-2">Aucune donnée</p>
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
          <SelectTrigger className="w-56">
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

      {/* Read-only table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            {filtered.length} ordre(s) — lecture seule
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-blue-400">
              <CheckCircle2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
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
                    <th className="py-3 pr-4">Rapport Tech.</th>
                    <th className="py-3">Feedback ChefTech</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filtered.map((wo) => (
                    <tr key={wo.id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 pr-4 font-mono font-bold text-blue-100">#{wo.id}</td>
                      <td className="py-3 pr-4 text-blue-100">{wo.machine_nom || `#${wo.machine_id}`}</td>
                      <td className="py-3 pr-4">
                        <div>
                          <p className="text-blue-100">{wo.technician_nom || '—'}</p>
                          {wo.technician_email && <p className="text-xs text-blue-400">{wo.technician_email}</p>}
                        </div>
                      </td>
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
                          <Badge variant="outline" className={wo.failure_type === 'NONE' ? 'text-blue-400' : 'text-amber-700 border-amber-300 bg-amber-50 text-xs'}>
                            {FAILURE_LABELS[wo.failure_type] || wo.failure_type}
                          </Badge>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="py-3 pr-4 max-w-[200px]">
                        {wo.rapport
                          ? <p className="text-xs text-blue-200 line-clamp-2">{wo.rapport}</p>
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="py-3 max-w-[180px]">
                        {wo.cheftech_feedback
                          ? <p className="text-xs text-indigo-700 bg-indigo-50 px-2 py-1 rounded line-clamp-2">{wo.cheftech_feedback}</p>
                          : <span className="text-xs text-gray-300 italic">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
