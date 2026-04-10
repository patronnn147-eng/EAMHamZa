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
  temperature?: number;
  vibration?: number;
  rpm?: number;
  torque?: number;
  power?: number;
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
            <Label htmlFor="temperature" className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              Temp (°C)
            </Label>
            <Input
              id="temperature"
              type="number"
              step="0.1"
              min="-50"
              max="200"
              placeholder="65.0"
              value={formData.temperature ?? ''}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="vibration" className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Vib (mm/s)
            </Label>
            <Input
              id="vibration"
              type="number"
              step="0.1"
              min="0"
              max="100"
              placeholder="3.5"
              value={formData.vibration ?? ''}
              onChange={(e) => handleChange('vibration', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="rpm" className="flex items-center gap-1">
              <Gauge className="h-3 w-3" />
              RPM
            </Label>
            <Input
              id="rpm"
              type="number"
              step="1"
              min="0"
              max="10000"
              placeholder="3500"
              value={formData.rpm ?? ''}
              onChange={(e) => handleChange('rpm', parseInt(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="torque" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Torque (Nm)
            </Label>
            <Input
              id="torque"
              type="number"
              step="0.1"
              min="0"
              max="1000"
              placeholder="45.0"
              value={formData.torque ?? ''}
              onChange={(e) => handleChange('torque', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="power" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Power (kW)
            </Label>
            <Input
              id="power"
              type="number"
              step="0.1"
              min="0"
              max="500"
              placeholder="12.5"
              value={formData.power ?? ''}
              onChange={(e) => handleChange('power', parseFloat(e.target.value) || undefined)}
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