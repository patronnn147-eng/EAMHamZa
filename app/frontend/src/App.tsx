import { useEffect } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { Toaster as ToasterUI } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { DataSyncProvider } from './contexts/DataSyncContext';
import { AuthProvider } from './contexts/AuthContext';
import { AppRoutes } from './app/routing';
import { ChatWidget } from './modules/shared/ChatInterface';

const queryClient = new QueryClient();

function App() {
  useEffect(() => {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <DataSyncProvider>
          <TooltipProvider>
            <Toaster />
            <ToasterUI />
            <BrowserRouter>
              <AppRoutes />
              <ChatWidget />
            </BrowserRouter>
          </TooltipProvider>
        </DataSyncProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;