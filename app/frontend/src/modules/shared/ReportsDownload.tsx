import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Download, RefreshCw, BarChart3, Calendar, Activity, Settings } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface ReportType {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const REPORT_TYPES: ReportType[] = [
  {
    id: 'asset_health',
    name: 'Asset Health Report',
    description: 'Current health status of all assets including RUL predictions and failure probabilities',
    icon: <Activity className="h-6 w-6" />,
  },
  {
    id: 'weekly_digest',
    name: 'Weekly Digest',
    description: 'Summary of maintenance activities, work orders, and alerts from the past week',
    icon: <Calendar className="h-6 w-6" />,
  },
  {
    id: 'maintenance_summary',
    name: 'Maintenance Summary',
    description: 'Overview of completed maintenance tasks, costs, and equipment reliability metrics',
    icon: <BarChart3 className="h-6 w-6" />,
  },
];

export const ReportsDownload: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<string>('asset_health');
  const [format, setFormat] = useState<string>('json');
  const [generating, setGenerating] = useState(false);
  const { toast } = useToast();

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await fetch(
        `${API}/api/v1/reports/download/${selectedReport}?format=${format}`,
        {
          headers: { Authorization: `Bearer ${getToken()}` },
        }
      );

      if (res.ok) {
        const data = await res.json();
        
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { 
          type: format === 'json' ? 'application/json' : 'text/plain' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedReport}_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        toast({
          title: 'Report generated',
          description: `${REPORT_TYPES.find(r => r.id === selectedReport)?.name} downloaded successfully`,
        });
      } else {
        throw new Error('Failed to generate report');
      }
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to generate report',
        variant: 'destructive',
      });
    } finally {
      setGenerating(false);
    }
  };

  const selectedReportType = REPORT_TYPES.find(r => r.id === selectedReport);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Reports</h1>
        <p className="text-muted-foreground">
          Generate and download on-demand reports
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {REPORT_TYPES.map((report) => (
          <Card
            key={report.id}
            className={`cursor-pointer transition-all ${
              selectedReport === report.id
                ? 'border-primary ring-1 ring-primary'
                : 'hover:border-primary/50'
            }`}
            onClick={() => setSelectedReport(report.id)}
          >
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className={`rounded-lg p-2 ${
                  selectedReport === report.id
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}>
                  {report.icon}
                </div>
                <div>
                  <CardTitle className="text-base">{report.name}</CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{report.description}</p>
              {selectedReport === report.id && (
                <Badge className="mt-2" variant="secondary">
                  Selected
                </Badge>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate Report</CardTitle>
          <CardDescription>
            Select report type above and click generate to download
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex-1">
              <label htmlFor="report-type-select" className="text-sm font-medium mb-2 block">Report Type</label>
              <Select value={selectedReport} onValueChange={setSelectedReport}>
                <SelectTrigger id="report-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REPORT_TYPES.map((report) => (
                    <SelectItem key={report.id} value={report.id}>
                      {report.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="w-full sm:w-40">
              <label htmlFor="format-select" className="text-sm font-medium mb-2 block">Format</label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger id="format-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="excel">Excel</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="pt-6">
              <Button
                onClick={handleGenerate}
                disabled={generating}
                className="w-full sm:w-auto"
              >
                {generating ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Generate & Download
                  </>
                )}
              </Button>
            </div>
          </div>

          {selectedReportType && (
            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-2">{selectedReportType.name}</h4>
              <p className="text-sm text-muted-foreground">
                {selectedReportType.description}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Scheduled Reports
          </CardTitle>
          <CardDescription>
            For automated recurring reports, contact your administrator to set up scheduled delivery
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Need reports sent automatically? Administrators can configure scheduled reports
            with email delivery in the Report Scheduler section.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ReportsDownload;
