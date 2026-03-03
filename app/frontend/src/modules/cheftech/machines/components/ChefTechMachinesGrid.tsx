import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Eye, AlertTriangle } from 'lucide-react';
import type { Machine } from '@/lib/types';
import MachineHealthBar from '@/modules/shared/machines/components/MachineHealthBar';
import { computeHealthScore } from '@/modules/shared/machines/utils/healthScore';
import { MachineQRCode } from '@/modules/shared/MachineQRCode';

interface ChefTechMachinesGridProps {
  machines: Machine[];
}

// Helper function to truncate text with title attribute for tooltip
const TruncateText: React.FC<{ text: string; maxLength: number }> = ({ text, maxLength }) => {
  if (text.length <= maxLength) {
    return <span>{text}</span>;
  }

  return (
    <span
      title={text}
      className="cursor-help truncate"
    >
      {text.substring(0, maxLength)}...
    </span>
  );
};

function getMachineStatusConfig(statut = '') {
  const map: Record<string, { label: string; dot: string }> = {
    OPERATIONNELLE: { label: 'Opérationnelle', dot: 'bg-emerald-500' },
    EN_MAINTENANCE: { label: 'En Maintenance', dot: 'bg-amber-500' },
    EN_PANNE: { label: 'En Panne', dot: 'bg-red-500 animate-pulse' },
    HORS_SERVICE: { label: 'Hors Service', dot: 'bg-gray-400' },
  };
  return map[statut] ?? { label: statut || 'Inconnu', dot: 'bg-gray-300' };
}

export const ChefTechMachinesGrid: React.FC<ChefTechMachinesGridProps> = ({ machines }) => {
  const navigate = useNavigate();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {machines.length === 0 ? (
        <div className="col-span-full text-center py-12">
          <p className="text-gray-500">Aucune machine trouvée</p>
        </div>
      ) : (
        machines.map((machine) => {
          const statusConfig = getMachineStatusConfig(machine.statut);
          const health = computeHealthScore(machine);
          const isCritical = health.score < 60;

          return (
            <Card
              key={machine.id}
              className={`hover:shadow-xl transition-all duration-200 group overflow-hidden ${isCritical ? 'ring-1 ring-red-200' : ''
                }`}
            >
              {/* Colored health-score top band */}
              <div className={`h-1 w-full bg-gradient-to-r ${health.colorClass}`} />

              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">
                      <TruncateText text={machine.nom} maxLength={28} />
                    </CardTitle>
                    {machine.ordre && (
                      <p className="text-xs text-gray-400 mt-0.5">Ordre: {machine.ordre}</p>
                    )}
                  </div>
                  {/* Status dot + label */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={`inline-block w-2 h-2 rounded-full ${statusConfig.dot}`} />
                    <span className="text-xs text-gray-500">{statusConfig.label}</span>
                    {isCritical && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Machine image */}
                <img
                  src={
                    machine.image_url ||
                    'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'
                  }
                  alt={machine.nom}
                  className="w-full h-40 object-cover rounded-lg"
                />

                {/* Quick info */}
                <div className="space-y-1.5 text-sm">
                  {machine.type && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Type</span>
                      <span className="font-medium text-gray-800">{machine.type}</span>
                    </div>
                  )}
                  {machine.zone && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Zone</span>
                      <span className="font-medium text-gray-800">
                        {[machine.zone, machine.sous_zone].filter(Boolean).join(' / ')}
                      </span>
                    </div>
                  )}
                  {machine.date_prochaine_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Prochaine maint.</span>
                      <span className={`font-medium ${new Date(machine.date_prochaine_maintenance) < new Date() ? 'text-red-600' : 'text-amber-600'}`}>
                        {new Date(machine.date_prochaine_maintenance).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                  )}
                </div>

                {/* Health Score Bar */}
                <div className="pt-1 border-t border-gray-50">
                  <MachineHealthBar health={health} compact />
                </div>

                {/* Buttons */}
                <div className="flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/machines/${machine.id}`)}
                  >
                    <Eye className="mr-1.5 h-4 w-4" />
                    Voir les détails
                  </Button>
                  <MachineQRCode machine={machine} compact />
                </div>
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
};
