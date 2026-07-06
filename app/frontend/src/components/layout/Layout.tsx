import { ReactNode } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import { useSidebar } from '@/hooks/useSidebar';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: Readonly<LayoutProps>) {
  const { collapsed } = useSidebar();

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
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
