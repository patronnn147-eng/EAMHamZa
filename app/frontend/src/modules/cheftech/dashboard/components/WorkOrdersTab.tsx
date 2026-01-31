import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/badges';
import type { WorkOrder } from '../types';

interface WorkOrdersTabProps {
  workOrders: WorkOrder[];
}

export const WorkOrdersTab: React.FC<WorkOrdersTabProps> = ({ workOrders }) => {
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
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
