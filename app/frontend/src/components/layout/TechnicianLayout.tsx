import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Bell, Menu, X, LayoutDashboard, ClipboardList, Wrench, Settings, FileText, AlertTriangle, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Notification {
  id: number;
  type: string;
  message: string;
  date_envoi: string;
  lu: boolean;
}

export default function TechnicianLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
    fetchNotifications();

    // Set up SSE connection
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;
    const eventSource = new EventSource(`${baseUrl}/api/v1/notifications/stream?token=${token}`);

    eventSource.onmessage = (event) => {
      try {
        const newNotif = JSON.parse(event.data);
        if (newNotif && newNotif.id) {
          setNotifications(prev => {
            if (prev.find(n => n.id === newNotif.id)) return prev;
            return [newNotif, ...prev].slice(0, 10);
          });
          setUnreadCount(prev => prev + 1);
        }
      } catch (err) {
        console.error('Error parsing SSE message:', err);
      }
    };

    eventSource.addEventListener('heartbeat', () => {
      console.debug('SSE Heartbeat');
    });

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
    };

    return () => {
      eventSource.close();
    };
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

  const fetchNotifications = async () => {
    try {
      const response = await client.apiCall.invoke({
        url: '/api/v1/notifications',
        method: 'GET',
        data: { skip: 0, limit: 10 },
      });
      setNotifications(response.data.items || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const markAsRead = async (notificationId: number) => {
    try {
      await client.apiCall.invoke({
        url: '/api/v1/notifications/mark-as-read',
        method: 'POST',
        data: { notification_ids: [notificationId] },
      });
      await fetchNotifications();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await client.apiCall.invoke({
        url: '/api/v1/notifications/mark-all-as-read',
        method: 'POST',
      });
      await fetchNotifications();
    } catch (error) {
      console.error('Error marking all as read:', error);
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
    { path: '/technician/planning', label: 'Planning', icon: Calendar },
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
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="relative">
                  <Bell className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 bg-red-500 text-white">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80">
                <div className="flex items-center justify-between px-4 py-2 border-b">
                  <h3 className="font-semibold">Notifications</h3>
                  {unreadCount > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={markAllAsRead}
                      className="text-xs"
                    >
                      Tout marquer comme lu
                    </Button>
                  )}
                </div>
                <ScrollArea className="h-96">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-sm text-gray-500">
                      Aucune notification
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <DropdownMenuItem
                        key={notif.id}
                        className={`flex flex-col items-start p-4 cursor-pointer ${!notif.lu ? 'bg-blue-50' : ''
                          }`}
                        onClick={() => !notif.lu && markAsRead(notif.id)}
                      >
                        <div className="flex items-start justify-between w-full">
                          <p className="text-sm font-medium">{notif.message}</p>
                          {!notif.lu && (
                            <Badge className="ml-2 h-2 w-2 rounded-full bg-blue-600 p-0" />
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(notif.date_envoi).toLocaleString('fr-FR')}
                        </p>
                      </DropdownMenuItem>
                    ))
                  )}
                </ScrollArea>
              </DropdownMenuContent>
            </DropdownMenu>
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
          className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'
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