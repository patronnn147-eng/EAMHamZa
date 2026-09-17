import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Edit, Trash2, Eye, AlertTriangle } from 'lucide-react';
import type { Machine } from '@/lib/types';
import MachineHealthBar from '@/modules/shared/machines/components/MachineHealthBar';
import { computeHealthScore } from '@/modules/shared/machines/utils/healthScore';
import { MachineQRCode } from '@/modules/shared/MachineQRCode';

interface AdminMachinesGridProps {
  machines: Machine[];
  fleetPredictions?: Record<number, any>;
  onEdit: (machine: Machine) => void;
  onRequestDelete: (machine: Machine) => void;
}

const TruncateText: React.FC<{ text: string; maxLength: number }> = ({ text, maxLength }) => {
  if (text.length <= maxLength) return <span>{text}</span>;
  return <span title={text} className="cursor-help truncate">{text.substring(0, maxLength)}...</span>;
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

export const AdminMachinesGrid: React.FC<AdminMachinesGridProps> = ({
  machines,
  fleetPredictions = {},
  onEdit,
  onRequestDelete,
}) => {
  const navigate = useNavigate();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {machines.length === 0 ? (
        <div className="col-span-full text-center py-12">
          <p className="text-blue-300">Aucune machine trouvée</p>
        </div>
      ) : (
        machines.map((machine) => {
          const statusConfig = getMachineStatusConfig(machine.statut);
          const health = computeHealthScore(machine);

          // Override health score with ML prediction if available
          const prediction = fleetPredictions[machine.id];
          if (prediction?.health_score !== undefined) {
            health.score = Math.round(prediction.health_score);
            if (health.score < 60) {
              health.label = 'Critique (IA)';
              health.colorClass = 'from-red-400 to-red-600';
            } else if (health.score < 80) {
              health.label = 'Attention (IA)';
              health.colorClass = 'from-amber-400 to-amber-600';
            } else {
              health.label = 'Bonne (IA)';
              health.colorClass = 'from-emerald-400 to-emerald-600';
            }
          }

          const isCritical = health.score < 60;

          let riskLevelClass = 'bg-emerald-100 text-emerald-700';
          if (prediction?.risk_level === 'CRITICAL') {
            riskLevelClass = 'bg-red-100 text-red-700';
          } else if (prediction?.risk_level === 'HIGH') {
            riskLevelClass = 'bg-orange-100 text-orange-700';
          } else if (prediction?.risk_level === 'MEDIUM') {
            riskLevelClass = 'bg-amber-100 text-amber-700';
          }

          return (
            <Card
              key={machine.id}
              className={`bg-gradient-to-br from-slate-800 to-blue-900 border-blue-700 hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-200 overflow-hidden ${isCritical ? 'ring-1 ring-red-500' : ''}`}
            >
              <div className={`h-1 w-full bg-gradient-to-r ${health.colorClass}`} />

              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate text-white">
                      <TruncateText text={machine.nom} maxLength={28} />
                    </CardTitle>
                    {machine.ordre && (
                      <p className="text-xs text-blue-300 mt-0.5">Ordre: {machine.ordre}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={`inline-block w-2 h-2 rounded-full ${statusConfig.dot}`} />
                    <span className="text-xs text-blue-300">{statusConfig.label}</span>
                    {isCritical && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <img
                  src={
                    machine.image_url ||
                    'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'
                  }
                  alt={machine.nom}
                  className="w-full h-40 object-cover rounded-lg ring-2 ring-blue-500/30"
                />
                <div className="space-y-1.5 text-sm">
                  {machine.type && (
                    <div className="flex justify-between">
                      <span className="text-blue-300">Type</span>
                      <span className="font-medium text-white">{machine.type}</span>
                    </div>
                  )}
                  {machine.zone && (
                    <div className="flex justify-between">
                      <span className="text-blue-300">Zone</span>
                      <span className="font-medium text-blue-100">
                        {[machine.zone, machine.sous_zone].filter(Boolean).join(' / ')}
                      </span>
                    </div>
                  )}
                  {prediction?.risk_level && (
                    <div className="flex justify-between">
                      <span className="text-blue-300">Risque IA</span>
                      <span className={`font-bold text-xs px-1.5 py-0.5 rounded ${riskLevelClass}`}>
                        {prediction.risk_level}
                      </span>
                    </div>
                  )}
                  {machine.date_prochaine_maintenance && (
                    <div className="flex justify-between">
                      <span className="text-blue-300">Prochaine maint.</span>
                      <span className={`font-medium ${new Date(machine.date_prochaine_maintenance) < new Date() ? 'text-red-400' : 'text-amber-400'}`}>
                        {new Date(machine.date_prochaine_maintenance).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                  )}
                </div>

                <div className="pt-1 border-t border-blue-700/50">
                  <MachineHealthBar health={health} compact />
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                    onClick={() => navigate(`/machines/${machine.id}`)}
                  >
                    <Eye className="mr-1.5 h-4 w-4" />
                    Voir
                  </Button>
                  <Button variant="outline" size="sm" className="bg-blue-700/40 border-blue-600 text-blue-100 hover:bg-blue-600 hover:text-white" onClick={() => onEdit(machine)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <MachineQRCode machine={machine} compact />
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-red-900/40 border-red-700 text-red-200 hover:bg-red-800"
                    onClick={() => onRequestDelete(machine)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
};
