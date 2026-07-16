import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { TrendChart } from '@/components/telemetry/TrendChart';
import { 
  Thermometer, 
  Activity, 
  Gauge, 
  TrendingUp, 
  Zap,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface TelemetryData {
  temperature: number;
  vibration: number;
  rpm: number;
  torque: number;
  power: number;
  timestamp: string;
}

interface TelemetryHistory {
  metric: string;
  data: { timestamp: string; value: number }[];
}

const metricConfig = {
  temperature: {
    name: 'Temperature',
    unit: '°C',
    icon: <Thermometer className="h-5 w-5" />,
    thresholds: { warning: 80, critical: 95 },
    description: 'Motor temperature in Celsius'
  },
  vibration: {
    name: 'Vibration',
    unit: 'mm/s',
    icon: <Activity className="h-5 w-5" />,
    thresholds: { warning: 7, critical: 10 },
    description: 'Vibration amplitude'
  },
  rpm: {
    name: 'RPM',
    unit: 'rpm',
    icon: <Gauge className="h-5 w-5" />,
    thresholds: { warning: 4500, critical: 5000 },
    description: 'Rotational speed'
  },
  torque: {
    name: 'Torque',
    unit: 'Nm',
    icon: <TrendingUp className="h-5 w-5" />,
    thresholds: { warning: 80, critical: 95 },
    description: 'Torque output'
  },
  power: {
    name: 'Power',
    unit: 'kW',
    icon: <Zap className="h-5 w-5" />,
    thresholds: { warning: 15, critical: 20 },
    description: 'Power consumption'
  }
};

const generateMockHistory = (metric: string, days: number = 7): { timestamp: string; value: number }[] => {
  const data: { timestamp: string; value: number }[] = [];
  const now = new Date();
  let baseValue: number;
  if (metric === 'rpm') {
    baseValue = 3000;
  } else if (metric === 'temperature') {
    baseValue = 45;
  } else {
    baseValue = 50;
  }
  
  for (let i = days * 24; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
    const variation = (Math.random() - 0.5) * 20;
    let value = baseValue + variation;
    
    if (i % 100 === 0) {
      value += (Math.random() - 0.3) * 30;
    }
    
    data.push({
      timestamp: timestamp.toISOString(),
      value: Math.max(0, value)
    });
  }
  
  return data;
};

export const TelemetryPanel: React.FC = () => {
  const { machineId } = useParams<{ machineId: string }>();
  const [currentData, setCurrentData] = useState<TelemetryData | null>(null);
  const [history, setHistory] = useState<TelemetryHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 30000);
    return () => clearInterval(interval);
  }, [machineId]);

  const fetchTelemetry = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/machines/${machineId}/telemetry`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setCurrentData(data.current);
        setHistory(data.history || []);
      } else {
        setCurrentData({
          temperature: 45 + Math.random() * 20,
          vibration: 3 + Math.random() * 4,
          rpm: 2800 + Math.random() * 800,
          torque: 40 + Math.random() * 30,
          power: 8 + Math.random() * 8,
          timestamp: new Date().toISOString()
        });
        
        setHistory([
          { metric: 'temperature', data: generateMockHistory('temperature') },
          { metric: 'vibration', data: generateMockHistory('vibration') },
          { metric: 'rpm', data: generateMockHistory('rpm') },
          { metric: 'torque', data: generateMockHistory('torque') },
          { metric: 'power', data: generateMockHistory('power') }
        ]);
      }
    } catch (err) {
      console.error('Failed to load telemetry', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatus = (metric: string, value: number) => {
    const config = metricConfig[metric as keyof typeof metricConfig];
    if (!config) return 'unknown';
    if (value >= config.thresholds.critical) return 'critical';
    if (value >= config.thresholds.warning) return 'warning';
    return 'normal';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'critical': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default: return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
  };

  const exportAllData = () => {
    const headers = 'metric,timestamp,value\n';
    const rows = history.flatMap(h => 
      h.data.map(d => `${h.metric},${d.timestamp},${d.value}`)
    ).join('\n');
    
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `machine_${machineId}_telemetry.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !currentData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6" />
            Machine Telemetry
          </h1>
          <p className="text-muted-foreground">
            Real-time sensor data and historical trends
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchTelemetry}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportAllData}>
            <Download className="mr-2 h-4 w-4" />
            Export All
          </Button>
        </div>
      </div>

      {currentData && (
        <>
          <div className="grid gap-4 md:grid-cols-5">
            {Object.entries(currentData).filter(([k]) => k !== 'timestamp').map(([key, value]) => {
              const config = metricConfig[key as keyof typeof metricConfig];
              const status = getStatus(key, value as number);
              
              return (
                <Card key={key}>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-muted-foreground">
                        {config?.icon}
                      </div>
                      {getStatusIcon(status)}
                    </div>
                    <div className="text-2xl font-bold">
                      {(value as number).toFixed(1)}
                      <span className="text-sm font-normal text-muted-foreground ml-1">
                        {config?.unit}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {config?.name}
                    </p>
                    {status !== 'normal' && (
                      <Badge 
                        variant={status === 'critical' ? 'destructive' : 'secondary'}
                        className="mt-2 text-xs"
                      >
                        {status.toUpperCase()}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {(Object.keys(metricConfig) as Array<keyof typeof metricConfig>).map((metric) => {
              const historyData = history.find(h => h.metric === metric);
              const config = metricConfig[metric];
              
              return (
                <TrendChart
                  key={metric}
                  data={historyData?.data || generateMockHistory(metric)}
                  metric={metric}
                  unit={config.unit}
                  thresholds={config.thresholds}
                  title={config.name}
                />
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default TelemetryPanel;
