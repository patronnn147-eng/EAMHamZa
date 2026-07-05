import { useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import Header from './Header';
import Sidebar from './Sidebar';
import { useSidebar } from '@/hooks/useSidebar';
import { cn } from '@/lib/utils';

export default function TechnicianLayout() {
  const navigate = useNavigate();
  const { collapsed } = useSidebar();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await client.auth.me();
        if (response.data) {
          if (response.data.role !== 'TECHNICIEN') {
            navigate('/');
          }
        } else {
          navigate('/login');
        }
      } catch {
        navigate('/login');
      }
    };

    checkAuth();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-background dark:bg-gradient-to-b dark:from-slate-950 dark:via-blue-950 dark:to-slate-950">
      <div className="fixed inset-0 mesh-gradient opacity-30 -z-10 hidden dark:block" />
      <Header />
      <Sidebar />
      <div
        className={cn(
          'flex flex-col flex-1 transition-[padding] duration-300 ease-in-out',
          collapsed ? 'md:pl-0' : 'md:pl-64'
        )}
      >
        <main className="flex-1 pt-16">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
