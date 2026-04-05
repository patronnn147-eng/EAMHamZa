import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Activity,
  AlertTriangle,
  TrendingDown,
  CheckCircle2,
  ArrowUpDown,
  Filter,
} from 'lucide-react';
import type { FleetMachineCard } from '@/lib/types';
import { MachineDetailPanel } from './MachineDetailPanel';

interface FleetOverviewProps {
  machines: FleetMachineCard[];
  summary: {
    totalMachines: number;
    criticalCount: number;
    highRiskCount: number;
    avgHealthScore: number;
    avgReliabilityScore: number;
  };
}

type RiskFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
type SortField = 'health' | 'rul' | 'risk';

const riskConfig: Record<string, { label: string; color: string; bg: string; border: string; order: number }> = {
  CRITICAL: { label: 'Critique', color: 'text-red-700', bg: 'bg-red-100', border: 'border-red-200', order: 0 },
  HIGH: { label: 'Élevé', color: 'text-orange-700', bg: 'bg-orange-100', border: 'border-orange-200', order: 1 },
  MEDIUM: { label: 'Modéré', color: 'text-amber-700', bg: 'bg-amber-100', border: 'border-amber-200', order: 2 },
  LOW: { label: 'Faible', color: 'text-emerald-700', bg: 'bg-emerald-100', border: 'border-emerald-200', order: 3 },
};

function getHealthBarColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-blue-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
}

function getHealthTextColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-blue-600';
  if (score >= 40) return 'text-amber-600';
  return 'text-red-600';
}

export const FleetOverview: React.FC<FleetOverviewProps> = ({ machines, summary }) => {
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('ALL');
  const [sortField, setSortField] = useState<SortField>('health');
  const [selectedMachine, setSelectedMachine] = useState<FleetMachineCard | null>(null);

  const filteredMachines = machines.filter((m) => {
    if (riskFilter === 'ALL') return true;
    return m.ml.risk_level === riskFilter;
  });

  const sortedMachines = [...filteredMachines].sort((a, b) => {
    switch (sortField) {
      case 'health':
        return b.ml.health_score - a.ml.health_score;
      case 'rul':
        return a.ml.rul_days - b.ml.rul_days;
      case 'risk':
        return (riskConfig[a.ml.risk_level]?.order ?? 3) - (riskConfig[b.ml.risk_level]?.order ?? 3);
      default:
        return 0;
    }
  });

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm border-l-4 border-l-blue-500">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Machines</p>
              <Activity className="h-4 w-4 text-blue-500" />
            </div>
            <p className="text-3xl font-black text-gray-900">{summary.totalMachines}</p>
            <p className="text-xs text-gray-400 mt-1">Flotte complète</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-l-4 border-l-red-500">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Risque Critique</p>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </div>
            <p className="text-3xl font-black text-red-600">{summary.criticalCount}</p>
            <p className="text-xs text-gray-400 mt-1">Action immédiate requise</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-l-4 border-l-orange-500">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Risque Élevé</p>
              <TrendingDown className="h-4 w-4 text-orange-500" />
            </div>
            <p className="text-3xl font-black text-orange-600">{summary.highRiskCount}</p>
            <p className="text-xs text-gray-400 mt-1">Surveillance accrue</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-l-4 border-l-emerald-500">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Santé Moyenne</p>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </div>
            <p className="text-3xl font-black text-emerald-600">{Math.round(summary.avgHealthScore)}</p>
            <p className="text-xs text-gray-400 mt-1">Score sur 100</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter & Sort Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-600">Filtrer:</span>
          <div className="flex gap-1">
            {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as RiskFilter[]).map((level) => (
              <Button
                key={level}
                variant={riskFilter === level ? 'default' : 'outline'}
                size="sm"
                onClick={() => setRiskFilter(level)}
                className={`text-xs h-7 ${
                  riskFilter === level
                    ? level === 'CRITICAL'
                      ? 'bg-red-600 hover:bg-red-700'
                      : level === 'HIGH'
                      ? 'bg-orange-500 hover:bg-orange-600'
                      : level === 'MEDIUM'
                      ? 'bg-amber-500 hover:bg-amber-600'
                      : level === 'LOW'
                      ? 'bg-emerald-500 hover:bg-emerald-600'
                      : ''
                    : ''
                }`}
              >
                {level === 'ALL' ? 'Toutes' : riskConfig[level]?.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 sm:ml-auto">
          <ArrowUpDown className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-600">Trier:</span>
          <div className="flex gap-1">
            {([
              { key: 'health' as SortField, label: 'Santé' },
              { key: 'rul' as SortField, label: 'RUL' },
              { key: 'risk' as SortField, label: 'Risque' },
            ]).map((opt) => (
              <Button
                key={opt.key}
                variant={sortField === opt.key ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortField(opt.key)}
                className="text-xs h-7"
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Machine Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sortedMachines.map((machine) => {
          const rc = riskConfig[machine.ml.risk_level] || riskConfig.LOW;
          return (
            <Card
              key={machine.id}
              className={`cursor-pointer hover:shadow-md transition-shadow border ${rc.border} hover:border-blue-300`}
              onClick={() => setSelectedMachine(machine)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-sm font-bold text-gray-900 truncate">{machine.nom}</CardTitle>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {[machine.zone, machine.sous_zone].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <Badge className={`shrink-0 ml-2 text-[10px] px-1.5 py-0 ${rc.bg} ${rc.color} border-0`}>
                    {rc.label}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Health Score */}
                <div className="space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">Santé</span>
                    <span className={`text-sm font-bold ${getHealthTextColor(machine.ml.health_score)}`}>
                      {Math.round(machine.ml.health_score)}/100
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${getHealthBarColor(machine.ml.health_score)}`}
                      style={{ width: `${Math.min(100, machine.ml.health_score)}%` }}
                    />
                  </div>
                </div>

                {/* RUL & Reliability */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="text-center p-2 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500">RUL</p>
                    <p className={`text-lg font-black ${machine.ml.rul_days <= 7 ? 'text-red-600' : 'text-gray-800'}`}>
                      {Math.round(machine.ml.rul_days)}j
                    </p>
                  </div>
                  <div className="text-center p-2 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500">Fiabilité</p>
                    <p className="text-lg font-black text-gray-800">
                      {Math.round(machine.ml.reliability_score)}
                    </p>
                  </div>
                </div>

                {/* Anomaly indicator */}
                {machine.ml.is_anomaly && (
                  <div className="flex items-center gap-1.5 text-xs text-purple-600 bg-purple-50 px-2 py-1 rounded">
                    <AlertTriangle className="h-3 w-3" />
                    <span>Anomalie détectée (score: {machine.ml.anomaly_score?.toFixed(2)})</span>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {sortedMachines.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Activity className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg">Aucune machine trouvée pour ce filtre</p>
        </div>
      )}

      {/* Machine Detail Panel */}
      {selectedMachine && (
        <MachineDetailPanel
          machine={selectedMachine}
          onClose={() => setSelectedMachine(null)}
        />
      )}
    </div>
  );
};
