import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Edit, FileText, Trash2 } from 'lucide-react';
import type { Intervention, OrdreTravail } from '@/lib/types';

interface InterventionsListProps {
  interventions: Intervention[];
  workOrders: OrdreTravail[];
  isAdmin: boolean;
  onEdit: (intervention: Intervention) => void;
  onRequestDelete: (intervention: Intervention) => void;
}

export const InterventionsList: React.FC<InterventionsListProps> = ({
  interventions,
  workOrders,
  isAdmin,
  onEdit,
  onRequestDelete,
}) => {
  const getWorkOrderInfo = (ordreId: number) => {
    const workOrder = workOrders.find((wo) => wo.id === ordreId);
    return workOrder ? `Work Order #${workOrder.id}` : `Work Order #${ordreId}`;
  };

  if (interventions.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <p className="text-gray-500">No interventions found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {interventions.map((intervention) => (
        <Card key={intervention.id} className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  Intervention #{intervention.id}
                </CardTitle>
                <p className="text-sm text-gray-500 mt-1">{getWorkOrderInfo(intervention.ordre_travail_id)}</p>
              </div>
              <Badge variant="outline" className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(intervention.date_intervention).toLocaleDateString()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Report:</h4>
              <p className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                {intervention.rapport}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1" onClick={() => onEdit(intervention)}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
              {isAdmin && (
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-red-600 hover:text-red-700"
                  onClick={() => onRequestDelete(intervention)}
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
