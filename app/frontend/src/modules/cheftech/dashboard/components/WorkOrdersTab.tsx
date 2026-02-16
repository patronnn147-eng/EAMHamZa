import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Activity, Users } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/badges';
import type { Machine, Technician, WorkOrder } from '../types';

const getAuthToken = () => localStorage.getItem('access_token');

interface WorkOrdersTabProps {
  workOrders: WorkOrder[];
  technicians: Technician[];
  machines: Machine[];
  assignWorkOrder: (
    ordreId: number,
    technicienIds: number[],
    machineIds: number[],
    estimatedCompletionDate?: string,
  ) => Promise<void>;
}

export const WorkOrdersTab: React.FC<WorkOrdersTabProps> = ({ workOrders, technicians, machines, assignWorkOrder }) => {
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [selectedTechIds, setSelectedTechIds] = useState<number[]>([]);
  const [selectedMachineIds, setSelectedMachineIds] = useState<number[]>([]);
  const [estimatedDate, setEstimatedDate] = useState<string>('');

  const sortedTechs = useMemo(
    () => [...technicians].sort((a, b) => a.nom.localeCompare(b.nom)),
    [technicians],
  );

  const displayedTechs = useMemo(() => {
    if (selectedTechIds.length === 0) return sortedTechs;
    const allowed = new Set(selectedTechIds);
    const filtered = sortedTechs.filter((t) => allowed.has(t.id));
    return filtered.length > 0 ? filtered : sortedTechs;
  }, [selectedTechIds, sortedTechs]);

  const openAssign = async (order: WorkOrder) => {
    setSelectedOrder(order);
    setSelectedMachineIds(order.machine_id ? [order.machine_id] : []);
    setEstimatedDate(order.date_echeance ? order.date_echeance.slice(0, 10) : '');

    // Preselect technicians already linked to this work order (if any)
    try {
      const token = getAuthToken();
      if (!token) {
        setSelectedTechIds([]);
      } else {
        const resp = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/entities/ordres_intervention?query=${encodeURIComponent(
            JSON.stringify({ ordre_travail_id: order.id }),
          )}&limit=2000`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (!resp.ok) {
          setSelectedTechIds([]);
        } else {
          const raw = (await resp.json()) as unknown;
          const unwrap = (value: unknown): unknown => {
            let current = value;
            for (let i = 0; i < 5; i += 1) {
              if (!current || typeof current !== 'object') return current;
              if (Array.isArray(current)) return current;
              const obj = current as Record<string, unknown>;
              if ('items' in obj && Array.isArray(obj.items)) return obj;
              if ('data' in obj) {
                current = obj.data;
                continue;
              }
              return current;
            }
            return current;
          };

          const extracted = unwrap(raw) as { items?: Array<{ technicien_id?: number | null }> } | undefined;
          const techIds = (extracted?.items || [])
            .map((i) => i.technicien_id)
            .filter((id): id is number => typeof id === 'number');
          setSelectedTechIds(Array.from(new Set(techIds)));
        }
      }
    } catch {
      setSelectedTechIds([]);
    }

    setAssignOpen(true);
  };

  const toggleTech = (id: number) => {
    setSelectedTechIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleMachine = (id: number) => {
    setSelectedMachineIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const submitAssign = async () => {
    if (!selectedOrder) return;
    await assignWorkOrder(selectedOrder.id, selectedTechIds, selectedMachineIds, estimatedDate || undefined);
    setAssignOpen(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Ordres de travail
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {workOrders.map((order) => (
            <div key={order.id} className="border rounded-lg p-4">
              <h3 className="font-semibold">{order.titre}</h3>
              <p className="text-sm text-gray-600">{order.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge className={getPriorityColor(order.priorite)}>{order.priorite}</Badge>
                <Badge className={getStatusColor(order.statut)}>{order.statut}</Badge>
                {order.machine_nom && (
                  <span className="text-sm text-gray-500">Machine: {order.machine_nom}</span>
                )}
              </div>

              <div className="mt-3">
                <Button variant="outline" size="sm" onClick={() => void openAssign(order)}>
                  <Users className="mr-2 h-4 w-4" />
                  Assigner
                </Button>
              </div>
            </div>
          ))}
        </div>

        <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Assigner l'ordre de travail</DialogTitle>
              <DialogDescription>
                Sélectionne un ou plusieurs techniciens. Le système créera automatiquement les interventions.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="grid gap-2">
                <Label>Date estimée de fin (optionnel)</Label>
                <Input type="date" value={estimatedDate} onChange={(e) => setEstimatedDate(e.target.value)} />
              </div>

              <div className="space-y-2">
                <Label>Machines</Label>
                <div className="max-h-48 overflow-auto border rounded-md p-2 space-y-2">
                  {machines.map((m) => (
                    <label key={m.id} className="flex items-center gap-2 text-sm">
                      <Checkbox checked={selectedMachineIds.includes(m.id)} onCheckedChange={() => toggleMachine(m.id)} />
                      <span>
                        {m.nom} (#{m.id})
                      </span>
                    </label>
                  ))}
                  {machines.length === 0 && <p className="text-sm text-gray-500">Aucune machine</p>}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Techniciens</Label>
                <div className="max-h-64 overflow-auto border rounded-md p-2 space-y-2">
                  {displayedTechs.map((t) => (
                    <label key={t.id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedTechIds.includes(t.id)}
                        onCheckedChange={() => toggleTech(t.id)}
                      />
                      <span>{t.nom}</span>
                    </label>
                  ))}
                  {displayedTechs.length === 0 && (
                    <p className="text-sm text-gray-500">Aucun technicien disponible</p>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAssignOpen(false)}>
                Annuler
              </Button>
              <Button
                onClick={submitAssign}
                disabled={!selectedOrder || selectedTechIds.length === 0 || selectedMachineIds.length === 0}
              >
                Assigner
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};
