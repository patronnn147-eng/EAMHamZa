/**
 * PlanningMachinesDialog — admin/cheftech assigns machines to a planning.
 *
 * Lists all machines with checkboxes, pre-checks currently assigned ones.
 * Submits via PUT /api/v1/plannings/{id} with the full new machine_ids array.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, X, Cog, Search, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { client } from '@/lib/api';

interface MachineEntry {
  id: number;
  nom: string;
  zone?: string | null;
  statut?: string | null;
  reference?: string | null;
}

interface PlanningMachinesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  planningId: number;
  initialMachineIds: number[];
  onSaved: (newMachineIds: number[]) => void;
}

export function PlanningMachinesDialog({
  open,
  onOpenChange,
  planningId,
  initialMachineIds,
  onSaved,
}: PlanningMachinesDialogProps) {
  const { toast } = useToast();
  const [machines, setMachines] = useState<MachineEntry[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');

  // Sync selection from props on open
  useEffect(() => {
    if (open) setSelected(new Set(initialMachineIds));
  }, [open, initialMachineIds]);

  // Load all machines on open
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    (async () => {
      try {
        const resp = await client.apiCall.invoke({
          url: '/api/v1/entities/machines?size=500',
          method: 'GET',
        });
        const raw: any = (resp as any)?.data ?? resp;
        const items: MachineEntry[] = raw?.items ?? (Array.isArray(raw) ? raw : []);
        setMachines(items);
      } catch (e) {
        toast({
          title: 'Erreur',
          description: 'Impossible de charger les machines',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    })();
  }, [open, toast]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return machines;
    return machines.filter(
      (m) =>
        m.nom.toLowerCase().includes(q) ||
        (m.zone || '').toLowerCase().includes(q) ||
        String(m.id).includes(q),
    );
  }, [machines, search]);

  const toggle = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const save = useCallback(async () => {
    setSaving(true);
    try {
      const ids = Array.from(selected);
      const resp = await client.apiCall.invoke({
        url: `/api/v1/plannings/${planningId}`,
        method: 'PUT',
        data: { machine_ids: ids },
      });
      if (!resp) throw new Error('Empty response');
      toast({ title: 'Machines mises à jour', description: `${ids.length} machine(s) assignée(s)` });
      onSaved(ids);
      onOpenChange(false);
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Échec de sauvegarde',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  }, [selected, planningId, onSaved, onOpenChange, toast]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Cog className="h-5 w-5 text-cyan-400" />
            Assigner machines au planning
          </DialogTitle>
          <DialogDescription>
            Sélectionnez les machines couvertes par ce planning. Les techniciens ne
            verront ces machines que dans les formulaires de tâches.
          </DialogDescription>
        </DialogHeader>

        <div className="relative py-2 border-y border-blue-500/10">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-blue-400/60" />
          <Input
            placeholder="Rechercher machine / zone / id…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9 bg-slate-950/40 border-blue-500/20 text-sm"
          />
        </div>

        <div className="flex-1 overflow-y-auto rounded border border-blue-500/15 bg-slate-950/40">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-12 text-blue-400/60 font-mono text-xs">
              <Loader2 className="h-4 w-4 animate-spin" />
              chargement…
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="py-12 text-center text-blue-400/40 font-mono text-[11px] uppercase tracking-wider">
              {search ? 'aucun résultat' : 'liste vide'}
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <ul className="divide-y divide-blue-500/5">
              {filtered.map((m) => {
                const checked = selected.has(m.id);
                return (
                  <li
                    key={m.id}
                    className={`flex items-center gap-3 px-3 py-2 transition-colors cursor-pointer ${
                      checked ? 'bg-cyan-500/5' : 'hover:bg-blue-500/5'
                    }`}
                    onClick={() => toggle(m.id)}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(m.id)}
                      className="w-4 h-4 rounded border-blue-500/40 bg-slate-900 text-cyan-500 focus:ring-cyan-500/40 cursor-pointer"
                    />
                    <Cog className="h-3.5 w-3.5 text-blue-400/60 shrink-0" />
                    <span className="font-mono text-[10px] text-blue-400/60 tabular-nums min-w-[40px]">
                      #{m.id}
                    </span>
                    <span className={`flex-1 text-sm truncate ${checked ? 'text-cyan-200' : 'text-blue-100'}`}>
                      {m.nom}
                    </span>
                    {m.zone && (
                      <Badge variant="secondary" className="font-mono text-[9px] uppercase tracking-wider bg-slate-800/60 text-blue-300 border-blue-500/20">
                        {m.zone}
                      </Badge>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="text-xs text-blue-400/70 font-mono py-1 px-1">
          {selected.size} machine(s) sélectionnée(s) sur {machines.length}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            <X className="h-4 w-4 mr-2" />
            Annuler
          </Button>
          <Button
            onClick={save}
            disabled={saving}
            className="bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Sauvegarder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
