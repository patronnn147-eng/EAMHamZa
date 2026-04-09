import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Machine, OrdreTravail } from '@/lib/types';

interface WorkOrderDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workOrder: OrdreTravail | null;
  machines: Machine[];
}

export const WorkOrderDetailsDialog: React.FC<WorkOrderDetailsDialogProps> = ({
  open,
  onOpenChange,
  workOrder,
  machines,
}) => {
  const machineName = workOrder
    ? machines.find((m) => m.id === workOrder.machine_id)?.nom || `Machine #${workOrder.machine_id}`
    : '';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Work Order Details</DialogTitle>
        </DialogHeader>

        {workOrder ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-blue-300">ID</div>
                <div className="font-medium">#{workOrder.id}</div>
              </div>
              <div>
                <div className="text-xs text-blue-300">Machine</div>
                <div className="font-medium">{machineName}</div>
              </div>
              <div>
                <div className="text-xs text-blue-300">Priority</div>
                <div className="font-medium">{workOrder.priorite}</div>
              </div>
              <div>
                <div className="text-xs text-blue-300">Status</div>
                <div className="font-medium">{workOrder.statut}</div>
              </div>
              <div>
                <div className="text-xs text-blue-300">Due date</div>
                <div className="font-medium">
                  {workOrder.date_echeance ? new Date(workOrder.date_echeance).toLocaleDateString() : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-blue-300">Assigned user</div>
                <div className="font-medium">{workOrder.utilisateur_id ? `User #${workOrder.utilisateur_id}` : '—'}</div>
              </div>
            </div>

            <div>
              <div className="text-xs text-blue-300">Title</div>
              <div className="font-medium">{workOrder.titre}</div>
            </div>

            <div>
              <div className="text-xs text-blue-300">Description</div>
              <div className="whitespace-pre-wrap text-sm">{workOrder.description}</div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-blue-300">No work order selected.</div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
