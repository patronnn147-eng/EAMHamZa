import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { MACHINE_STATUS_OPTIONS } from '@/lib/constants';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface PendingRequest {
  id: number;
  machine_id: number;
  machine_name: string;
  from_status: string;
  to_status: string;
  requested_by: number | null;
  requested_by_name: string | null;
  requested_at: string | null;
  source_intervention_id: number | null;
}

function statusLabel(value: string): string {
  return MACHINE_STATUS_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

export default function MachineStatusRequestsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<PendingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [rejectNoteId, setRejectNoteId] = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState('');

  const loadData = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/cheftech/machine-status-requests`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch (err) {
      console.error('Failed to load machine status requests:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const approve = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetch(
        `${API}/api/v1/cheftech/machine-status-requests/${id}/approve`,
        { method: 'PATCH', headers: { Authorization: `Bearer ${getToken()}` } }
      );
      if (!res.ok) throw new Error('API error');
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast({
        title: 'Statut approuvé',
        description: 'Le statut de la machine a été mis à jour.',
      });
    } catch {
      toast({
        title: 'Erreur',
        description: "Impossible d'approuver la demande",
        variant: 'destructive',
      });
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetch(
        `${API}/api/v1/cheftech/machine-status-requests/${id}/reject`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ note: rejectNote || undefined }),
        }
      );
      if (!res.ok) throw new Error('API error');
      setItems((prev) => prev.filter((i) => i.id !== id));
      setRejectNoteId(null);
      setRejectNote('');
      toast({ title: 'Demande rejetée' });
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de rejeter la demande',
        variant: 'destructive',
      });
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-6 w-6 text-white/70" />
          <h1 className="text-2xl font-bold text-white">Changements de statut</h1>
          <Badge variant="outline" className="border-white/10 text-white/50 text-xs">
            {items.length} en attente
          </Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadData}
          className="border-white/10 bg-white/5 text-white/60 hover:bg-white/10 text-xs"
        >
          Actualiser
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="font-medium text-sm">Aucune demande en attente</span>
        </div>
      ) : (
        <div className="rounded-xl border border-white/[0.06] bg-[#0f1623] overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-white/[0.06] hover:bg-transparent">
                <TableHead className="text-white/50">Machine</TableHead>
                <TableHead className="text-white/50">Technicien</TableHead>
                <TableHead className="text-white/50">Statut actuel</TableHead>
                <TableHead className="text-white/50">Statut proposé</TableHead>
                <TableHead className="text-white/50 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <React.Fragment key={item.id}>
                  <TableRow className="border-white/[0.06]">
                    <TableCell className="text-white font-medium">
                      {item.machine_name} (#{item.machine_id})
                    </TableCell>
                    <TableCell className="text-white/60">
                      {item.requested_by_name ?? `Utilisateur #${item.requested_by}`}
                    </TableCell>
                    <TableCell className="text-white/60">
                      {statusLabel(item.from_status)}
                    </TableCell>
                    <TableCell className="text-white font-semibold">
                      {statusLabel(item.to_status)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-500 text-white"
                          disabled={busyId === item.id}
                          onClick={() => approve(item.id)}
                        >
                          <CheckCircle2 className="h-4 w-4 mr-1" />
                          Approuver
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                          disabled={busyId === item.id}
                          onClick={() =>
                            setRejectNoteId(rejectNoteId === item.id ? null : item.id)
                          }
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Rejeter
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  {rejectNoteId === item.id && (
                    <TableRow className="border-white/[0.06]">
                      <TableCell colSpan={5} className="bg-[#131c2e]">
                        <div className="flex items-center gap-2 py-2">
                          <Textarea
                            value={rejectNote}
                            onChange={(e) => setRejectNote(e.target.value)}
                            placeholder="Motif du rejet (optionnel)"
                            className="bg-[#0f1623] border-white/[0.08] text-white text-sm min-h-[40px]"
                          />
                          <Button
                            size="sm"
                            className="bg-red-600 hover:bg-red-500 text-white shrink-0"
                            disabled={busyId === item.id}
                            onClick={() => reject(item.id)}
                          >
                            Confirmer
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
