import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Edit, Trash2 } from 'lucide-react';
import type { Machine } from '@/lib/types';
import { StatusBadge } from '../utils/badges';

interface AdminMachinesGridProps {
  machines: Machine[];
  onEdit: (machine: Machine) => void;
  onRequestDelete: (machine: Machine) => void;
}

export const AdminMachinesGrid: React.FC<AdminMachinesGridProps> = ({
  machines,
  onEdit,
  onRequestDelete,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {machines.length === 0 ? (
        <div className="col-span-full text-center py-12">
          <p className="text-gray-500">No machines found</p>
        </div>
      ) : (
        machines.map((machine) => (
          <Card key={machine.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">{machine.nom}</CardTitle>
                  <p className="text-sm text-gray-500 mt-1">{machine.identifiant_machine}</p>
                </div>
                <StatusBadge statut={machine.statut} />
              </div>
            </CardHeader>
            <CardContent>
              <img
                src={
                  machine.image_url ||
                  'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'
                }
                alt={machine.nom}
                className="w-full h-48 object-cover rounded-md mb-4"
              />
              <div className="space-y-2 text-sm mb-4">
                <div className="flex justify-between">
                  <span className="text-gray-500">Type:</span>
                  <span className="font-medium">{machine.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Location:</span>
                  <span className="font-medium">{machine.emplacement}</span>
                </div>
                {machine.date_derniere_maintenance && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Last Maintenance:</span>
                    <span className="font-medium">
                      {new Date(machine.date_derniere_maintenance).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {machine.date_prochaine_maintenance && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Next Maintenance:</span>
                    <span className="font-medium text-orange-600">
                      {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1" onClick={() => onEdit(machine)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-red-600 hover:text-red-700"
                  onClick={() => onRequestDelete(machine)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
};
