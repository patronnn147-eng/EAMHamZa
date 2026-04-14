import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, Info, AlertCircle, X, Bell, RefreshCw, Wrench, ExternalLink, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface Alert {
  id: number;
  alert_id: string;
  machine_id: number;
  alert_type: string;
  severity: string;
  message: string;
  rul_days?: number;
  failure_probability?: number;
  is_active: boolean;
  created_at: string;
  dismissed_at?: string;
  is_linked_to_wo?: boolean;
  work_order_id?: number;
  priority?: string;
}

interface AlertStats {
  total_active: number;
  by_severity: Record<string, number>;
  machines_affected: number;
}

const severityConfig: Record<string, { color: string; icon: React.ReactNode; bg: string }> = {
  CRITICAL: { color: 'bg-red-500', icon: <AlertTriangle className="h-4 w-4 text-red-500" />, bg: 'bg-red-50' },
  HIGH: { color: 'bg-orange-500', icon: <AlertCircle className="h-4 w-4 text-orange-500" />, bg: 'bg-orange-50' },
  MEDIUM: { color: 'bg-yellow-500', icon: <AlertCircle className="h-4 w-4 text-yellow-500" />, bg: 'bg-yellow-50' },
  LOW: { color: 'bg-blue-500', icon: <Info className="h-4 w-4 text-blue-500" />, bg: 'bg-blue-50' },
};

export const AlertsPanel: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [creatingWo, setCreatingWo] = useState<number | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const params = severityFilter !== 'all' ? `?severity=${severityFilter}` : '';
      const res = await fetch(`${API}/api/v1/alerts${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        setAlerts(await res.json());
      }

      const statsRes = await fetch(`${API}/api/v1/alerts/stats`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      console.error('Failed to load alerts', err);
    } finally {
      setLoading(false);
    }
  }, [API, severityFilter]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleDismiss = async (alertId: number) => {
    try {
      const userId = 1; // TODO: Get from auth context
      const res = await fetch(`${API}/api/v1/alerts/${alertId}/dismiss`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId }),
      });
      if (res.ok) {
        setAlerts(alerts.filter((a) => a.id !== alertId));
        toast({
          title: 'Alert dismissed',
          description: 'The alert has been dismissed.',
          variant: 'default',
        });
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to dismiss alert.',
        variant: 'destructive',
      });
    }
  };

  const handleMachineClick = (machineId: number) => {
    navigate(`/machines/${machineId}`);
  };

  const handleCreateWorkOrder = async (alertId: number) => {
    setCreatingWo(alertId);
    try {
      const res = await fetch(`${API}/api/v1/alerts/${alertId}/create-work-order`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const wo = await res.json();
        setAlerts(alerts.map(a => 
          a.id === alertId ? { ...a, is_linked_to_wo: true, work_order_id: wo.id } : a
        ));
        toast({
          title: 'Work Order Created',
          description: `Work Order #${wo.id} has been created from this alert.`,
          variant: 'default',
        });
      } else {
        const err = await res.json();
        toast({
          title: 'Error',
          description: err.detail || 'Failed to create work order.',
          variant: 'destructive',
        });
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to create work order.',
        variant: 'destructive',
      });
    } finally {
      setCreatingWo(null);
    }
  };

  const handleViewWorkOrder = (workOrderId: number) => {
    navigate(`/work-orders/${workOrderId}`);
  };

  if (loading && !alerts.length) {
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
            <Bell className="h-6 w-6" />
            Predictive Alerts
          </h1>
          <p className="text-muted-foreground">
            ML-powered alerts based on Remaining Useful Life and failure predictions
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAlerts}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{stats.total_active}</div>
              <p className="text-sm text-muted-foreground">Active Alerts</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-red-600">{stats.by_severity.CRITICAL || 0}</div>
              <p className="text-sm text-muted-foreground">Critical</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-orange-600">{stats.by_severity.HIGH || 0}</div>
              <p className="text-sm text-muted-foreground">High</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{stats.machines_affected}</div>
              <p className="text-sm text-muted-foreground">Machines Affected</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-4">
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="CRITICAL">Critical</SelectItem>
            <SelectItem value="HIGH">High</SelectItem>
            <SelectItem value="MEDIUM">Medium</SelectItem>
            <SelectItem value="LOW">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No Active Alerts</h3>
            <p className="text-muted-foreground">
              All machines are operating normally. Alerts will appear here when ML
              predictions indicate potential issues.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const config = severityConfig[alert.severity] || severityConfig.LOW;
            return (
              <Card key={alert.id} className={config.bg}>
                <CardContent className="flex items-start justify-between py-4">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">{config.icon}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className="font-semibold cursor-pointer hover:underline"
                          onClick={() => handleMachineClick(alert.machine_id)}
                        >
                          Machine #{alert.machine_id}
                        </span>
                        <Badge variant={alert.severity === 'CRITICAL' ? 'destructive' : 'secondary'}>
                          {alert.alert_type}
                        </Badge>
                        <Badge variant="outline">{alert.severity}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span>
                          Created: {new Date(alert.created_at).toLocaleString()}
                        </span>
                        {alert.rul_days !== null && (
                          <span>RUL: {alert.rul_days?.toFixed(1)} days</span>
                        )}
                        {alert.failure_probability !== null && (
                          <span>
                            Failure Prob: {(alert.failure_probability * 100).toFixed(1)}%
                          </span>
                        )}
                        {alert.priority && (
                          <Badge variant="outline" className="text-xs">Priority: {alert.priority}</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {alert.is_linked_to_wo && alert.work_order_id ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewWorkOrder(alert.work_order_id!)}
                      >
                        <ExternalLink className="mr-1 h-3 w-3" />
                        View WO #{alert.work_order_id}
                      </Button>
                    ) : (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleCreateWorkOrder(alert.id)}
                        disabled={creatingWo === alert.id}
                      >
                        {creatingWo === alert.id ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Wrench className="mr-1 h-3 w-3" />
                        )}
                        Create WO
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDismiss(alert.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AlertsPanel;