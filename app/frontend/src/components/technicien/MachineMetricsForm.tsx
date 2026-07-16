import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Thermometer, Activity, Gauge, Zap, FileText } from 'lucide-react';

interface MachineMetricsFormProps {
  formData: TelemetryFormData;
  onChange: (data: TelemetryFormData) => void;
}

export interface TelemetryFormData {
  air_temperature?: number;
  process_temperature?: number;
  rotational_speed?: number;
  torque?: number;
  tool_wear?: number;
  notes?: string;
}

export const MachineMetricsForm: React.FC<MachineMetricsFormProps> = ({ formData, onChange }) => {
  const handleChange = (field: keyof TelemetryFormData, value: string | number) => {
    onChange({ ...formData, [field]: value });
  };

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Machine Metrics (Optional)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="space-y-2">
            <Label htmlFor="air_temperature" className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              Temp. Air (K)
            </Label>
            <Input
              id="air_temperature"
              type="number"
              step="0.1"
              min="250"
              max="400"
              placeholder="298.0"
              value={formData.air_temperature ?? ''}
              onChange={(e) => handleChange('air_temperature', Number.parseFloat(e.target.value) || undefined)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="process_temperature" className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              Temp. Process (K)
            </Label>
            <Input
              id="process_temperature"
              type="number"
              step="0.1"
              min="250"
              max="450"
              placeholder="308.0"
              value={formData.process_temperature ?? ''}
              onChange={(e) => handleChange('process_temperature', Number.parseFloat(e.target.value) || undefined)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rotational_speed" className="flex items-center gap-1">
              <Gauge className="h-3 w-3" />
              Vitesse (RPM)
            </Label>
            <Input
              id="rotational_speed"
              type="number"
              step="1"
              min="0"
              max="10000"
              placeholder="1500"
              value={formData.rotational_speed ?? ''}
              onChange={(e) => handleChange('rotational_speed', Number.parseInt(e.target.value) || undefined)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="torque" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Couple (Nm)
            </Label>
            <Input
              id="torque"
              type="number"
              step="0.1"
              min="0"
              max="1000"
              placeholder="40.0"
              value={formData.torque ?? ''}
              onChange={(e) => handleChange('torque', Number.parseFloat(e.target.value) || undefined)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tool_wear" className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Usure outil (min)
            </Label>
            <Input
              id="tool_wear"
              type="number"
              step="1"
              min="0"
              max="500"
              placeholder="0"
              value={formData.tool_wear ?? ''}
              onChange={(e) => handleChange('tool_wear', Number.parseInt(e.target.value) || undefined)}
            />
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <Label htmlFor="notes" className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            Notes (Optional)
          </Label>
          <Textarea
            id="notes"
            placeholder="Any observations about machine state..."
            value={formData.notes ?? ''}
            onChange={(e) => handleChange('notes', e.target.value)}
            rows={2}
          />
        </div>
      </CardContent>
    </Card>
  );
};

export type { TelemetryFormData };



