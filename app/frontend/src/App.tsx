import { useEffect, useState } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { Toaster as ToasterUI } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { client } from './lib/api';
import Layout from './components/layout/Layout';
import TechnicianLayout from './components/layout/TechnicianLayout';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import Machines from './pages/Machines';
import WorkOrders from './pages/WorkOrders';
import Interventions from './pages/Interventions';
import PlanningPage from './pages/Planning';
import Reports from './pages/Reports';
import Archives from './pages/Archives';
import TechnicianDashboard from './pages/technician/TechnicianDashboard';
import TechnicianWorkOrders from './pages/technician/TechnicianWorkOrders';
import TechnicianWorkOrderDetail from './pages/technician/TechnicianWorkOrderDetail';
import TechnicianInterventions from './pages/technician/TechnicianInterventions';
import TechnicianMachines from './pages/technician/TechnicianMachines';
import TechnicianMachineDetail from './pages/technician/TechnicianMachineDetail';
import TechnicianDocuments from './pages/technician/TechnicianDocuments';
import TechnicianUrgentAlert from './pages/technician/TechnicianUrgentAlert';
import NotFound from './pages/NotFound';

const queryClient = new QueryClient();

function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await client.auth.me();
      if (user.data) {
        setIsAuthenticated(true);
        setUserRole(user.data.role);
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      setIsAuthenticated(false);
    }
  };

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && userRole && !allowedRoles.includes(userRole)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function RoleBasedRedirect() {
  const [loading, setLoading] = useState(true);
  const [redirectPath, setRedirectPath] = useState<string>('/');

  useEffect(() => {
    checkRole();
  }, []);

  const checkRole = async () => {
    try {
      const user = await client.auth.me();
      if (user.data) {
        if (user.data.role === 'TECHNICIEN') {
          setRedirectPath('/technician/dashboard');
        } else {
          setRedirectPath('/admin/dashboard');
        }
      }
    } catch (error) {
      console.error('Error checking role:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return <Navigate to={redirectPath} replace />;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <ToasterUI />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          
          {/* Role-based root redirect */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <RoleBasedRedirect />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes */}
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/machines"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <Machines />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/work-orders"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <WorkOrders />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/interventions"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <Interventions />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/planning"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <PlanningPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <Reports />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/archives"
            element={
              <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
                <Layout>
                  <Archives />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Technician Routes */}
          <Route
            path="/technician"
            element={
              <ProtectedRoute allowedRoles={['TECHNICIEN']}>
                <TechnicianLayout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<TechnicianDashboard />} />
            <Route path="work-orders" element={<TechnicianWorkOrders />} />
            <Route path="work-orders/:id" element={<TechnicianWorkOrderDetail />} />
            <Route path="interventions" element={<TechnicianInterventions />} />
            <Route path="machines" element={<TechnicianMachines />} />
            <Route path="machines/:id" element={<TechnicianMachineDetail />} />
            <Route path="documents" element={<TechnicianDocuments />} />
            <Route path="urgent-alert" element={<TechnicianUrgentAlert />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;