import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Save, Plus, RefreshCw, Calendar, Clock, Mail, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface Recipient {
  email: string;
  nom: string;
}

interface ScheduleConfig {
  frequency: string;
  day_of_week?: number;
  time: string;
  recipients: Recipient[];
}

interface ScheduledReport {
  id: number;
  identifiant_rapport: string;
  titre: string;
  report_type: string;
  schedule_config: ScheduleConfig;
  is_active: boolean;
  last_sent_at?: string;
  created_at: string;
}

export const ReportScheduler: React.FC = () => {
  const [reports, setReports] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingReport, setEditingReport] = useState<ScheduledReport | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    report_type: 'asset_health',
    title: '',
    frequency: 'weekly',
    day_of_week: 1,
    time: '08:00',
    recipients: [{ email: '', nom: '' }],
    is_active: true,
  });
  // Stable per-row React keys for recipients, independent of the plain-data shape.
  const recipientKeysRef = useRef<string[]>([]);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/reports/scheduled`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReports(data.items || []);
      }
    } catch (err) {
      console.error('Failed to load scheduled reports', err);
    } finally {
      setLoading(false);
    }
  }, [API]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleOpenDialog = (report?: ScheduledReport) => {
    recipientKeysRef.current = [];
    if (report) {
      setEditingReport(report);
      const config = report.schedule_config || {};
      setFormData({
        report_type: report.report_type || 'asset_health',
        title: report.titre,
        frequency: config.frequency || 'weekly',
        day_of_week: config.day_of_week || 1,
        time: config.time || '08:00',
        recipients: config.recipients?.length ? config.recipients : [{ email: '', nom: '' }],
        is_active: report.is_active,
      });
    } else {
      setEditingReport(null);
      setFormData({
        report_type: 'asset_health',
        title: '',
        frequency: 'weekly',
        day_of_week: 1,
        time: '08:00',
        recipients: [{ email: '', nom: '' }],
        is_active: true,
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.title.trim()) {
      toast({ title: 'Error', description: 'Title is required', variant: 'destructive' });
      return;
    }

    const validRecipients = formData.recipients.filter(r => r.email.trim());
    if (validRecipients.length === 0) {
      toast({ title: 'Error', description: 'At least one recipient is required', variant: 'destructive' });
      return;
    }

    try {
      const payload = {
        report_type: formData.report_type,
        title: formData.title,
        frequency: formData.frequency,
        day_of_week: formData.frequency === 'weekly' ? formData.day_of_week : null,
        time: formData.time,
        recipients: validRecipients,
        is_active: formData.is_active,
      };

      const url = editingReport
        ? `${API}/api/v1/reports/scheduled/${editingReport.id}`
        : `${API}/api/v1/reports/scheduled`;
      const method = editingReport ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        toast({
          title: editingReport ? 'Schedule updated' : 'Schedule created',
          description: editingReport
            ? 'Report schedule has been updated.'
            : 'New report schedule has been created.',
        });
        setDialogOpen(false);
        fetchReports();
      } else {
        throw new Error('Failed to save');
      }
    } catch {
      toast({ title: 'Error', description: 'Failed to save schedule', variant: 'destructive' });
    }
  };

  const handleDelete = async (report: ScheduledReport) => {
    try {
      const res = await fetch(`${API}/api/v1/reports/scheduled/${report.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        toast({ title: 'Deleted', description: 'Schedule removed successfully' });
        fetchReports();
      }
    } catch {
      toast({ title: 'Error', description: 'Failed to delete schedule', variant: 'destructive' });
    }
  };

  const handleToggleActive = async (report: ScheduledReport) => {
    try {
      await fetch(`${API}/api/v1/reports/scheduled/${report.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !report.is_active }),
      });
      fetchReports();
    } catch {
      toast({ title: 'Error', description: 'Failed to update status', variant: 'destructive' });
    }
  };

  const updateRecipient = (index: number, field: keyof Recipient, value: string) => {
    const newRecipients = [...formData.recipients];
    newRecipients[index] = { ...newRecipients[index], [field]: value };
    setFormData({ ...formData, recipients: newRecipients });
  };

  const addRecipient = () => {
    recipientKeysRef.current.push(crypto.randomUUID());
    setFormData({
      ...formData,
      recipients: [...formData.recipients, { email: '', nom: '' }],
    });
  };

  const removeRecipient = (index: number) => {
    if (formData.recipients.length > 1) {
      recipientKeysRef.current.splice(index, 1);
      const newRecipients = formData.recipients.filter((_, i) => i !== index);
      setFormData({ ...formData, recipients: newRecipients });
    }
  };

  const getFrequencyLabel = (freq: string) => {
    switch (freq) {
      case 'daily': return 'Daily';
      case 'weekly': return 'Weekly';
      case 'monthly': return 'Monthly';
      default: return freq;
    }
  };

  const getReportTypeLabel = (type: string) => {
    switch (type) {
      case 'asset_health': return 'Asset Health Report';
      case 'weekly_digest': return 'Weekly Digest';
      case 'maintenance_summary': return 'Maintenance Summary';
      default: return type;
    }
  };

  if (loading) {
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
          <h1 className="text-2xl font-bold">Report Scheduler</h1>
          <p className="text-muted-foreground">
            Configure automated report generation and delivery
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchReports}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => handleOpenDialog()}>
            <Plus className="mr-2 h-4 w-4" />
            New Schedule
          </Button>
        </div>
      </div>

      {reports.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No scheduled reports configured</p>
            <Button className="mt-4" onClick={() => handleOpenDialog()}>
              <Plus className="mr-2 h-4 w-4" />
              Create First Schedule
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {reports.map((report) => (
            <Card key={report.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{report.titre}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {getReportTypeLabel(report.report_type)}
                    </p>
                  </div>
                  <Switch
                    checked={report.is_active}
                    onCheckedChange={() => handleToggleActive(report)}
                  />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span>{getFrequencyLabel(report.schedule_config?.frequency)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <span>{report.schedule_config?.recipients?.length || 0} recipients</span>
                  </div>
                </div>

                {report.last_sent_at && (
                  <p className="text-xs text-muted-foreground">
                    Last sent: {new Date(report.last_sent_at).toLocaleString()}
                  </p>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenDialog(report)}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-600 hover:text-red-700"
                    onClick={() => handleDelete(report)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingReport ? 'Edit Schedule' : 'Create Schedule'}
            </DialogTitle>
            <DialogDescription>
              Configure automated report generation and email delivery
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">Report Title</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., Weekly Asset Health Report"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Report Type</Label>
                <Select
                  value={formData.report_type}
                  onValueChange={(v) => setFormData({ ...formData, report_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asset_health">Asset Health Report</SelectItem>
                    <SelectItem value="weekly_digest">Weekly Digest</SelectItem>
                    <SelectItem value="maintenance_summary">Maintenance Summary</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Frequency</Label>
                <Select
                  value={formData.frequency}
                  onValueChange={(v) => setFormData({ ...formData, frequency: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {formData.frequency === 'weekly' && (
              <div className="grid gap-2">
                <Label>Day of Week</Label>
                <Select
                  value={formData.day_of_week.toString()}
                  onValueChange={(v) => setFormData({ ...formData, day_of_week: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Sunday</SelectItem>
                    <SelectItem value="1">Monday</SelectItem>
                    <SelectItem value="2">Tuesday</SelectItem>
                    <SelectItem value="3">Wednesday</SelectItem>
                    <SelectItem value="4">Thursday</SelectItem>
                    <SelectItem value="5">Friday</SelectItem>
                    <SelectItem value="6">Saturday</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid gap-2">
              <Label>Time (HH:MM)</Label>
              <Input
                type="time"
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
              />
            </div>

            <div className="grid gap-2">
              <Label>Recipients</Label>
              {formData.recipients.map((recipient, index) => {
                if (!recipientKeysRef.current[index]) recipientKeysRef.current[index] = crypto.randomUUID();
                return (
                <div key={recipientKeysRef.current[index]} className="flex gap-2">
                  <Input
                    placeholder="Name"
                    value={recipient.nom}
                    onChange={(e) => updateRecipient(index, 'nom', e.target.value)}
                    className="flex-1"
                  />
                  <Input
                    placeholder="Email"
                    type="email"
                    value={recipient.email}
                    onChange={(e) => updateRecipient(index, 'email', e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeRecipient(index)}
                    disabled={formData.recipients.length <= 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                );
              })}
              <Button variant="outline" size="sm" onClick={addRecipient}>
                <Plus className="mr-2 h-4 w-4" />
                Add Recipient
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
              <Label htmlFor="active">Enable schedule</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              <Save className="mr-2 h-4 w-4" />
              {editingReport ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ReportScheduler;
