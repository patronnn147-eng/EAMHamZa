import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, Calendar, Edit, Trash2 } from 'lucide-react';
import type { Machine, OrdreTravail } from '@/lib/types';
import { isOverdue, PriorityBadge, StatusBadge } from '../utils/badges';

interface WorkOrdersListProps {
  workOrders: OrdreTravail[];
  machines: Machine[];
  isAdmin: boolean;
  onEdit: (workOrder: OrdreTravail) => void;
  onRequestDelete: (workOrder: OrdreTravail) => void;
}

export const WorkOrdersList: React.FC<WorkOrdersListProps> = ({
  workOrders,
  machines,
  isAdmin,
  onEdit,
  onRequestDelete,
}) => {
  const getMachineName = (machineId: number) => {
    const machine = machines.find((m) => m.id === machineId);
    return machine ? machine.nom : `Machine #${machineId}`;
  };

  if (workOrders.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <p className="text-gray-500">No work orders found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {workOrders.map((wo) => (
        <Card key={wo.id} className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg flex items-center gap-2">
                  Work Order #{wo.id}
                  {isOverdue(wo.date_echeance, wo.statut) && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                </CardTitle>
                <p className="text-sm text-gray-500 mt-1">{getMachineName(wo.machine_id)}</p>
              </div>
              <div className="flex items-center gap-2">
                <PriorityBadge priorite={wo.priorite} />
                <StatusBadge statut={wo.statut} />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm mb-4">
              <div>
                <p className="text-gray-500 flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  Due Date
                </p>
                <p
                  className={`font-medium mt-1 ${
                    isOverdue(wo.date_echeance, wo.statut) ? 'text-red-600' : ''
                  }`}
                >
                  {new Date(wo.date_echeance).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Created</p>
                <p className="font-medium mt-1">{new Date(wo.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-gray-500">Assigned To</p>
                <p className="font-medium mt-1">
                  {wo.utilisateur_id ? `User #${wo.utilisateur_id}` : 'Unassigned'}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => onEdit(wo)}
              >
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
              {isAdmin && (
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-red-600 hover:text-red-700"
                  onClick={() => onRequestDelete(wo)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
