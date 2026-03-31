import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, 
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts';
import { AlertCircle, Clock, CheckCircle2, TrendingUp, RefreshCw } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#ffc658'];

interface AnalyticsData {
  summary: {
    total_assigned: number;
    completed: number;
    pending: number;
    in_progress: number;
    avg_duration: number;
    failure_types: Record<string, number>;
  };
  pdca: {
    plan: number;
    do: number;
    check: number;
    act: number;
  };
  trends: Array<{
    date: string;
    completed: number;
  }>;
  alerts: {
    late_wos: number;
    top_failure: string;
  };
}

const FAILURE_LABELS: Record<string, string> = {
  NONE: 'Aucune panne',
  TWF: 'TWF — Usure outil',
  HDF: 'HDF — Thermique',
  PWF: 'PWF — Électrique',
  OSF: 'OSF — Surcharge',
  RNF: 'RNF — Aléatoire',
};

export const AnalyticsTab: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/cheftech/analytics/dashboard`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error('Failed to load analytics', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (!data) return <div>Erreur de chargement des données.</div>;

  const failureData = Object.entries(data.summary.failure_types).map(([key, value]) => ({
    name: FAILURE_LABELS[key] || key,
    value,
  }));

  const totalPdca = data.pdca.plan + data.pdca.do + data.pdca.check + data.pdca.act || 1; // avoid division by zero

  const formatDuration = (mins: number) => {
    if (mins < 60) return `${mins} min`;
    return `${Math.floor(mins / 60)}h ${mins % 60}min`;
  };

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="shadow-sm">
          <CardContent className="pt-4 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-bold uppercase">Total Assurances</p>
              <h3 className="text-2xl font-black mt-1">{data.summary.total_assigned}</h3>
            </div>
            <div className="bg-indigo-100 p-2 rounded-full text-indigo-600"><TrendingUp size={20} /></div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="pt-4 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-bold uppercase">Taux de Plannings Actifs</p>
              <h3 className="text-2xl font-black mt-1 text-blue-600">{data.summary.in_progress}</h3>
            </div>
            <div className="bg-blue-100 p-2 rounded-full text-blue-600"><RefreshCw size={20} /></div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="pt-4 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-bold uppercase">Durée Moyenne</p>
              <h3 className="text-2xl font-black mt-1 text-amber-600">{formatDuration(data.summary.avg_duration)}</h3>
            </div>
            <div className="bg-amber-100 p-2 rounded-full text-amber-600"><Clock size={20} /></div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-l-4 border-l-red-500">
          <CardContent className="pt-4 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-red-500 font-bold uppercase flex items-center gap-1">
                <AlertCircle size={14} /> OTs en Retard
              </p>
              <h3 className="text-2xl font-black mt-1 text-red-600">{data.alerts.late_wos}</h3>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* PDCA Visual Tracker */}
      <Card className="border-indigo-100 shadow-md">
        <CardHeader className="bg-indigo-50/50 pb-4 border-b">
          <CardTitle className="text-base text-indigo-900 flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-indigo-500" />
            Cycle PDCA Actif (Plan - Do - Check - Act)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex gap-2 h-8 rounded-lg overflow-hidden border bg-gray-100">
            <div 
              style={{ width: `${(data.pdca.plan / totalPdca) * 100}%` }} 
              className="bg-blue-400 h-full flex items-center justify-center transition-all group relative pl-1"
            >
              {data.pdca.plan > 0 && <span className="text-[10px] font-bold text-white uppercase truncate">Plan ({data.pdca.plan})</span>}
            </div>
            <div 
              style={{ width: `${(data.pdca.do / totalPdca) * 100}%` }} 
              className="bg-yellow-400 h-full flex items-center justify-center transition-all"
            >
              {data.pdca.do > 0 && <span className="text-[10px] font-bold text-yellow-900 uppercase truncate">Do ({data.pdca.do})</span>}
            </div>
            <div 
              style={{ width: `${(data.pdca.check / totalPdca) * 100}%` }} 
              className="bg-green-400 h-full flex items-center justify-center transition-all"
            >
              {data.pdca.check > 0 && <span className="text-[10px] font-bold text-green-900 uppercase truncate">Check ({data.pdca.check})</span>}
            </div>
            <div 
              style={{ width: `${(data.pdca.act / totalPdca) * 100}%` }} 
              className="bg-red-400 h-full flex items-center justify-center transition-all bg-gradient-to-r from-red-400 to-red-500"
            >
              {data.pdca.act > 0 && <span className="text-[10px] font-bold text-white uppercase truncate">Act ({data.pdca.act})</span>}
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-3 text-xs text-gray-500 px-1 text-center">
            <div>
              <span className="font-bold text-blue-700">PLAN:</span> <br/>Demandes en attente
            </div>
            <div>
              <span className="font-bold text-yellow-700">DO:</span> <br/>Assignés & En cours
            </div>
            <div>
              <span className="font-bold text-green-700">CHECK:</span> <br/>OTs Terminés (Brut)
            </div>
            <div>
              <span className="font-bold text-red-700">ACT:</span> <br/>Feedbacks ChefTech
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm">Tendances de Complétion (Historique)</CardTitle>
          </CardHeader>
          <CardContent className="h-[250px]">
            {data.trends.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-400 text-sm italic">
                Pas assez de données
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis dataKey="date" tick={{fontSize: 10}} tickMargin={10} axisLine={false} tickLine={false} />
                  <YAxis tick={{fontSize: 10}} axisLine={false} tickLine={false} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="completed" 
                    stroke="#4F46E5" 
                    strokeWidth={3}
                    dot={{ r: 4, strokeWidth: 2 }}
                    activeDot={{ r: 6 }} 
                    name="OT Complétés" 
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Failures Pie Chart */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              Typologie des Pannes
              {data.alerts.top_failure !== "N/A" && (
                <Badge variant="destructive" className="ml-2 font-normal">
                  Dominant: {FAILURE_LABELS[data.alerts.top_failure] || data.alerts.top_failure}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[250px]">
            {failureData.length === 0 ? (
               <div className="h-full flex items-center justify-center text-gray-400 text-sm italic">
                 Pas assez de données
               </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={failureData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {failureData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  );
};
