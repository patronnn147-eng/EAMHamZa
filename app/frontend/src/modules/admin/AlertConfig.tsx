import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Save, RefreshCw, Bell, Mail, Clock } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface AlertConfig {
  id: number;
  rul_threshold_days: number;
  failure_probability_threshold: number;
  enable_rul_alerts: boolean;
  enable_failure_alerts: boolean;
  enable_anomaly_alerts: boolean;
  notification_in_app: boolean;
  notification_email: boolean;
  frequency: string;
}

export const AlertConfig: React.FC = () => {
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/alerts/config`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        setConfig(await res.json());
      }
    } catch (err) {
      console.error('Failed to load alert config', err);
    } finally {
      setLoading(false);
    }
  }, [API]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/v1/alerts/config`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        toast({
          title: 'Configuration saved',
          description: 'Alert settings have been updated successfully.',
          variant: 'default',
        });
      } else {
        throw new Error('Failed to save');
      }
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to save alert configuration.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerCheck = async () => {
    try {
      const res = await fetch(`${API}/api/v1/alerts/check`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const result = await res.json();
        toast({
          title: 'Alert check completed',
          description: `Created: ${result.alerts_created?.rul_warnings || 0} RUL, ${result.alerts_created?.failure_predicted || 0} failure alerts`,
          variant: 'default',
        });
      }
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to trigger alert check.',
        variant: 'destructive',
      });
    }
  };

  if (loading || !config) {
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
          <h1 className="text-2xl font-bold">Alert Configuration</h1>
          <p className="text-muted-foreground">
            Configure predictive maintenance alerts and notifications
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleTriggerCheck}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Run Alert Check
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* RUL Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              RUL Warning Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable-rul">Enable RUL Alerts</Label>
              <Switch
                id="enable-rul"
                checked={config.enable_rul_alerts}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, enable_rul_alerts: checked })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>RUL Threshold (days)</Label>
              <Slider
                value={[config.rul_threshold_days]}
                onValueChange={([value]) =>
                  setConfig({ ...config, rul_threshold_days: value })
                }
                min={1}
                max={30}
                step={1}
              />
              <p className="text-sm text-muted-foreground">
                Alert when Remaining Useful Life is below {config.rul_threshold_days} days
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Failure Prediction Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Failure Prediction Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable-failure">Enable Failure Alerts</Label>
              <Switch
                id="enable-failure"
                checked={config.enable_failure_alerts}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, enable_failure_alerts: checked })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Failure Probability Threshold</Label>
              <Slider
                value={[config.failure_probability_threshold * 100]}
                onValueChange={([value]) =>
                  setConfig({
                    ...config,
                    failure_probability_threshold: value / 100,
                  })
                }
                min={10}
                max={90}
                step={5}
              />
              <p className="text-sm text-muted-foreground">
                Alert when failure probability exceeds{' '}
                {Math.round(config.failure_probability_threshold * 100)}%
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Anomaly Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Anomaly Detection Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable-anomaly">Enable Anomaly Alerts</Label>
              <Switch
                id="enable-anomaly"
                checked={config.enable_anomaly_alerts}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, enable_anomaly_alerts: checked })
                }
              />
            </div>
            <p className="text-sm text-muted-foreground">
              Alert when machines show anomalous behavior detected by ML models
            </p>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Notification Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                <Label htmlFor="notif-inapp">In-App Notifications</Label>
              </div>
              <Switch
                id="notif-inapp"
                checked={config.notification_in_app}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, notification_in_app: checked })
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <Label htmlFor="notif-email">Email Notifications</Label>
              </div>
              <Switch
                id="notif-email"
                checked={config.notification_email}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, notification_email: checked })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Alert Frequency</Label>
              <Select
                value={config.frequency}
                onValueChange={(value) =>
                  setConfig({ ...config, frequency: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="real-time">Real-time</SelectItem>
                  <SelectItem value="daily">Daily Digest</SelectItem>
                  <SelectItem value="weekly">Weekly Digest</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-primary/10 p-2">
              <Bell className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">How Alerts Work</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Predictive alerts are generated based on ML model predictions. The system
                checks all machines periodically and creates alerts when:
              </p>
              <ul className="text-sm text-muted-foreground mt-2 list-disc list-inside">
                <li>RUL (Remaining Useful Life) drops below the threshold</li>
                <li>Failure probability exceeds the configured percentage</li>
                <li>Machine behavior is flagged as anomalous</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AlertConfig;