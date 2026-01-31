import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Users } from 'lucide-react';
import type { Technician } from '../types';

interface TechniciansTabProps {
  technicians: Technician[];
  fetchTechnicians: (disponible?: boolean) => Promise<void>;
}

export const TechniciansTab: React.FC<TechniciansTabProps> = ({
  technicians,
  fetchTechnicians,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Techniciens
        </CardTitle>
        <div className="flex gap-4">
          <Button variant="outline" onClick={() => fetchTechnicians()}>
            Tous
          </Button>
          <Button variant="outline" onClick={() => fetchTechnicians(true)}>
            Disponibles
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {technicians.map((technician) => (
            <div key={technician.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{technician.nom}</h3>
                  <p className="text-sm text-gray-600">{technician.email}</p>
                </div>
                <Badge className="bg-green-100 text-green-800">Disponible</Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
