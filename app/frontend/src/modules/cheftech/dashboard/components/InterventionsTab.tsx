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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Wrench, Download, FileText, Loader2 } from 'lucide-react';
import { getStatusColor } from '../utils/badges';
import type { Intervention } from '../types';

const getAuthToken = () => localStorage.getItem('access_token');

interface InterventionsTabProps {
  interventions: Intervention[];
  fetchInterventions: (filters?: {
    statut?: string;
  }) => Promise<void>;
  approveIntervention: (interventionId: number) => Promise<void>;
  rejectIntervention: (interventionId: number, reason?: string) => Promise<void>;
  noGrouping?: boolean;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  interventions,
  fetchInterventions,
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
    if (!['APPROVED', 'EN_COURS', 'TERMINÉ', 'TERMINE', 'BLOQUÉ'].includes(status)) return 0;
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

  const pending = useMemo(
    () => interventions.filter((i) => (i.statut || 'EN_ATTENTE') === 'PENDING_APPROVAL'),
    [interventions],
  );

  // Group interventions by work order to avoid showing duplicates
  const groupedInterventions = useMemo(() => {
    const groups = new Map<number, Intervention[]>();
    for (const intervention of interventions) {
      const woId = intervention.ordre_travail_id;
      if (!groups.has(woId)) {
        groups.set(woId, []);
      }
      groups.get(woId)!.push(intervention);
    }
    // Convert to array of groups, sorted by most recent intervention date
    return Array.from(groups.values())
      .map((group) => ({
        interventions: group.sort((a, b) =>
          new Date(b.date_intervention).getTime() - new Date(a.date_intervention).getTime()
        ),
        primaryIntervention: group[0], // Use first as representative
      }))
      .sort((a, b) =>
        new Date(b.primaryIntervention.date_intervention).getTime() -
        new Date(a.primaryIntervention.date_intervention).getTime()
      );
  }, [interventions]);

  const displayList = noGrouping
    ? interventions.map(i => ({ interventions: [i], primaryIntervention: i }))
    : groupedInterventions;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench className="h-5 w-5" />
          Interventions
        </CardTitle>
        <div className="flex gap-4">
          <Select onValueChange={(value) => fetchInterventions(value === 'ALL' ? {} : { statut: value })}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Tous les statuts</SelectItem>
              <SelectItem value="EN_ATTENTE">En attente</SelectItem>
              <SelectItem value="EN_COURS">En cours</SelectItem>
              <SelectItem value="TERMINÉ">Terminé</SelectItem>
              <SelectItem value="BLOQUÉ">Bloqué</SelectItem>
              <SelectItem value="PENDING_APPROVAL">Pending approval</SelectItem>
              <SelectItem value="APPROVED">Approved</SelectItem>
              <SelectItem value="DECLINED">Declined</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Pending requests: {pending.length}</div>
          </div>

          <div className="space-y-4">
            {displayList.map((group) => {
              const intervention = group.primaryIntervention;
              const hasMultipleTechs = group.interventions.length > 1;
              return (
                <div key={`wo-${intervention.ordre_travail_id}`} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className={getStatusColor(intervention.statut || 'EN_ATTENTE')}>
                          {intervention.statut || 'EN_ATTENTE'}
                        </Badge>
                        {intervention.is_overdue ? (
                          <Badge className="bg-red-100 text-red-800">Overdue</Badge>
                        ) : null}
                        <span className="text-sm text-gray-500">Ordre: #{intervention.ordre_travail_id}</span>
                        {hasMultipleTechs ? (
                          <span className="text-sm font-medium text-blue-600">
                            {group.interventions.length} Technicians
                          </span>
                        ) : (
                          typeof intervention.technicien_id === 'number' && (
                            <span className="text-sm text-gray-500">Tech: #{intervention.technicien_id}</span>
                          )
                        )}
                        <span className="text-sm text-gray-500">
                          {new Date(intervention.date_intervention).toLocaleDateString()}
                        </span>
                      </div>

                      {intervention.problem_description && (
                        <div className="text-sm text-gray-700 mt-2 line-clamp-3">
                          {renderContentWithFiles(intervention.problem_description)}
                        </div>
                      )}

                      {hasMultipleTechs && (
                        <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t">
                          {group.interventions.map((i) => (
                            <div key={`sub-${i.id}`} className="flex items-center gap-2 bg-gray-50 px-2 py-1 rounded border text-xs">
                              <span className="text-gray-600 font-medium">Tech #{i.technicien_id}:</span>
                              <Badge className={getStatusColor(i.statut || 'EN_ATTENTE')} variant="secondary" style={{ fontSize: '10px', height: '18px' }}>
                                {i.statut || 'EN_ATTENTE'}
                              </Badge>
                            </div>
                          ))}
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

                      {(intervention.statut || 'EN_ATTENTE') === 'PENDING_APPROVAL' ? (
                        <>
                          <Button size="sm" onClick={() => approveIntervention(intervention.id)}>
                            Accept
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => {
                              setSelected(intervention);
                              setRejectReason('');
                              setRejectOpen(true);
                            }}
                          >
                            Decline
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>
              )
            })}

            {groupedInterventions.length === 0 && <div className="text-sm text-gray-500">Aucune intervention</div>}
          </div>
        </div>

        <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Détails intervention</DialogTitle>
              <DialogDescription>Revue de la demande d'intervention.</DialogDescription>
            </DialogHeader>
            {selected ? (
              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-gray-500">Statut</div>
                  <div className="font-medium">{selected.statut || 'EN_ATTENTE'}</div>
                </div>
                <div>
                  <div className="text-gray-500">Ordre de travail</div>
                  <div className="font-medium">#{selected.ordre_travail_id}</div>
                </div>
                {typeof selected.machine_id === 'number' && (
                  <div>
                    <div className="text-gray-500">Machine</div>
                    <div className="font-medium">#{selected.machine_id}</div>
                  </div>
                )}
                {selected.priority && (
                  <div>
                    <div className="text-gray-500">Priorité</div>
                    <div className="font-medium">{selected.priority}</div>
                  </div>
                )}
                {typeof selected.estimated_duration_minutes === 'number' && (
                  <div>
                    <div className="text-gray-500">Durée estimée (min)</div>
                    <div className="font-medium">{selected.estimated_duration_minutes}</div>
                  </div>
                )}
                {selected.required_materials && (
                  <div>
                    <div className="text-gray-500">Matériels requis</div>
                    <div className="mt-1 p-2 bg-gray-50 rounded border">
                      {renderContentWithFiles(selected.required_materials)}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-gray-500">Description du problème</div>
                  <div className="mt-1 p-2 bg-gray-50 rounded border">
                    {renderContentWithFiles(selected.problem_description)}
                  </div>
                </div>
                {selected.rejection_reason && (
                  <div>
                    <div className="text-gray-500">Motif de rejet</div>
                    <div className="font-medium whitespace-pre-wrap">{selected.rejection_reason}</div>
                  </div>
                )}

                {selected.is_overdue ? (
                  <div>
                    <div className="text-gray-500">Échéance</div>
                    <div className="font-medium text-red-700">Overdue</div>
                  </div>
                ) : selected.work_order_due_date ? (
                  <div>
                    <div className="text-gray-500">Échéance</div>
                    <div className="font-medium">
                      {new Date(selected.work_order_due_date).toLocaleString()}
                    </div>
                  </div>
                ) : null}

                <div>
                  <div className="text-gray-500">Chrono</div>
                  <div className="font-medium">{formatDuration(getElapsedMs(selected))}</div>
                </div>
              </div>
            ) : null}
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
