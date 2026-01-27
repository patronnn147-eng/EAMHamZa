import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Bell, Menu, X, LayoutDashboard, ClipboardList, Wrench, Settings, FileText, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export default function TechnicianLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await client.auth.me();
      if (response.data) {
        setUser(response.data);
        if (response.data.role !== 'TECHNICIEN') {
          navigate('/');
        }
      } else {
        navigate('/login');
      }
    } catch (error) {
      navigate('/login');
    }
  };

  const handleLogout = async () => {
    await client.auth.logout();
    navigate('/login');
  };

  const menuItems = [
    { path: '/technician/dashboard', label: 'Tableau de Bord', icon: LayoutDashboard },
    { path: '/technician/work-orders', label: 'Mes Ordres', icon: ClipboardList },
    { path: '/technician/interventions', label: 'Interventions', icon: Wrench },
    { path: '/technician/machines', label: 'Machines', icon: Settings },
    { path: '/technician/documents', label: 'Documents', icon: FileText },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
            <h1 className="text-xl font-bold text-gray-900">Espace Technicien</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="h-5 w-5" />
              <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 bg-red-500">
                0
              </Badge>
            </Button>
            <div className="hidden md:flex items-center gap-2">
              <span className="text-sm text-gray-600">{user?.email}</span>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Déconnexion
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } lg:translate-x-0 fixed lg:static inset-y-0 left-0 z-30 w-64 bg-white border-r border-gray-200 transition-transform duration-300 ease-in-out`}
        >
          <nav className="p-4 space-y-2 mt-16 lg:mt-0">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');
              return (
                <Button
                  key={item.path}
                  variant={isActive ? 'default' : 'ghost'}
                  className="w-full justify-start"
                  onClick={() => {
                    navigate(item.path);
                    setSidebarOpen(false);
                  }}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {item.label}
                </Button>
              );
            })}
            <div className="pt-4 border-t">
              <Button
                variant="ghost"
                className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={() => navigate('/technician/urgent-alert')}
              >
                <AlertTriangle className="mr-2 h-4 w-4" />
                Alerte Urgente
              </Button>
            </div>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}