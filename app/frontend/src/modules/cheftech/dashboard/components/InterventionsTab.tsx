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
import { UserCheck, Wrench } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/badges';
import type { Intervention, Technician } from '../types';

interface InterventionsTabProps {
  interventions: Intervention[];
  technicians: Technician[];
  selectedTechnician: number | null;
  selectedIntervention: number | null;
  setSelectedTechnician: React.Dispatch<React.SetStateAction<number | null>>;
  setSelectedIntervention: React.Dispatch<React.SetStateAction<number | null>>;
  fetchInterventions: (filters?: {
    statut?: string;
    priorite?: string;
    technicien_id?: number;
  }) => Promise<void>;
  assignTechnician: (interventionId: number, technicianId: number) => Promise<void>;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  interventions,
  technicians,
  selectedTechnician,
  selectedIntervention,
  setSelectedTechnician,
  setSelectedIntervention,
  fetchInterventions,
  assignTechnician,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench className="h-5 w-5" />
          Interventions
        </CardTitle>
        <div className="flex gap-4">
          <Select onValueChange={(value) => fetchInterventions({ statut: value })}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EN_ATTENTE">En attente</SelectItem>
              <SelectItem value="EN_COURS">En cours</SelectItem>
              <SelectItem value="TERMINÉ">Terminé</SelectItem>
            </SelectContent>
          </Select>
          <Select onValueChange={(value) => fetchInterventions({ priorite: value })}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filtrer par priorité" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="URGENTE">Urgente</SelectItem>
              <SelectItem value="ÉLEVÉE">Élevée</SelectItem>
              <SelectItem value="MOYENNE">Moyenne</SelectItem>
              <SelectItem value="BASSE">Basse</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {interventions.map((intervention) => (
            <div key={intervention.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold">{intervention.titre}</h3>
                  <p className="text-sm text-gray-600">{intervention.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getPriorityColor(intervention.priorite)}>
                      {intervention.priorite}
                    </Badge>
                    <Badge className={getStatusColor(intervention.statut)}>
                      {intervention.statut}
                    </Badge>
                    {intervention.machine_nom && (
                      <span className="text-sm text-gray-500">
                        Machine: {intervention.machine_nom}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {intervention.technicien_nom ? (
                    <div className="text-sm">
                      <span className="font-medium">{intervention.technicien_nom}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Select
                        value={
                          selectedIntervention === intervention.id
                            ? selectedTechnician?.toString()
                            : ''
                        }
                        onValueChange={(value) => {
                          setSelectedIntervention(intervention.id);
                          setSelectedTechnician(parseInt(value));
                        }}
                      >
                        <SelectTrigger className="w-40">
                          <SelectValue placeholder="Assigner" />
                        </SelectTrigger>
                        <SelectContent>
                          {technicians.map((tech) => (
                            <SelectItem key={tech.id} value={tech.id.toString()}>
                              {tech.nom}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {selectedIntervention === intervention.id && selectedTechnician && (
                        <Button
                          size="sm"
                          onClick={() => {
                            assignTechnician(intervention.id, selectedTechnician);
                            setSelectedIntervention(null);
                            setSelectedTechnician(null);
                          }}
                        >
                          <UserCheck className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
