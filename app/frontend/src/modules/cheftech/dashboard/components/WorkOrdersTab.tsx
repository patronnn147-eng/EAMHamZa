import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Activity, Users, Calendar, Eye } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/badges';
import type { Machine, Technician, WorkOrder } from '../types';

const getAuthToken = () => localStorage.getItem('access_token');

interface WorkOrdersTabProps {
  workOrders: WorkOrder[];
  technicians: Technician[];
  machines: Machine[];
  assignWorkOrder?: (
    ordreId: number,
    technicienIds: number[],
    machineIds: number[],
    estimatedCompletionDate?: string,
  ) => Promise<void>;
  validateWorkOrder?: (ordreId: number, technicianId: number) => Promise<void>;
  rejectWorkOrder?: (ordreId: number, reason?: string) => Promise<void>;
}

export const WorkOrdersTab: React.FC<WorkOrdersTabProps> = ({ 
  workOrders, 
  technicians, 
  machines, 
  assignWorkOrder,
  validateWorkOrder,
  rejectWorkOrder
}) => {
  const navigate = useNavigate();
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [selectedTechs, setSelectedTechs] = useState<Record<number, string>>({});

  const sortedTechs = useMemo(
    () => [...technicians].sort((a, b) => a.nom.localeCompare(b.nom)),
    [technicians],
  );

  const pendingAssignments = useMemo(
    () => (workOrders || []).filter((wo) => wo.utilisateur_id == null),
    [workOrders],
  );

  const handleTechSelection = (orderId: number, techId: string) => {
    setSelectedTechs((prev) => ({ ...prev, [orderId]: techId }));
  };

  const handleAssign = async (order: WorkOrder) => {
    const techIdStr = selectedTechs[order.id];
    if (!techIdStr || !validateWorkOrder) return;
    
    await validateWorkOrder(order.id, parseInt(techIdStr, 10));
    
    // Clear selection on success
    setSelectedTechs((prev) => {
      const next = { ...prev };
      delete next[order.id];
      return next;
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Unassigned Work Orders
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-amber-600">A assigner: {pendingAssignments.length}</div>
          </div>
          {pendingAssignments.map((order) => {
            const isPreventive = order.titre.startsWith('[PRÉVENTIF]');
            return (
              <div
                key={order.id}
                className={`border rounded-lg p-4 ${isPreventive ? 'border-amber-300 bg-amber-50' : ''}`}
              >
                <h3 className="font-semibold">{order.titre}</h3>
                <p className="text-sm text-blue-200">{order.description}</p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <Badge className={getPriorityColor(order.priorite)}>{order.priorite}</Badge>
                  <Badge className={getStatusColor(order.statut)}>
                    {order.statut === 'EN_ATTENTE' ? 'A VALIDER' : order.statut}
                  </Badge>
                  {isPreventive && (
                    <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-[10px] flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Maintenance Automatisée
                    </Badge>
                  )}
                  {order.machine_nom && (
                    <span className="text-sm text-blue-300">Machine: {order.machine_nom}</span>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between p-3 bg-slate-800/50 border rounded gap-4">
                  {validateWorkOrder && (
                    <div className="flex-1 max-w-sm">
                      <Select
                        value={selectedTechs[order.id] || ''}
                        onValueChange={(val) => handleTechSelection(order.id, val)}
                      >
                        <SelectTrigger className="bg-slate-800">
                          <SelectValue placeholder="Sélectionner un technicien" />
                        </SelectTrigger>
                        <SelectContent>
                          {sortedTechs.map((tech) => (
                            <SelectItem key={`tech-${tech.id}`} value={tech.id.toString()}>
                              {tech.nom}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    {validateWorkOrder && (
                      <Button
                        size="sm"
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                        disabled={!selectedTechs[order.id]}
                        onClick={() => void handleAssign(order)}
                      >
                        <Users className="mr-2 h-4 w-4" />
                        Assigner
                      </Button>
                    )}
                    
                    {rejectWorkOrder && (
                      <Button 
                        variant="destructive" 
                        size="sm"
                        onClick={() => {
                          setSelectedOrder(order);
                          setRejectReason('');
                          setRejectOpen(true);
                        }}
                      >
                        Rejeter
                      </Button>
                    )}

                    <Button variant="ghost" size="sm" onClick={() => navigate(`/work-orders/${order.id}`)}>
                      <Eye className="mr-2 h-4 w-4" />
                      Détails
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
          {pendingAssignments.length === 0 && (
            <div className="text-sm text-blue-300 text-center py-8">Aucun ordre de travail en attente d'assignation.</div>
          )}
        </div>
        <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Rejeter l'ordre de travail</DialogTitle>
              <DialogDescription>Ajoutez un motif de rejet pour informer le ChefOp.</DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label>Motif du rejet</Label>
              <Input 
                placeholder="Ex: Description insuffisante, priorité trop basse..." 
                value={rejectReason} 
                onChange={(e) => setRejectReason(e.target.value)} 
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRejectOpen(false)}>Annuler</Button>
              <Button 
                variant="destructive" 
                onClick={async () => {
                  if (selectedOrder) {
                    await rejectWorkOrder(selectedOrder.id, rejectReason);
                    setRejectOpen(false);
                  }
                }}
              >
                Rejeter l'ordre
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};
