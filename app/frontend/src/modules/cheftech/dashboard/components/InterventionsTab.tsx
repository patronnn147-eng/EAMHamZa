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
import { Wrench } from 'lucide-react';
import { getStatusColor } from '../utils/badges';
import type { Intervention } from '../types';

interface InterventionsTabProps {
  interventions: Intervention[];
  fetchInterventions: (filters?: {
    statut?: string;
  }) => Promise<void>;
  approveIntervention: (interventionId: number) => Promise<void>;
  rejectIntervention: (interventionId: number, reason?: string) => Promise<void>;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  interventions,
  fetchInterventions,
  approveIntervention,
  rejectIntervention,
}) => {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selected, setSelected] = useState<Intervention | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

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
    const start = i.date_debut ? new Date(i.date_debut).getTime() : null;
    if (!start) return 0;
    const end = i.date_fin ? new Date(i.date_fin).getTime() : now;
    return Math.max(0, end - start);
  };

  const pending = useMemo(
    () => interventions.filter((i) => (i.statut || 'EN_ATTENTE') === 'PENDING_APPROVAL'),
    [interventions],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench className="h-5 w-5" />
          Interventions
        </CardTitle>
        <div className="flex gap-4">
          <Select onValueChange={(value) => fetchInterventions({ statut: value })}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
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
            {interventions.map((intervention) => (
              <div key={intervention.id} className="border rounded-lg p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={getStatusColor(intervention.statut || 'EN_ATTENTE')}>
                        {intervention.statut || 'EN_ATTENTE'}
                      </Badge>
                      {intervention.is_overdue ? (
                        <Badge className="bg-red-100 text-red-800">Overdue</Badge>
                      ) : null}
                      <span className="text-sm text-gray-500">Intervention #{intervention.id}</span>
                      <span className="text-sm text-gray-500">Ordre: #{intervention.ordre_travail_id}</span>
                      {typeof intervention.technicien_id === 'number' && (
                        <span className="text-sm text-gray-500">Tech: #{intervention.technicien_id}</span>
                      )}
                      <span className="text-sm text-gray-500">
                        {new Date(intervention.date_intervention).toLocaleDateString()}
                      </span>
                    </div>

                    {intervention.problem_description && (
                      <p className="text-sm text-gray-700 mt-2 line-clamp-2">{intervention.problem_description}</p>
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
            ))}

            {interventions.length === 0 && <div className="text-sm text-gray-500">Aucune intervention</div>}
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
                    <div className="font-medium whitespace-pre-wrap">{selected.required_materials}</div>
                  </div>
                )}
                {selected.problem_description && (
                  <div>
                    <div className="text-gray-500">Description du problème</div>
                    <div className="font-medium whitespace-pre-wrap">{selected.problem_description}</div>
                  </div>
                )}
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
