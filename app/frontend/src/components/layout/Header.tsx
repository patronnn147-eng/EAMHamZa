import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bell, LogOut, User, Menu, PanelLeftClose, Sun, Moon } from 'lucide-react';
import { useSidebar } from '@/hooks/useSidebar';
import { useTheme } from '@/contexts/ThemeContext';

interface UserData {
  id: string;
  email: string;
}

interface Notification {
  id: number;
  type: string;
  message: string;
  date_envoi: string;
  lu: boolean;
}

function mergeNewNotification(prev: Notification[], newNotif: Notification): Notification[] {
  if (prev.some((n) => n.id === newNotif.id)) return prev;
  return [newNotif, ...prev].slice(0, 10);
}

export default function Header() {
  const [user, setUser] = useState<UserData | null>(null);
  const [userRole, setUserRole] = useState<string>('');
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const { collapsed, toggle } = useSidebar();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await client.auth.me();
        if (userData.data) {
          setUser(userData.data);

          if (userData.data.role) {
            setUserRole(userData.data.role);
          }
        }
      } catch (error) {
        console.error('Error fetching user:', error);
      }
    };

    fetchUser();
  }, []);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await client.apiCall.invoke({
          url: '/api/v1/notifications?page=1&size=10',
          method: 'GET',
        });

        const data = (response as { data?: { items?: Notification[]; unread_count?: number } }).data;
        setNotifications(data?.items || []);
        setUnreadCount(data?.unread_count || 0);
      } catch (error) {
        console.error('Error fetching initial notifications:', error);
      }
    };

    fetchNotifications();

    // Set up SSE connection
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || globalThis.location.origin;
    const eventSource = new EventSource(`${baseUrl}/api/v1/notifications/stream?token=${token}`);

    eventSource.onmessage = (event) => {
      try {
        const newNotif = JSON.parse(event.data);
        if (newNotif?.id) {
          setNotifications((prev) => mergeNewNotification(prev, newNotif));
          setUnreadCount(prev => prev + 1);
        }
      } catch (err) {
        console.error('Error parsing SSE message:', err);
      }
    };

    eventSource.addEventListener('heartbeat', () => {
      // Just a keep-alive, no action needed
      console.debug('SSE Heartbeat');
    });

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      // EventSource auto-reconnects by default, but we log the error
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const markAsRead = async (notificationId: number) => {
    try {
      await client.apiCall.invoke({
        url: '/api/v1/notifications/mark-as-read',
        method: 'POST',
        data: { notification_ids: [notificationId] },
      });

      const response = await client.apiCall.invoke({
        url: '/api/v1/notifications?page=1&size=10',
        method: 'GET',
      });

      const data = (response as { data?: { items?: Notification[]; unread_count?: number } }).data;
      setNotifications(data?.items || []);
      setUnreadCount(data?.unread_count || 0);
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

      const response = await client.apiCall.invoke({
        url: '/api/v1/notifications?page=1&size=10',
        method: 'GET',
      });

      const data = (response as { data?: { items?: Notification[]; unread_count?: number } }).data;
      setNotifications(data?.items || []);
      setUnreadCount(data?.unread_count || 0);
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await client.auth.logout();
      globalThis.location.href = '/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const getInitials = (email: string) => {
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <header className="bg-[hsl(226_70%_40%)] dark:bg-gradient-to-r dark:from-slate-900 dark:via-blue-900 dark:to-slate-900 border-b border-[hsl(226_70%_32%)] dark:border-blue-800 sticky top-0 z-50 backdrop-blur-md">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggle}
              aria-label={collapsed ? 'Afficher la barre latérale' : 'Masquer la barre latérale'}
              title={collapsed ? 'Afficher la barre latérale' : 'Masquer la barre latérale'}
              className="text-white/90 dark:text-blue-100 hover:text-white dark:hover:text-white hover:bg-white/10 dark:hover:bg-blue-800/40"
            >
              {collapsed ? <Menu className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </Button>
            <img
              src="https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/44d01b7c-ac50-4b6d-9ccb-0a74219d8673.png"
              alt="Logo"
              className="h-8 w-8"
            />
            <h1 className="text-xl font-bold text-white dark:text-white">Asset Management</h1>
          </div>

          <div className="flex items-center space-x-4">
            {userRole && (
              <span className="text-sm text-white bg-white/15 dark:bg-blue-600/30 border border-white/25 dark:border-blue-500/30 px-3 py-1 rounded-full">
                {userRole}
              </span>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="relative text-white/90 hover:text-white hover:bg-white/10 dark:text-inherit dark:hover:bg-accent">
                  <Bell className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 bg-red-500 text-white">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-80">
                <div className="flex items-center justify-between px-4 py-2 border-b">
                  <h3 className="font-semibold">Notifications</h3>
                  {unreadCount > 0 && (
                    <Button variant="ghost" size="sm" onClick={markAllAsRead} className="text-xs">
                      Tout marquer comme lu
                    </Button>
                  )}
                </div>
                <ScrollArea className="h-96">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-sm text-gray-500">Aucune notification</div>
                  ) : (
                    notifications.map((notif) => (
                      <DropdownMenuItem
                        key={notif.id}
                        className={`flex flex-col items-start p-4 cursor-pointer ${notif.lu ? '' : 'bg-blue-50 dark:bg-blue-900/30'}`}
                        onClick={() => !notif.lu && markAsRead(notif.id)}
                      >
                        <div className="flex items-start justify-between w-full">
                          <p className="text-sm font-medium">{notif.message}</p>
                          {!notif.lu && <Badge className="ml-2 h-2 w-2 rounded-full bg-blue-600 p-0" />}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{new Date(notif.date_envoi).toLocaleString('fr-FR')}</p>
                      </DropdownMenuItem>
                    ))
                  )}
                </ScrollArea>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar>
                    <AvatarFallback className="bg-gradient-to-br from-blue-500 to-cyan-500 text-white">
                      {user?.email ? getInitials(user.email) : <User className="h-5 w-5" />}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">My Account</p>
                    {user?.email && (
                      <p className="text-xs text-blue-600 dark:text-blue-300">{user.email}</p>
                    )}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuItem
                  onClick={toggleTheme}
                  className="text-slate-700 dark:text-blue-100 focus:bg-slate-100 dark:focus:bg-blue-800/40 cursor-pointer"
                >
                  {theme === 'dark' ? (
                    <><Sun className="mr-2 h-4 w-4" /><span>Mode Clair</span></>
                  ) : (
                    <><Moon className="mr-2 h-4 w-4" /><span>Mode Sombre</span></>
                  )}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-slate-700 dark:text-blue-100 focus:bg-slate-100 dark:focus:bg-blue-800/40">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  );
}