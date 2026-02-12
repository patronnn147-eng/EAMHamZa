import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Wrench } from 'lucide-react';
import { getStatusColor } from '../utils/badges';
import type { Intervention } from '../types';

interface InterventionsTabProps {
  interventions: Intervention[];
  fetchInterventions: (filters?: {
    statut?: string;
  }) => Promise<void>;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  interventions,
  fetchInterventions,
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
              <SelectItem value="BLOQUÉ">Bloqué</SelectItem>
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
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className={getStatusColor(intervention.statut || 'EN_ATTENTE')}>
                      {intervention.statut || 'EN_ATTENTE'}
                    </Badge>
                    <span className="text-sm text-gray-500">Ordre: #{intervention.ordre_travail_id}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(intervention.date_intervention).toLocaleDateString()}
                    </span>
                  </div>
                  {intervention.rapport && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">{intervention.rapport}</p>
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
