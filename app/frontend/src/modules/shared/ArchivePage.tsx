/**
 * ArchivePage — unified archive view across all 4 date-based modules.
 *
 * Role scoping handled by backend (TECHNICIEN sees own items only;
 * ADMIN/CHEFTECH/CHETOP see all in their scope).
 *
 * Modules: planning_taches, ordres_travail, ordres_intervention, plannings.
 * Each item carries a reason badge: PAST_DUE_DATE or COMPLETED.
 * Admin/cheftech can reactivate items (sets archived_at = NULL).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Archive,
  Search,
  Calendar,
  RotateCcw,
  Loader2,
  FileText,
  ClipboardList,
  Wrench,
  Layers,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';

const apiBase = import.meta.env.VITE_API_BASE_URL || '';
function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

type Module = 'planning_taches' | 'ordres_travail' | 'ordres_intervention' | 'plannings';

const MODULE_META: Record<
  Module,
  { label: string; icon: React.ComponentType<{ className?: string }>; dueColumn: string }
> = {
  planning_taches:     { label: 'Tâches planning',  icon: ClipboardList, dueColumn: 'date_fin' },
  ordres_travail:      { label: 'Ordres travail',   icon: FileText,      dueColumn: 'date_echeance' },
  ordres_intervention: { label: 'Interventions',    icon: Wrench,        dueColumn: 'date_intervention' },
  plannings:           { label: 'Plannings',        icon: Layers,        dueColumn: 'date_fin' },
};

interface ArchivedRow {
  id: number;
  archived_at: string | null;
  archive_reason: string | null;
  titre?: string;
  identifiant_planning?: string;
  problem_description?: string;
  description?: string;
  rapport?: string;
  priorite?: string;
  priority?: string;
  statut?: string;
  planning_statut?: string;
  date_echeance?: string | null;
  date_fin?: string | null;
  date_debut?: string | null;
  date_intervention?: string | null;
  machine_id?: number | null;
  technicien_id?: number | null;
  technician_id?: number | null;
  utilisateur_id?: number | null;
}

interface CountsResponse {
  counts: Record<Module, number>;
  total: number;
}

export default function ArchivePage() {
  const { toast } = useToast();
  const [module, setModule] = useState<Module>('planning_taches');
  const [counts, setCounts] = useState<CountsResponse | null>(null);
  const [items, setItems] = useState<ArchivedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [reactivating, setReactivating] = useState<number | null>(null);

  const role = useMemo(() => {
    try {
      const u = localStorage.getItem('user');
      return u ? (JSON.parse(u).role || '').toUpperCase() : '';
    } catch {
      return '';
    }
  }, []);
  const canReactivate = role === 'ADMIN' || role === 'CHEFTECH';

  // ─── Fetchers ──────────────────────────────────────────────────────

  const fetchCounts = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase}/api/v1/archive/counts`, { headers: getAuthHeaders() });
      if (r.ok) setCounts(await r.json());
    } catch {/* silent */}
  }, []);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), size: String(size) });
      if (search) params.set('search', search);
      if (dateFrom) params.set('date_from', new Date(dateFrom).toISOString());
      if (dateTo) params.set('date_to', new Date(dateTo).toISOString());
      const r = await fetch(`${apiBase}/api/v1/archive/${module}?${params}`, { headers: getAuthHeaders() });
      if (r.ok) {
        const body = await r.json();
        setItems(body.items || []);
        setTotal(body.total || 0);
      }
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Chargement échoué',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [module, page, size, search, dateFrom, dateTo, toast]);

  useEffect(() => { void fetchCounts(); }, [fetchCounts]);
  useEffect(() => { void fetchItems(); }, [fetchItems]);

  // ─── Actions ───────────────────────────────────────────────────────

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleReactivate = async (item: ArchivedRow) => {
    if (!confirm(`Réactiver l'élément #${item.id} ? Il sera retiré de l'archive.`)) return;
    setReactivating(item.id);
    try {
      const r = await fetch(`${apiBase}/api/v1/archive/${module}/${item.id}/reactivate`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast({ title: 'Réactivé', description: `Élément #${item.id} retourné aux actifs` });
      await fetchItems();
      await fetchCounts();
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Échec',
        variant: 'destructive',
      });
    } finally {
      setReactivating(null);
    }
  };

  const handleSweepNow = async () => {
    if (!confirm('Lancer la sweep d\'archivage maintenant ?')) return;
    try {
      const r = await fetch(`${apiBase}/api/v1/archive/sweep`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const body = await r.json();
      toast({
        title: 'Sweep lancée',
        description: `${body.total ?? 0} élément(s) archivé(s)`,
      });
      await fetchCounts();
      await fetchItems();
    } catch {
      toast({ title: 'Erreur', variant: 'destructive' });
    }
  };

  // ─── Render ────────────────────────────────────────────────────────

  const pageMeta = MODULE_META[module];
  const PageIcon = pageMeta.icon;
  const totalPages = Math.max(1, Math.ceil(total / size));

  return (
    <div className="space-y-5">
      {/* Header */}
      <header className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-['DM_Sans'] text-2xl font-semibold text-white flex items-center gap-2.5">
            <Archive className="h-7 w-7 text-amber-400" />
            Archive
          </h1>
          <p className="mt-1 text-sm text-blue-300/70 font-mono tracking-wide">
            <span className="text-amber-400 font-semibold tabular-nums">{counts?.total ?? 0}</span>{' '}
            élément(s) archivé(s) au total · purge auto après 30 jours
          </p>
        </div>

        {role === 'ADMIN' && (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/10 font-mono text-xs tracking-wider"
              onClick={handleSweepNow}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Lancer sweep
            </Button>
          </div>
        )}
      </header>

      {/* Module tabs */}
      <Tabs value={module} onValueChange={(v) => { setModule(v as Module); setPage(1); }}>
        <TabsList className="bg-slate-900/60 border border-blue-500/20">
          {(Object.keys(MODULE_META) as Module[]).map((m) => {
            const Icon = MODULE_META[m].icon;
            const c = counts?.counts?.[m] ?? 0;
            return (
              <TabsTrigger
                key={m}
                value={m}
                className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-300"
              >
                <Icon className="h-3.5 w-3.5 mr-1.5" />
                {MODULE_META[m].label}
                <span className="ml-1.5 text-[10px] tabular-nums opacity-70">({c})</span>
              </TabsTrigger>
            );
          })}
        </TabsList>
      </Tabs>

      {/* Filter bar */}
      <div className="flex items-end gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-blue-400/60" />
          <Input
            placeholder="Rechercher titre / description / référence…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="pl-9 h-9 bg-slate-950/60 border-blue-500/30 placeholder:text-blue-400/40 text-sm"
          />
        </div>
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] font-mono uppercase tracking-wider text-blue-400/60">De</label>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-9 bg-slate-950/60 border-blue-500/30 text-sm w-40"
          />
        </div>
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] font-mono uppercase tracking-wider text-blue-400/60">À</label>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-9 bg-slate-950/60 border-blue-500/30 text-sm w-40"
          />
        </div>
        <Button onClick={handleSearch} size="sm" className="bg-blue-700 hover:bg-blue-600 h-9 font-mono text-xs tracking-wider">
          <Search className="h-3.5 w-3.5 mr-1.5" />
          Filtrer
        </Button>
        {(search || dateFrom || dateTo) && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => { setSearch(''); setSearchInput(''); setDateFrom(''); setDateTo(''); setPage(1); }}
            className="h-9 font-mono text-xs tracking-wider text-blue-300 hover:bg-slate-800"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Reset
          </Button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center gap-2 py-12 text-blue-400/60 font-mono text-xs">
          <Loader2 className="h-4 w-4 animate-spin" />
          chargement…
        </div>
      )}

      {/* Empty */}
      {!loading && items.length === 0 && (
        <div className="rounded-lg border border-dashed border-blue-500/30 bg-slate-950/40 py-16 text-center">
          <PageIcon className="h-10 w-10 mx-auto mb-3 text-blue-500/40" />
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-blue-400/60">
            aucun élément archivé{search || dateFrom || dateTo ? ' (filtres actifs)' : ''}
          </p>
        </div>
      )}

      {/* List */}
      {!loading && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <ArchivedItemCard
              key={`${module}-${item.id}`}
              item={item}
              module={module}
              canReactivate={canReactivate}
              reactivating={reactivating === item.id}
              onReactivate={() => handleReactivate(item)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-blue-500/10 pt-3 mt-4">
          <span className="text-xs text-blue-400/60 font-mono">
            Page {page} / {totalPages} · {total} élément(s)
          </span>
          <div className="flex gap-1">
            <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              ← Précédent
            </Button>
            <Button size="sm" variant="outline" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>
              Suivant →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── ArchivedItemCard ──────────────────────────────────────────────────

interface CardProps {
  item: ArchivedRow;
  module: Module;
  canReactivate: boolean;
  reactivating: boolean;
  onReactivate: () => void;
}

function ArchivedItemCard({ item, module, canReactivate, reactivating, onReactivate }: Readonly<CardProps>) {
  const dueColumnKey = MODULE_META[module].dueColumn as keyof ArchivedRow;
  const dueDateRaw = item[dueColumnKey] as string | null | undefined;
  const dueDate = dueDateRaw ? new Date(dueDateRaw) : null;
  const archivedAt = item.archived_at ? new Date(item.archived_at) : null;

  let reasonStyle: string;
  if (item.archive_reason === 'PAST_DUE_DATE') {
    reasonStyle = 'bg-orange-500/15 text-orange-300 border-orange-500/40';
  } else if (item.archive_reason === 'COMPLETED') {
    reasonStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
  } else {
    reasonStyle = 'bg-slate-500/15 text-slate-300 border-slate-500/40';
  }

  const title = item.titre || item.identifiant_planning || item.problem_description?.slice(0, 80) || `#${item.id}`;
  const subtitle =
    item.description?.slice(0, 120) ||
    item.problem_description?.slice(0, 120) ||
    item.rapport?.slice(0, 120) ||
    '';
  const prio = item.priorite || item.priority;
  const statut = item.statut || item.planning_statut;

  return (
    <div className="rounded-lg border border-amber-500/20 bg-slate-950/40 hover:border-amber-500/40 transition-colors p-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] tracking-wider text-blue-400/60 tabular-nums">
              #{String(item.id).padStart(4, '0')}
            </span>
            <Badge className={`font-mono text-[9px] uppercase tracking-wider border ${reasonStyle}`}>
              {item.archive_reason === 'PAST_DUE_DATE' ? 'Échéance dépassée' : item.archive_reason || 'Archivé'}
            </Badge>
            {prio && (
              <Badge className="font-mono text-[9px] uppercase tracking-wider bg-blue-500/10 text-blue-300 border border-blue-500/30">
                {prio}
              </Badge>
            )}
            {statut && (
              <Badge variant="secondary" className="font-mono text-[9px] uppercase tracking-wider bg-slate-700/60 text-slate-300">
                {statut}
              </Badge>
            )}
          </div>
          <h3 className="text-white font-semibold text-sm leading-tight">{title}</h3>
          {subtitle && (
            <p className="text-xs text-blue-300/70 mt-1 leading-relaxed line-clamp-2">{subtitle}</p>
          )}
        </div>

        {canReactivate && (
          <Button
            size="sm"
            variant="outline"
            disabled={reactivating}
            onClick={onReactivate}
            className="border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 font-mono text-[11px] tracking-wider shrink-0"
          >
            {reactivating ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5 mr-1.5" />}
            Réactiver
          </Button>
        )}
      </div>

      {/* Date row */}
      <div className="mt-3 flex items-center gap-5 text-[11px] font-mono text-blue-400/60 flex-wrap">
        {dueDate && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span className="opacity-70">échéance:</span>
            <span className="text-orange-300 tabular-nums">
              {dueDate.toLocaleDateString('fr-FR')}{' '}
              {dueDate.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </span>
        )}
        {archivedAt && (
          <span className="flex items-center gap-1">
            <Archive className="h-3 w-3" />
            <span className="opacity-70">archivé:</span>
            <span className="text-amber-300 tabular-nums">
              {archivedAt.toLocaleDateString('fr-FR')}{' '}
              {archivedAt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </span>
        )}
      </div>
    </div>
  );
}
