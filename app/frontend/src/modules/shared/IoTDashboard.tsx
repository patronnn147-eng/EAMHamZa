import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Activity, 
  Thermometer, 
  Gauge, 
  Zap,
  RefreshCw,
  Signal,
  AlertTriangle,
  Wifi,
  WifiOff
} from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface MachineTelemetry {
  id: number;
  name: string;
  zone: string;
  status: string;
  temperature: number | null;
  vibration: number | null;
  rpm: number | null;
  torque: number | null;
  power: number | null;
  online: boolean;
  lastUpdate: string | null;
  hasTelemetry: boolean;
}

interface IoTStats {
  total: number;
  online: number;
  warning: number;
  critical: number;
}

export const IoTDashboard: React.FC = () => {
  const [machines, setMachines] = useState<MachineTelemetry[]>([]);
  const [loading, setLoading] = useState(true);
  const [zoneFilter, setZoneFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [healthFilter, setHealthFilter] = useState<string>('all');
  const navigate = useNavigate();

  useEffect(() => {
    fetchMachines();
    const interval = setInterval(fetchMachines, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMachines = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/machines?limit=50`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        const machinesData = data.items || data || [];
        
        // For each machine, fetch latest telemetry
        const machinesWithTelemetry = await Promise.all(
          machinesData.map(async (m: any) => {
            let telemetry = null;
            try {
              const telRes = await fetch(
                `${API}/api/v1/technicien/machines/${m.id}/telemetry/latest`,
                { headers: { Authorization: `Bearer ${getToken()}` } }
              );
              if (telRes.ok) {
                telemetry = await telRes.json();
              }
            } catch {
              // No telemetry for this machine
            }
            
            return {
              id: m.id,
              name: m.nom || `Machine ${m.id}`,
              zone: m.zone || 'Zone A',
              status: m.statut || 'OPERATIONAL',
              temperature: telemetry?.temperature ?? null,
              vibration: telemetry?.vibration ?? null,
              rpm: telemetry?.rpm ?? null,
              torque: telemetry?.torque ?? null,
              power: telemetry?.power ?? null,
              online: telemetry !== null,
              lastUpdate: telemetry?.recorded_at ?? null,
              hasTelemetry: telemetry !== null,
            };
          })
        );
        
        setMachines(machinesWithTelemetry);
      } else {
        // API returned error, show empty
        setMachines([]);
      }
    } catch (err) {
      console.error('Failed to load machines', err);
      setMachines([]);
    } finally {
      setLoading(false);
    }
  };

  const getHealthStatus = (machine: MachineTelemetry) => {
    // If no telemetry data, show as unknown
    if (!machine.hasTelemetry || machine.temperature === null) {
      return 'unknown';
    }
    if (machine.temperature > 95 || machine.vibration > 10) return 'critical';
    if (machine.temperature > 80 || machine.vibration > 7) return 'warning';
    return 'normal';
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'critical': return 'border-l-red-500';
      case 'warning': return 'border-l-yellow-500';
      case 'unknown': return 'border-l-gray-400';
      default: return 'border-l-green-500';
    }
  };

  const getStats = (): IoTStats => {
    const filtered = getFilteredMachines();
    return {
      total: filtered.length,
      online: filtered.filter(m => m.online).length,
      warning: filtered.filter(m => getHealthStatus(m) === 'warning').length,
      critical: filtered.filter(m => getHealthStatus(m) === 'critical').length
    };
  };

  const getFilteredMachines = () => {
    return machines.filter(m => {
      if (zoneFilter !== 'all' && m.zone !== zoneFilter) return false;
      if (statusFilter !== 'all' && m.status !== statusFilter) return false;
      if (healthFilter !== 'all' && getHealthStatus(m) !== healthFilter) return false;
      return true;
    });
  };

  const stats = getStats();
  const filteredMachines = getFilteredMachines();

  if (loading && machines.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  const zones = [...new Set(machines.map(m => m.zone))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6" />
            IoT Dashboard
          </h1>
          <p className="text-muted-foreground">
            Real-time telemetry and health status for all machines
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchMachines}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-sm text-muted-foreground">Total Machines</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-600 flex items-center gap-2">
              <Wifi className="h-5 w-5" />
              {stats.online}
            </div>
            <p className="text-sm text-muted-foreground">Online</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-yellow-600 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              {stats.warning}
            </div>
            <p className="text-sm text-muted-foreground">Warning</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-red-600 flex items-center gap-2">
              <Signal className="h-5 w-5" />
              {stats.critical}
            </div>
            <p className="text-sm text-muted-foreground">Critical</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-4">
        <Select value={zoneFilter} onValueChange={setZoneFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Zones" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Zones</SelectItem>
            {zones.map(zone => (
              <SelectItem key={zone} value={zone}>{zone}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="OPERATIONAL">Operational</SelectItem>
            <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
            <SelectItem value="PANNE">Panne</SelectItem>
          </SelectContent>
        </Select>

        <Select value={healthFilter} onValueChange={setHealthFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Health" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Health</SelectItem>
            <SelectItem value="normal">Normal</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredMachines.map((machine) => {
          const health = getHealthStatus(machine);
          
          return (
            <Card 
              key={machine.id} 
              className={`cursor-pointer hover:shadow-md transition-shadow border-l-4 ${getHealthColor(health)}`}
              onClick={() => navigate(`/machines/${machine.id}/telemetry`)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{machine.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    {machine.online ? (
                      <Wifi className="h-4 w-4 text-green-500" />
                    ) : (
                      <WifiOff className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">{machine.zone}</Badge>
                  <Badge 
                    variant={machine.status === 'OPERATIONAL' ? 'default' : 
                            machine.status === 'PANNE' ? 'destructive' : 'secondary'}
                    className="text-xs"
                  >
                    {machine.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {machine.hasTelemetry ? (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Thermometer className="h-3 w-3 text-muted-foreground" />
                      <span>{machine.temperature?.toFixed(1)}°C</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Activity className="h-3 w-3 text-muted-foreground" />
                      <span>{machine.vibration?.toFixed(1)} mm/s</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Gauge className="h-3 w-3 text-muted-foreground" />
                      <span>{machine.rpm?.toFixed(0)} rpm</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Zap className="h-3 w-3 text-muted-foreground" />
                      <span>{machine.power?.toFixed(1)} kW</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground italic">
                    No telemetry data
                  </div>
                )}
                {machine.lastUpdate && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    Updated: {new Date(machine.lastUpdate).toLocaleTimeString()}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredMachines.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No Machines Found</h3>
            <p className="text-muted-foreground">
              No machines match the current filters.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default IoTDashboard;
