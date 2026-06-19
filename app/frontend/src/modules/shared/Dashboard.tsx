import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Settings, 
  ClipboardList, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  TrendingUp
} from 'lucide-react';
import type { DashboardMetrics, Machine, OrdreTravail } from '@/lib/types';
import { Link } from 'react-router-dom';
import { BriefingBar } from './dashboard/BriefingBar';
import { NextBestActions } from './dashboard/NextBestActions';
import { DashboardSkeleton } from './dashboard/DashboardSkeleton';
import { DeltaBadge } from './dashboard/DeltaBadge';
import { DashboardFilters } from './dashboard/DashboardFilters';
import { loadFilters, saveFilters, DashboardFilterState } from './dashboard/dashboardFilters';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalMachines: 0,
    activeMachines: 0,
    pendingWorkOrders: 0,
    urgentWorkOrders: 0,
    completedThisWeek: 0,
    upcomingMaintenance: 0,
  });
  const [recentWorkOrders, setRecentWorkOrders] = useState<OrdreTravail[]>([]);
  const [upcomingMaintenance, setUpcomingMaintenance] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);

  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); }
    catch { return {}; }
  })();
  const userId = String(currentUser.id ?? 'anon');
  const [filters, setFilters] = useState<DashboardFilterState>(() => loadFilters(userId));
  const updateFilters = (f: DashboardFilterState) => { setFilters(f); saveFilters(userId, f); };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch machines
      const machinesResponse = await client.entities.machines.query({
        query: {},
        limit: 100
      });
      const machines = machinesResponse.data.items || [];

      // Fetch work orders
      const workOrdersResponse = await client.entities.ordres_travail.query({
        query: {},
        sort: '-created_at',
        limit: 100
      });
      const workOrders = workOrdersResponse.data.items || [];

      // Calculate metrics
      const activeMachines = machines.filter((m: Machine) => m.statut === 'EN_COURS').length;
      const pendingWorkOrders = workOrders.filter((wo: OrdreTravail) => wo.statut === 'EN_ATTENTE').length;
      const urgentWorkOrders = workOrders.filter((wo: OrdreTravail) => wo.priorite === 'URGENTE' && wo.statut !== 'TERMINE').length;
      
      const oneWeekAgo = new Date();
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
      const completedThisWeek = workOrders.filter((wo: OrdreTravail) => {
        return wo.statut === 'TERMINE' && new Date(wo.created_at) >= oneWeekAgo;
      }).length;

      const now = new Date();
      const upcomingMaintenanceMachines = machines.filter((m: Machine) => {
        if (!m.date_prochaine_maintenance) return false;
        const maintenanceDate = new Date(m.date_prochaine_maintenance);
        const daysUntil = (maintenanceDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
        return daysUntil <= 7 && daysUntil >= 0;
      });

      setMetrics({
        totalMachines: machines.length,
        activeMachines,
        pendingWorkOrders,
        urgentWorkOrders,
        completedThisWeek,
        upcomingMaintenance: upcomingMaintenanceMachines.length,
      });

      setRecentWorkOrders(workOrders.slice(0, 5));
      setUpcomingMaintenance(upcomingMaintenanceMachines.slice(0, 5));
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (statut: string) => {
    const statusConfig = {
      EN_ATTENTE: { label: 'Pending', variant: 'secondary' as const },
      EN_COURS: { label: 'In Progress', variant: 'default' as const },
      TERMINE: { label: 'Completed', variant: 'outline' as const },
      ANNULE: { label: 'Cancelled', variant: 'destructive' as const },
    };
    const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getPriorityBadge = (priorite: string) => {
    const priorityConfig = {
      BASSE: { label: 'Low', className: 'bg-gray-100 text-blue-50' },
      MOYENNE: { label: 'Medium', className: 'bg-blue-100 text-blue-800' },
      ELEVEE: { label: 'High', className: 'bg-orange-100 text-orange-800' },
      URGENTE: { label: 'Urgent', className: 'bg-red-100 text-red-800' },
    };
    const config = priorityConfig[priorite as keyof typeof priorityConfig] || priorityConfig.MOYENNE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-4xl font-bold text-white">Dashboard</h2>
        <p className="mt-1 text-sm text-blue-300">
          Overview of your asset management system
        </p>
      </div>

      <DashboardFilters value={filters} onChange={updateFilters} />
      <BriefingBar site={filters.site} />
      <NextBestActions
        role={currentUser.role || 'ADMIN'}
        userId={Number(currentUser.id) || undefined}
        workOrders={recentWorkOrders.map((wo) => ({
          id: wo.id, priorite: wo.priorite, statut: wo.statut,
          technicien_id: (wo as any).utilisateur_id, machine_id: (wo as any).machine_id,
        }))}
        overduePMs={upcomingMaintenance.map((m) => ({ machine_id: m.id, nom: m.nom }))}
        alerts={[]}
      />

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Machines</CardTitle>
            <Settings className="h-4 w-4 text-blue-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.totalMachines}</div>
            <p className="text-xs text-blue-300 mt-1">
              {metrics.activeMachines} currently active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Work Orders</CardTitle>
            <ClipboardList className="h-4 w-4 text-blue-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.pendingWorkOrders}</div>
            <p className="text-xs text-blue-300 mt-1">
              Awaiting assignment or start
            </p>
          </CardContent>
        </Card>

        <Link to="/work-orders?priority=URGENTE">
          <Card className="cursor-pointer hover:bg-slate-700/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Urgent Work Orders</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{metrics.urgentWorkOrders}</div>
              <DeltaBadge current={metrics.urgentWorkOrders} previous={metrics.urgentWorkOrders} />
            </CardContent>
          </Card>
        </Link>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed This Week</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{metrics.completedThisWeek}</div>
            <p className="text-xs text-blue-300 mt-1">
              Work orders finished
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Upcoming Maintenance</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{metrics.upcomingMaintenance}</div>
            <p className="text-xs text-blue-300 mt-1">
              Due within 7 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {metrics.totalMachines > 0 
                ? Math.round((metrics.activeMachines / metrics.totalMachines) * 100) 
                : 0}%
            </div>
            <p className="text-xs text-blue-300 mt-1">
              Machines operational
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Work Orders */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Work Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentWorkOrders.length === 0 ? (
              <p className="text-sm text-blue-300 text-center py-4">No work orders found</p>
            ) : (
              recentWorkOrders.map((wo) => (
                <div key={wo.id} className="flex items-center justify-between border-b pb-3 last:border-b-0">
                  <div className="flex-1">
                    <p className="text-sm font-medium">Work Order #{wo.id}</p>
                    <p className="text-xs text-blue-300">
                      Due: {new Date(wo.date_echeance).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getPriorityBadge(wo.priorite)}
                    {getStatusBadge(wo.statut)}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Upcoming Maintenance */}
      <Card>
        <CardHeader>
          <CardTitle>Upcoming Maintenance (Next 7 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {upcomingMaintenance.length === 0 ? (
              <p className="text-sm text-blue-300 text-center py-4">No upcoming maintenance scheduled</p>
            ) : (
              upcomingMaintenance.map((machine) => (
                <div key={machine.id} className="flex items-center justify-between border-b pb-3 last:border-b-0">
                  <div className="flex items-center space-x-3">
                    <img 
                      src={machine.image_url || 'https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/e1cfe394-7674-4c68-a85b-56fb0119fd9d.png'} 
                      alt={machine.nom}
                      className="h-10 w-10 rounded object-cover"
                    />
                    <div>
                      <p className="text-sm font-medium">{machine.nom}</p>
                      <p className="text-xs text-blue-300">{machine.identifiant_machine}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-orange-600">
                      {new Date(machine.date_prochaine_maintenance!).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-blue-300">{machine.emplacement}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}