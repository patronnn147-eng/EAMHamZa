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
import type { Technician, WorkOrder } from '../types';

interface WorkOrdersTabProps {
  workOrders: WorkOrder[];
  technicians: Technician[];
  assignWorkOrder: (ordreId: number, technicienIds: number[], estimatedCompletionDate?: string) => Promise<void>;
}

export const WorkOrdersTab: React.FC<WorkOrdersTabProps> = ({ workOrders, technicians, assignWorkOrder }) => {
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [selectedTechIds, setSelectedTechIds] = useState<number[]>([]);
  const [estimatedDate, setEstimatedDate] = useState<string>('');

  const sortedTechs = useMemo(
    () => [...technicians].sort((a, b) => a.nom.localeCompare(b.nom)),
    [technicians],
  );

  const openAssign = (order: WorkOrder) => {
    setSelectedOrder(order);
    setSelectedTechIds([]);
    setEstimatedDate(order.date_echeance ? order.date_echeance.slice(0, 10) : '');
    setAssignOpen(true);
  };

  const toggleTech = (id: number) => {
    setSelectedTechIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const submitAssign = async () => {
    if (!selectedOrder) return;
    await assignWorkOrder(selectedOrder.id, selectedTechIds, estimatedDate || undefined);
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
                <Button variant="outline" size="sm" onClick={() => openAssign(order)}>
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
                <Label>Techniciens</Label>
                <div className="max-h-64 overflow-auto border rounded-md p-2 space-y-2">
                  {sortedTechs.map((t) => (
                    <label key={t.id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedTechIds.includes(t.id)}
                        onCheckedChange={() => toggleTech(t.id)}
                      />
                      <span>{t.nom}</span>
                    </label>
                  ))}
                  {sortedTechs.length === 0 && (
                    <p className="text-sm text-gray-500">Aucun technicien disponible</p>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAssignOpen(false)}>
                Annuler
              </Button>
              <Button onClick={submitAssign} disabled={!selectedOrder || selectedTechIds.length === 0}>
                Assigner
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};
