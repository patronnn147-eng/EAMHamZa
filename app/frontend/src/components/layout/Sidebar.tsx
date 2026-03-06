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
  const baseItems: NavigationItem[] = [
    { name: 'Dashboard', href: `/${role.toLowerCase()}/dashboard`, icon: LayoutDashboard },
    { name: 'Machines', href: `/${role.toLowerCase()}/machines`, icon: Settings },
    { name: 'Work Orders', href: `/${role.toLowerCase()}/work-orders`, icon: ClipboardList },
    { name: 'Interventions', href: `/${role.toLowerCase()}/interventions`, icon: Wrench },
    { name: 'Planning', href: `/${role.toLowerCase()}/planning`, icon: Calendar },
    { name: 'Stocks', href: `/${role.toLowerCase()}/inventory`, icon: Package },
  ];


  if (['ADMIN', 'CHETOP', 'CHEFTECH'].includes(role)) {
    baseItems.push({ name: 'PDCA Kanban', href: '/pdca', icon: Columns });
  }

  // Add admin-specific items
  if (role === 'ADMIN') {
    baseItems.push({
      name: 'User Approvals',
      href: '/admin/user-approvals',
      icon: UserCheck,
    });

    baseItems.push({
      name: 'User Management',
      href: '/admin/users',
      icon: Users,
    });

    baseItems.push({
      name: 'IA & Prédictions',
      href: '/admin/ml',
      icon: BrainCircuit,
    });
  }

  // Add common items for admin roles
  if (['ADMIN', 'CHETOP', 'CHEFTECH'].includes(role)) {
    baseItems.push(
      { name: 'Reports', href: '/reports', icon: FileText },
      { name: 'Archives', href: '/archives', icon: Archive }
    );
  }

  return baseItems;
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
    <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 pt-16">
      <div className="flex-1 flex flex-col min-h-0 bg-gray-900">
        <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
          <nav className="mt-5 flex-1 px-2 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                location.pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    isActive
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white',
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors'
                  )}
                >
                  <item.icon
                    className={cn(
                      isActive ? 'text-white' : 'text-gray-400 group-hover:text-gray-300',
                      'mr-3 flex-shrink-0 h-6 w-6'
                    )}
                    aria-hidden="true"
                  />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}