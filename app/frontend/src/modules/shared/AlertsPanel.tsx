import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, Info, AlertCircle, X, Bell, RefreshCw, Wrench, ExternalLink, Loader2, Cpu, Clock, Activity, TrendingDown, Package } from 'lucide-react';
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

const severityConfig: Record<string, {
  border: string;
  iconBg: string;
  icon: React.ReactNode;
  badgeClass: string;
  barColor: string;
  glow: string;
  label: string;
}> = {
  CRITICAL: {
    border: 'border-l-red-500',
    iconBg: 'bg-red-500/10',
    icon: <AlertTriangle className="h-5 w-5 text-red-500" />,
    badgeClass: 'bg-red-500/20 text-red-400 border-red-500/30',
    barColor: 'bg-red-500',
    glow: 'shadow-red-500/10',
    label: 'CRITICAL',
  },
  HIGH: {
    border: 'border-l-orange-500',
    iconBg: 'bg-orange-500/10',
    icon: <AlertCircle className="h-5 w-5 text-orange-400" />,
    badgeClass: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    barColor: 'bg-orange-500',
    glow: 'shadow-orange-500/10',
    label: 'HIGH',
  },
  MEDIUM: {
    border: 'border-l-yellow-500',
    iconBg: 'bg-yellow-500/10',
    icon: <AlertCircle className="h-5 w-5 text-yellow-400" />,
    badgeClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    barColor: 'bg-yellow-500',
    glow: 'shadow-yellow-500/10',
    label: 'MEDIUM',
  },
  LOW: {
    border: 'border-l-blue-500',
    iconBg: 'bg-blue-500/10',
    icon: <Info className="h-5 w-5 text-blue-400" />,
    badgeClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    barColor: 'bg-blue-500',
    glow: 'shadow-blue-500/10',
    label: 'LOW',
  },
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
            const failurePct = alert.failure_probability != null
              ? Math.round(alert.failure_probability * 100)
              : null;
            const typeLabel = alert.alert_type === 'PARTS_SHORTAGE'
              ? 'Parts Shortage'
              : alert.alert_type.replace(/_/g, ' ');
            // Override icon for PARTS_SHORTAGE regardless of severity
            const rowIcon = alert.alert_type === 'PARTS_SHORTAGE'
              ? <Package className="h-5 w-5 text-orange-400" />
              : config.icon;

            return (
              <div
                key={alert.id}
                className={`
                  relative flex flex-col gap-0 rounded-xl border border-white/[0.06]
                  border-l-4 ${config.border}
                  bg-[#0f1623] shadow-lg ${config.glow}
                  overflow-hidden transition-all duration-200
                  hover:bg-[#131c2e] hover:border-white/[0.1]
                `}
              >
                {/* Top row */}
                <div className="flex items-start justify-between px-5 pt-4 pb-3">
                  {/* Left: icon + info */}
                  <div className="flex items-start gap-3">
                    {/* Type/severity icon */}
                    <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${config.iconBg}`}>
                      {rowIcon}
                    </div>

                    {/* Text block */}
                    <div className="flex flex-col gap-1">
                      {/* Machine + badges row */}
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          onClick={() => handleMachineClick(alert.machine_id)}
                          className="flex items-center gap-1.5 text-sm font-bold text-white hover:text-blue-400 transition-colors"
                        >
                          <Cpu className="h-3.5 w-3.5 opacity-70" />
                          Machine #{alert.machine_id}
                        </button>

                        {/* Alert type pill */}
                        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${config.badgeClass}`}>
                          {typeLabel}
                        </span>

                        {/* Severity pill */}
                        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${config.badgeClass}`}>
                          {config.label}
                        </span>

                        {alert.priority && (
                          <span className="inline-flex items-center rounded-full border border-white/10 px-2.5 py-0.5 text-[11px] font-medium text-white/50">
                            P: {alert.priority}
                          </span>
                        )}
                      </div>

                      {/* Message */}
                      <p className="text-[13px] text-white/60 leading-snug max-w-lg">
                        {alert.message}
                      </p>
                    </div>
                  </div>

                  {/* Right: actions */}
                  <div className="flex shrink-0 items-center gap-2 ml-4">
                    {alert.is_linked_to_wo && alert.work_order_id ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewWorkOrder(alert.work_order_id!)}
                        className="h-8 border-white/10 bg-white/5 text-white hover:bg-white/10 text-xs"
                      >
                        <ExternalLink className="mr-1.5 h-3 w-3" />
                        WO #{alert.work_order_id}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleCreateWorkOrder(alert.id)}
                        disabled={creatingWo === alert.id}
                        className="h-8 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium"
                      >
                        {creatingWo === alert.id ? (
                          <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                        ) : (
                          <Wrench className="mr-1.5 h-3 w-3" />
                        )}
                        Create WO
                      </Button>
                    )}
                    <button
                      onClick={() => handleDismiss(alert.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-white/30 hover:bg-white/5 hover:text-white/70 transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Bottom metrics row */}
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[0.05] px-5 py-2.5">
                  {/* Created at */}
                  <div className="flex items-center gap-1.5 text-[11px] text-white/40">
                    <Clock className="h-3 w-3" />
                    {new Date(alert.created_at).toLocaleString()}
                  </div>

                  {/* RUL */}
                  {alert.rul_days != null && (
                    <div className="flex items-center gap-1.5 text-[11px] text-white/40">
                      <TrendingDown className="h-3 w-3" />
                      RUL: <span className="font-semibold text-white/70">{alert.rul_days.toFixed(1)} days</span>
                    </div>
                  )}

                  {/* Failure probability with bar */}
                  {failurePct != null && (
                    <div className="flex items-center gap-2">
                      <Activity className="h-3 w-3 text-white/40" />
                      <span className="text-[11px] text-white/40">Failure prob:</span>
                      <span className={`text-[11px] font-bold ${failurePct >= 80 ? 'text-red-400' : failurePct >= 60 ? 'text-orange-400' : 'text-yellow-400'}`}>
                        {failurePct}%
                      </span>
                      <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${config.barColor} transition-all`}
                          style={{ width: `${Math.min(failurePct, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AlertsPanel;