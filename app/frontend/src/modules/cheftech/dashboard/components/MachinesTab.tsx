import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Settings } from 'lucide-react';
import { getStatusColor } from '../utils/badges';
import type { Machine } from '../types';

interface MachinesTabProps {
  machines: Machine[];
  fetchMachines: (filters?: { statut?: string; maintenance_required?: boolean }) => Promise<void>;
  updateMachineStatus: (machineId: number, status: string) => Promise<void>;
}

export const MachinesTab: React.FC<MachinesTabProps> = ({
  machines,
  fetchMachines,
  updateMachineStatus,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Machines
        </CardTitle>
        <div className="flex gap-4">
          <Button variant="outline" onClick={() => fetchMachines()}>
            Toutes
          </Button>
          <Button variant="outline" onClick={() => fetchMachines({ maintenance_required: true })}>
            Maintenance requise
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {machines.map((machine) => (
            <div key={machine.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{machine.nom}</h3>
                  <p className="text-sm text-gray-600">
                    {machine.type} • {machine.emplacement}
                  </p>
                  {machine.date_prochaine_maintenance && (
                    <p className="text-xs text-gray-500">
                      Prochaine maintenance:{' '}
                      {new Date(machine.date_prochaine_maintenance).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={getStatusColor(machine.statut)}>{machine.statut}</Badge>
                  <Select onValueChange={(value) => updateMachineStatus(machine.id, value)}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Statut" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ACTIF">Actif</SelectItem>
                      <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                      <SelectItem value="CRITIQUE">Critique</SelectItem>
                      <SelectItem value="HORS_SERVICE">Hors service</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
