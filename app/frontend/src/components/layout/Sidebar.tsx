import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Settings,
  Wrench,
  ClipboardList,
  Calendar,
  FileText,
  Archive,
  UserCheck,
  Users,
  Columns,
  Package,
  BrainCircuit,
  LucideIcon,
  Bell,
  MessageSquare,
  Activity,
  History,
  ChevronLeft,
  ListChecks,
  Database,
  PackageSearch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { client } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSidebar } from '@/hooks/useSidebar';

interface NavigationItem {
  name: string;
  href: string;
  icon: LucideIcon;
  roles?: string[];
}

const getNavigationItems = (role: string): NavigationItem[] => {
  const roleLower = role.toLowerCase();
  
  if (role === 'ADMIN') {
    return [
      { name: 'Admin Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
      { name: 'Planning', href: '/admin/planning', icon: Calendar },
      { name: 'Utilisateurs', href: '/admin/users', icon: Users },
      { name: 'Approbations Users', href: '/admin/user-approvals', icon: UserCheck },
      { name: 'Approbations ITV', href: '/admin/itv-approvals', icon: ClipboardList },
      { name: 'Gestion des OT', href: '/admin/work-orders-management', icon: FileText },
      { name: 'Machines', href: '/admin/machines', icon: Settings },
      { name: 'Stocks / Pièces', href: '/admin/inventory', icon: Package },
      { name: 'File pièces non-cat.', href: '/admin/pending-pieces', icon: PackageSearch },
      { name: 'ML & Prédictions', href: '/admin/ml', icon: BrainCircuit },
      { name: 'Dashboard IA Flotte', href: '/ml-dashboard', icon: BrainCircuit },
      { name: 'IoT Dashboard', href: '/iot-dashboard', icon: Activity },
      { name: 'Alertes Prédictives', href: '/alerts', icon: Bell },
      { name: 'Assistant IA', href: '/chat', icon: MessageSquare },
      { name: 'Base Documentaire', href: '/rag-documents', icon: Database },
      { name: 'Historique (Audit)', href: '/audit-log', icon: History },
      { name: 'Configuration Alertes', href: '/admin/alert-config', icon: Bell },
      { name: 'Rapports Planifiés', href: '/admin/report-scheduler', icon: FileText },
      { name: 'Télécharger Rapports', href: '/reports-download', icon: FileText },
      { name: 'PDCA Kanban', href: '/pdca', icon: Columns },
      { name: 'Archive (Échéances)', href: '/admin/archive', icon: Archive },
      { name: 'Archives', href: '/archives', icon: Archive }
    ];
  }

  if (role === 'CHETOP') {
    return [
      { name: 'Mes Demandes', href: '/chetop/dashboard', icon: LayoutDashboard },
      { name: 'Parc Machines', href: '/chetop/machines', icon: Settings },
      { name: 'Demandes Intervention', href: '/chetop/itv-requests', icon: ClipboardList },
      { name: 'Ordres de Travail', href: '/chetop/work-orders', icon: Wrench },
      { name: 'PDCA Kanban', href: '/pdca', icon: Columns },
      { name: 'Archive', href: '/chetop/archive', icon: Archive },
      { name: 'Archives', href: '/archives', icon: Archive },
      { name: 'Base Documentaire', href: '/rag-documents', icon: Database }
    ];
  }

  if (role === 'CHEFTECH') {
    return [
      { name: 'Validation Hub', href: '/cheftech/dashboard', icon: LayoutDashboard },
      { name: 'Planning & Equipes', href: '/cheftech/planning', icon: Calendar },
      { name: 'Tâches de Planning', href: '/cheftech/plannings-taches', icon: Calendar },
      { name: 'Suivi des OT', href: '/cheftech/work-orders-table', icon: Wrench },
      { name: 'Interventions', href: '/cheftech/interventions', icon: Wrench },
      { name: 'Stocks / Pièces', href: '/cheftech/inventory', icon: Package },
      { name: 'IoT Dashboard', href: '/iot-dashboard', icon: Activity },
      { name: 'Alertes Prédictives', href: '/alerts', icon: Bell },
      { name: 'Centre des alertes', href: '/cheftech/alerts', icon: Bell },
      { name: 'Assistant IA', href: '/chat', icon: MessageSquare },
      { name: 'Base Documentaire', href: '/rag-documents', icon: Database },
      { name: 'Historique (Audit)', href: '/audit-log', icon: History },
      { name: 'Télécharger Rapports', href: '/reports-download', icon: FileText },
      { name: 'PDCA Kanban', href: '/pdca', icon: Columns },
      { name: 'Rapports', href: '/reports', icon: FileText },
      { name: 'Archive', href: '/cheftech/archive', icon: Archive }
    ];
  }

  if (role === 'TECHNICIEN') {
    return [
      { name: 'Mes Tâches', href: '/technician/dashboard', icon: LayoutDashboard },
      { name: 'Mes Ordres de Travail', href: '/technician/work-orders', icon: ClipboardList },
      { name: 'Interventions', href: '/technician/interventions', icon: Wrench },
      { name: 'Planning', href: '/technician/planning', icon: Calendar },
      { name: 'Tâches de Planning', href: '/technician/planning-taches', icon: ListChecks },
      { name: 'Machines', href: '/technician/machines', icon: Settings },
      { name: 'Docs Techniques', href: '/technician/documents', icon: FileText },
      { name: 'Base Documentaire', href: '/rag-documents', icon: Database },
      { name: 'Stocks', href: '/technician/inventory', icon: Package },
      { name: 'Archive', href: '/technician/archive', icon: Archive }
    ];
  }

  return [
    { name: 'Dashboard', href: `/${roleLower}/dashboard`, icon: LayoutDashboard }
  ];
};

export default function Sidebar() {
  const location = useLocation();
  const [navigation, setNavigation] = useState<NavigationItem[]>([]);
  const [pendingPiecesCount, setPendingPiecesCount] = useState<number>(0);

  // Poll pending-pieces count for ADMIN sidebar badge (every 60s)
  useEffect(() => {
    const role = (() => {
      try {
        const stored = localStorage.getItem('user');
        if (stored) return (JSON.parse(stored).role || '').toUpperCase();
      } catch { /* ignore */ }
      return '';
    })();
    if (role !== 'ADMIN' && role !== 'CHEFTECH') return;

    let cancelled = false;
    const apiBase = import.meta.env.VITE_API_BASE_URL || '';
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const tick = async () => {
      try {
        const resp = await fetch(`${apiBase}/api/v1/inventory/pending?status=PENDING_REVIEW&size=1`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.ok && !cancelled) {
          const body = await resp.json();
          setPendingPiecesCount(body.total ?? 0);
        }
      } catch { /* silent — non-critical badge */ }
    };

    tick();
    const handle = window.setInterval(tick, 60_000);
    return () => { cancelled = true; window.clearInterval(handle); };
  }, []);

  const { user } = useAuth();
  const { collapsed, toggle } = useSidebar();

  useEffect(() => {
    const fetchUserRole = async () => {
      try {
        const roleFromContext = (user?.role ?? '').toUpperCase();
        if (roleFromContext) {
          setNavigation(getNavigationItems(roleFromContext));
          return;
        }

        const userData = await client.auth.me();
        const roleFromMe = (userData.data?.role ?? '').toUpperCase();
        if (roleFromMe) {
          setNavigation(getNavigationItems(roleFromMe));
          return;
        }

        const section = location.pathname.split('/')[1]?.toUpperCase();
        const roleFromPath = section === 'ADMIN' || section === 'CHETOP' || section === 'CHEFTECH' ? section : '';
        if (roleFromPath) {
          setNavigation(getNavigationItems(roleFromPath));
        }
      } catch (error) {
        console.error('Error fetching user role:', error);
      }
    };

    fetchUserRole();
  }, [location.pathname, user?.role]);

  return (
    <div
      className={cn(
        'hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 pt-16 z-40 transition-transform duration-300 ease-in-out',
        collapsed ? '-translate-x-full' : 'translate-x-0'
      )}
      aria-hidden={collapsed}
    >
      <div className="flex-1 flex flex-col min-h-0 bg-gradient-to-b from-slate-900/95 to-blue-950/95 m-3 rounded-2xl shadow-2xl border border-blue-800/30 overflow-hidden transition-all duration-500 backdrop-blur-md">
        <div className="flex-1 flex flex-col pt-6 pb-4 overflow-y-auto font-sans">
          <div className="px-6 mb-6 flex items-center justify-between">
            <h2 className="text-[10px] font-bold text-blue-400/60 uppercase tracking-[0.2em] opacity-80">
              Navigation Principal
            </h2>
            <button
              type="button"
              onClick={toggle}
              aria-label="Masquer la barre latérale"
              title="Masquer la barre latérale"
              className="p-1 rounded-md text-blue-300/70 hover:text-blue-100 hover:bg-blue-800/40 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
          <nav className="flex-1 px-3 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                location.pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'group flex items-center px-4 py-3 text-[13px] font-semibold rounded-xl transition-all duration-300 relative overflow-hidden',
                    isActive
                      ? 'bg-blue-600/40 text-blue-50 border-l-2 border-blue-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
                      : 'text-blue-200/70 hover:bg-blue-800/30 hover:text-blue-50'
                  )}
                >
                  {isActive && (
                    <div className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-premium rounded-full shadow-[0_0_15px_rgba(139,92,246,0.8)]" />
                  )}
                  <item.icon
                    className={cn(
                      isActive ? 'text-white scale-110' : 'text-blue-400/70 group-hover:text-blue-200',
                      'mr-3 flex-shrink-0 h-5 w-5 transition-all duration-300 group-hover:rotate-3'
                    )}
                    aria-hidden="true"
                  />
                  <span className="relative z-10 transition-transform duration-300 group-hover:translate-x-1">
                    {item.name}
                  </span>
                  {item.href === '/admin/pending-pieces' && pendingPiecesCount > 0 && (
                    <span className="ml-auto inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-amber-500/90 text-white text-[10px] font-bold tabular-nums shadow-md shadow-amber-500/40 animate-pulse">
                      {pendingPiecesCount > 99 ? '99+' : pendingPiecesCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}