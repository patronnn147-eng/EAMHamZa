import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Edit, Eye } from 'lucide-react';
import type { WorkOrder } from '../types';
import { getPriorityColor, getStatusColor, getStatusIcon } from '../utils/badges';

interface WorkOrdersTabProps {
  workOrders: WorkOrder[];
  onSelectOrder: (order: WorkOrder) => void;
}

export const WorkOrdersTab: React.FC<WorkOrdersTabProps> = ({ workOrders, onSelectOrder }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ordres de Travail</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {workOrders.map((order) => (
            <div key={order.id} className="border rounded-lg p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{order.titre}</h3>
                    <Badge className={getPriorityColor(order.priorite)}>{order.priorite}</Badge>
                    <div
                      className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${getStatusColor(order.statut)}`}
                    >
                      {getStatusIcon(order.statut)}
                      <span>{order.statut.replace('_', ' ')}</span>
                    </div>
                  </div>
                  <p className="text-gray-600 text-sm mb-2">{order.description}</p>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>Machine: {order.machine_nom || `ID: ${order.machine_id}`}</span>
                    {order.utilisateur_nom && <span>Assigné à: {order.utilisateur_nom}</span>}
                    <span>Créé: {new Date(order.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => onSelectOrder(order)}>
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm">
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
