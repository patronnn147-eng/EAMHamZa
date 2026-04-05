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
  LucideIcon
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { client } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

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
      { name: 'ML & Prédictions', href: '/admin/ml', icon: BrainCircuit },
      { name: 'Dashboard IA Flotte', href: '/ml-dashboard', icon: BrainCircuit },
      { name: 'PDCA Kanban', href: '/pdca', icon: Columns },
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
      { name: 'Archives', href: '/archives', icon: Archive }
    ];
  }

  if (role === 'CHEFTECH') {
    return [
      { name: 'Validation Hub', href: '/cheftech/dashboard', icon: LayoutDashboard },
      { name: 'Planning & Equipes', href: '/cheftech/planning', icon: Calendar },
      { name: 'Ordres Travail', href: '/cheftech/work-orders', icon: ClipboardList },
      { name: 'Suivi des OT', href: '/cheftech/work-orders-table', icon: Wrench },
      { name: 'Interventions', href: '/cheftech/interventions', icon: Wrench },
      { name: 'Stocks / Pièces', href: '/cheftech/inventory', icon: Package },
      { name: 'PDCA Kanban', href: '/pdca', icon: Columns },
      { name: 'Rapports', href: '/reports', icon: FileText }
    ];
  }

  if (role === 'TECHNICIEN') {
    return [
      { name: 'Mes Tâches', href: '/technicien/dashboard', icon: LayoutDashboard },
      { name: 'Mes Ordres de Travail', href: '/technicien/work-orders', icon: ClipboardList },
      { name: 'Interventions', href: '/technicien/interventions', icon: Wrench },
      { name: 'Planning', href: '/technicien/planning', icon: Calendar },
      { name: 'Docs Techniques', href: '/technicien/documents', icon: FileText },
      { name: 'Stocks', href: '/technicien/inventory', icon: Package }
    ];
  }

  return [
    { name: 'Dashboard', href: `/${roleLower}/dashboard`, icon: LayoutDashboard }
  ];
};

export default function Sidebar() {
  const location = useLocation();
  const [navigation, setNavigation] = useState<NavigationItem[]>([]);
  const { user } = useAuth();

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
    <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 pt-16 z-40">
      <div className="flex-1 flex flex-col min-h-0 glass-dark m-3 rounded-2xl shadow-2xl border-white/5 overflow-hidden transition-all duration-500">
        <div className="flex-1 flex flex-col pt-6 pb-4 overflow-y-auto font-sans">
          <div className="px-6 mb-6">
            <h2 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] opacity-80">
              Navigation Principal
            </h2>
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
                      ? 'bg-white/10 text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  )}
                >
                  {isActive && (
                    <div className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-premium rounded-full shadow-[0_0_15px_rgba(139,92,246,0.8)]" />
                  )}
                  <item.icon
                    className={cn(
                      isActive ? 'text-white scale-110' : 'text-gray-500 group-hover:text-gray-300',
                      'mr-3 flex-shrink-0 h-5 w-5 transition-all duration-300 group-hover:rotate-3'
                    )}
                    aria-hidden="true"
                  />
                  <span className="relative z-10 transition-transform duration-300 group-hover:translate-x-1">
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}