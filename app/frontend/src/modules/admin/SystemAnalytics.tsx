import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, 
  LineChart, Line, PieChart, Pie, Cell, Legend
} from 'recharts';
import { Download, Activity, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6366f1'];

interface TechPerformance {
  technician_id: number;
  completed: number;
  avg_duration: number;
}

interface AdminAnalyticsData {
  kpis: {
    total_completed: number;
    avg_duration_minutes: number;
    requests_validated: number;
    failures_by_type: Record<string, number>;
  };
  technician_performance: TechPerformance[];
  request_trends: {
    total_accepted: number;
    total_rejected: number;
    total_pending: number;
    daily_trends: Array<{
      date: string;
      accepted: number;
      rejected: number;
      pending: number;
    }>;
  };
}

export const SystemAnalytics: React.FC = () => {
  const [data, setData] = useState<AdminAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/admin/analytics/dashboard`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error('Failed to load admin analytics', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = async () => {
    try {
      const res = await fetch(`${API}/api/v1/admin/analytics/export`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const dateStr = new Date().toISOString().replace(/[:.]/g, '-');
        a.download = `system_export_${dateStr}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert("Erreur lors de l'exportation des données.");
      }
    } catch (err) {
      console.error('Export failed', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  if (!data) return <div className="p-8">Erreur de chargement des données système.</div>;

  const failureData = Object.entries(data.kpis.failures_by_type).map(([key, value]) => ({
    name: key,
    value,
  }));

  const formatDuration = (mins: number) => {
    if (mins < 60) return `${mins} min`;
    return `${Math.floor(mins / 60)}h ${mins % 60}min`;
  };

  return (
    <div className="min-h-screen bg-slate-800/50/50 p-8">
      <div className="max-w-[1600px] mx-auto">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-black text-white flex items-center gap-3">
              <Activity className="h-8 w-8 text-indigo-600" />
              Intelligence Système & Analytics
            </h1>
            <p className="text-blue-300 font-medium">Monitoring global des opérations et performances (Administrateur)</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => navigate('/admin')}>
              Retour Admin
            </Button>
            <Button onClick={handleExport} className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm">
              <Download className="mr-2 h-4 w-4" /> Exporter (CSV)
            </Button>
          </div>
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="shadow-sm border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <p className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-2">OTs Complétés Syst.</p>
              <h3 className="text-4xl font-black text-white">{data.kpis.total_completed}</h3>
              <p className="text-sm text-blue-600 font-medium mt-2 flex items-center gap-1">
                <CheckCircle className="w-4 h-4"/> Globalement traités
              </p>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-l-4 border-l-indigo-500">
            <CardContent className="pt-6">
              <p className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-2">Durée Moyenne Syst.</p>
              <h3 className="text-4xl font-black text-white">{formatDuration(data.kpis.avg_duration_minutes)}</h3>
              <p className="text-sm text-indigo-600 font-medium mt-2 flex items-center gap-1">
                <Clock className="w-4 h-4"/> Temps d'intervention
              </p>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-l-4 border-l-emerald-500">
            <CardContent className="pt-6">
              <p className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-2">Requêtes Validées</p>
              <h3 className="text-4xl font-black text-white">{data.kpis.requests_validated}</h3>
              <p className="text-sm text-emerald-600 font-medium mt-2 flex items-center gap-1">
                <CheckCircle className="w-4 h-4"/> Acceptées par ChefOps
              </p>
            </CardContent>
          </Card>
          <Card className="shadow-sm border-l-4 border-l-rose-500">
            <CardContent className="pt-6">
              <p className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-2">Requêtes Rejetées</p>
              <h3 className="text-4xl font-black text-white">{data.request_trends.total_rejected}</h3>
              <p className="text-sm text-rose-600 font-medium mt-2 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4"/> Refusées
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          
          {/* Trends Chart */}
          <Card className="shadow-sm">
            <CardHeader className="bg-slate-800 pb-0">
              <CardTitle className="text-lg">Tendances des Requêtes (Approbations)</CardTitle>
            </CardHeader>
            <CardContent className="p-6 h-[320px]">
              {data.request_trends.daily_trends.length === 0 ? (
                <div className="h-full flex items-center justify-center text-blue-400">Aucune donnée de tendance</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.request_trends.daily_trends} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
                    <XAxis dataKey="date" tick={{fontSize: 11}} tickMargin={10} axisLine={false} tickLine={false} />
                    <YAxis tick={{fontSize: 11}} axisLine={false} tickLine={false} />
                    <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Legend iconType="circle" />
                    <Line type="monotone" dataKey="accepted" name="Acceptées" stroke="#10b981" strokeWidth={3} dot={{r:3}} />
                    <Line type="monotone" dataKey="rejected" name="Rejetées" stroke="#ef4444" strokeWidth={3} dot={{r:3}} />
                    <Line type="monotone" dataKey="pending" name="En Attente" stroke="#f59e0b" strokeWidth={3} dot={{r:3}} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Failures Spread */}
          <Card className="shadow-sm">
            <CardHeader className="bg-slate-800 pb-0">
              <CardTitle className="text-lg">Répartition Globale des Pannes</CardTitle>
            </CardHeader>
            <CardContent className="p-6 h-[320px]">
              {failureData.length === 0 ? (
                 <div className="h-full flex items-center justify-center text-blue-400">Aucune donnée</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={failureData}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={60}
                      paddingAngle={2}
                      dataKey="value"
                      label={({name, percent}) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {failureData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 2 - Tech Perf */}
        <Card className="shadow-sm mb-8">
          <CardHeader className="bg-slate-800 border-b border-blue-800/50">
            <CardTitle className="text-lg">Performance des Techniciens (Top Contributeurs)</CardTitle>
          </CardHeader>
          <CardContent className="p-6 h-[350px]">
            {data.technician_performance.length === 0 ? (
              <div className="h-full flex items-center justify-center text-blue-400">Aucune donnée technicien</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.technician_performance.slice(0, 10)} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                  <XAxis dataKey="technician_id" tickFormatter={(id) => `Tech #${id}`} tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="left" orientation="left" stroke="#3b82f6" />
                  <YAxis yAxisId="right" orientation="right" stroke="#f59e0b" />
                  <RechartsTooltip 
                    cursor={{fill: 'rgba(0,0,0,0.05)'}}
                    labelFormatter={(label) => `Technicien ID: ${label}`}
                  />
                  <Legend iconType="circle" />
                  <Bar yAxisId="left" dataKey="completed" name="OTs Complétés" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                  <Bar yAxisId="right" dataKey="avg_duration" name="Durée Moyenne (min)" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  );
};

export default SystemAnalytics;
