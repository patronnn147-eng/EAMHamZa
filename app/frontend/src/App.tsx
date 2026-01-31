import { useEffect, useState } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { Toaster as ToasterUI } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { client } from './lib/api';
import { DataSyncProvider } from './contexts/DataSyncContext';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/layout/Layout';
import TechnicianLayout from './components/layout/TechnicianLayout';
import Login from './modules/auth/Login';
import AuthCallback from './modules/shared/AuthCallback';
import Dashboard from './modules/shared/Dashboard';
import ChetopDashboard from './modules/chetop/ChetopDashboard';
import CheftechDashboard from './modules/cheftech/CheftechDashboard';
import Machines from './modules/shared/Machines';
import WorkOrders from './modules/shared/WorkOrders';
import Interventions from './modules/shared/Interventions';
import PlanningPage from './modules/shared/PlanningPage';
import Reports from './modules/shared/Reports';
import Archives from './modules/shared/Archives';
import TechnicianDashboard from './modules/technicien/TechnicianDashboard';
import TechnicianWorkOrders from './modules/technicien/TechnicianWorkOrders';
import TechnicianWorkOrderDetail from './modules/technicien/TechnicianWorkOrderDetail';
import TechnicianInterventions from './modules/technicien/TechnicianInterventions';
import TechnicianMachines from './modules/technicien/TechnicianMachines';
import TechnicianMachineDetail from './modules/technicien/TechnicianMachineDetail';
import TechnicianDocuments from './modules/technicien/TechnicianDocuments';
import TechnicianUrgentAlert from './modules/technicien/TechnicianUrgentAlert';
import NotFound from './modules/shared/NotFound';

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
        } else if (user.data.role === 'CHETOP') {
          setRedirectPath('/chetop/dashboard');
        } else if (user.data.role === 'CHEFTECH') {
          setRedirectPath('/cheftech/dashboard');
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
    <AuthProvider>
      <DataSyncProvider>
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
              {/* CHETOP Routes */}
              <Route
                path="/chetop/dashboard"
                element={
                  <ProtectedRoute allowedRoles={['CHETOP']}>
                    <Layout>
                      <ChetopDashboard />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              {/* CHEFTECH Routes */}
              <Route
                path="/cheftech/dashboard"
                element={
                  <ProtectedRoute allowedRoles={['CHEFTECH']}>
                    <Layout>
                      <CheftechDashboard />
                    </Layout>
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
      </DataSyncProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;