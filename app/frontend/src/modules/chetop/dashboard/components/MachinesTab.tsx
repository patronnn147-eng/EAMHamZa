import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Machine } from '../types';

interface MachinesTabProps {
  machines: Machine[];
}

export const MachinesTab: React.FC<MachinesTabProps> = ({ machines }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Machines</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {machines.map((machine) => (
            <div key={machine.id} className="border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold">{machine.nom}</h3>
                {machine.statut && (
                  <Badge variant={machine.statut === 'hors_service' ? 'destructive' : 'secondary'}>
                    {machine.statut.replace('_', ' ')}
                  </Badge>
                )}
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                {machine.type && <p>Type: {machine.type}</p>}
                {machine.emplacement && <p>Emplacement: {machine.emplacement}</p>}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
