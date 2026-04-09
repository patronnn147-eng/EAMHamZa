import { Routes, Route } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import TechnicianLayout from '@/components/layout/TechnicianLayout';
import Login from '@/modules/auth/Login';
import AuthCallback from '@/modules/shared/AuthCallback';
import CheftechDashboard from '@/modules/cheftech/CheftechDashboard';
import AdminMachines from '@/modules/admin/AdminMachines';
import ChefTechMachines from '@/modules/cheftech/ChefTechMachines';
import MachineDetailPage from '@/modules/shared/MachineDetailPage';
import ChetopMachines from '@/modules/chetop/ChetopMachines';
import WorkOrders from '@/modules/shared/WorkOrders';
import Interventions from '@/modules/shared/Interventions';
import CheftechInterventionsPage from '@/modules/cheftech/CheftechInterventionsPage';
import PlanningPage from '@/modules/shared/PlanningPage';
import PlanningDetailPage from '@/modules/shared/PlanningDetailPage';
import WorkOrderDetailPage from '@/modules/shared/WorkOrderDetailPage';
import PlanningCalendarView from '@/modules/shared/PlanningCalendarView';
import PlanningManagement from '@/modules/admin/PlanningManagement';
import UserApprovalManagement from '@/modules/admin/UserApprovalManagement';
import UserManagement from '@/modules/admin/UserManagement';
import AdminCompletedWorkOrders from '@/modules/admin/AdminCompletedWorkOrders';
import SystemAnalytics from '@/modules/admin/SystemAnalytics';
import MLDashboard from '@/modules/admin/ml/MLDashboard';
import MLFleetDashboard from '@/modules/shared/MLFleetDashboard';
import Reports from '@/modules/shared/Reports';
import Archives from '@/modules/shared/Archives';
import TechnicianDashboard from '@/modules/technicien/TechnicianDashboard';
import TechnicianWorkOrders from '@/modules/technicien/TechnicianWorkOrders';
import TechnicianWorkOrderDetail from '@/modules/technicien/TechnicianWorkOrderDetail';
import TechnicianInterventions from '@/modules/technicien/TechnicianInterventions';
import TechnicianMachines from '@/modules/technicien/TechnicianMachines';
import TechnicianPlanning from '@/modules/technicien/TechnicianPlanning';
import TechnicianDocuments from '@/modules/technicien/TechnicianDocuments';
import ChefTechUrgentAlert from '@/modules/cheftech/ChefTechUrgentAlert';
import NotFound from '@/modules/shared/NotFound';
import { ProtectedRoute } from './ProtectedRoute';
import { RoleBasedRedirect } from './RoleBasedRedirect';
import { SectionRedirect } from './SectionRedirect';
import ChetopDashboard from '@/modules/chetop/ChetopDashboard';
import PDCAPage from '@/modules/shared/PDCAPage';
import InventoryPage from '@/modules/shared/InventoryPage';
import AdminWorkOrdersList from '@/modules/admin/AdminWorkOrdersList';
import AdminWorkOrdersTable from '@/modules/admin/AdminWorkOrdersTable';
import AdminItvApprovals from '@/modules/admin/AdminItvApprovals';
import ChefOpItvRequests from '@/modules/chetop/ChefOpItvRequests';
import ChefOpWorkOrders from '@/modules/chetop/ChefOpWorkOrders';
import ChefTechWorkOrdersTable from '@/modules/cheftech/ChefTechWorkOrdersTable';

export function AppRoutes() {
  return (
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
              <CheftechDashboard role="CHEFTECH" />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="/cheftech/urgent-alert" element={<ChefTechUrgentAlert />} />
      {/* Admin Routes */}
      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <CheftechDashboard role="ADMIN" />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Legacy shared URLs -> role-specific redirects */}
      <Route
        path="/machines"
        element={
          <ProtectedRoute>
            <SectionRedirect section="machines" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/work-orders"
        element={
          <ProtectedRoute>
            <SectionRedirect section="work-orders" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/interventions"
        element={
          <ProtectedRoute>
            <SectionRedirect section="interventions" />
          </ProtectedRoute>
        }
      />
      {/* Admin Machines Route */}
      <Route
        path="/admin/machines"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <AdminMachines />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* ChefTech Machines Route */}
      <Route
        path="/cheftech/machines"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <ChefTechMachines />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Shared Machine Detail Route */}
      <Route
        path="/machines/:id"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
            <Layout>
              <MachineDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Shared Work Order Detail Route */}
      <Route
        path="/work-orders/:id"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
            <Layout>
              <WorkOrderDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Chetop Machines Route */}
      <Route
        path="/chetop/machines"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <ChetopMachines />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/work-orders"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <AdminWorkOrdersList />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/work-orders-management"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <AdminWorkOrdersTable />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/completed-work-orders"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <AdminCompletedWorkOrders />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/itv-approvals"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <AdminItvApprovals />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/analytics"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <SystemAnalytics />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/work-orders-table"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <ChefTechWorkOrdersTable />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/work-orders"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <WorkOrders />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/itv-requests"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <ChefOpItvRequests />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/work-orders"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <ChefOpWorkOrders />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/work-orders/:id"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <WorkOrderDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Interventions - role-specific routes (temporary reuse of shared component) */}
      <Route
        path="/admin/interventions"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <Interventions />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/interventions"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <CheftechInterventionsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/interventions"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <Interventions />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Admin Planning Management (Full CRUD) */}
      <Route
        path="/admin/planning"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <PlanningManagement />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/planning/:id"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <PlanningDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/planning/:id/calendar"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <PlanningCalendarView />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Admin User Approval Management */}
      <Route
        path="/admin/user-approvals"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <UserApprovalManagement />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Admin User Management */}
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <UserManagement />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Admin ML Dashboard Route */}
      <Route
        path="/admin/ml"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <MLDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* ML Fleet Dashboard Route (ADMIN, CHEFTECH, CHETOP) */}
      <Route
        path="/ml-dashboard"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHEFTECH', 'CHETOP']}>
            <Layout>
              <MLFleetDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* ChefTech Planning (Read-only) */}
      <Route
        path="/cheftech/planning"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <PlanningPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/planning/:id"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <PlanningDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/planning/:id/calendar"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <PlanningCalendarView />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Chetop Planning (Read-only) */}
      <Route
        path="/chetop/planning"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <PlanningPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/planning/:id"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <PlanningDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/planning/:id/calendar"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <PlanningCalendarView />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Shared Planning Detail Page */}
      <Route
        path="/planning/:id"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH', 'TECHNICIEN']}>
            <Layout>
              <PlanningDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/planning/:id/calendar"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH', 'TECHNICIEN']}>
            <Layout>
              <PlanningCalendarView />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/pdca"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHETOP', 'CHEFTECH']}>
            <Layout>
              <PDCAPage />
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
      {/* Inventory Routes */}
      <Route
        path="/inventory"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHEFTECH', 'CHETOP', 'TECHNICIEN']}>
            <Layout>
              <InventoryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/inventory"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <Layout>
              <InventoryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cheftech/inventory"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <InventoryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chetop/inventory"
        element={
          <ProtectedRoute allowedRoles={['CHETOP']}>
            <Layout>
              <InventoryPage />
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
        <Route path="work-orders/:id" element={<WorkOrderDetailPage />} />
        <Route path="interventions" element={<TechnicianInterventions />} />
        <Route path="machines" element={<TechnicianMachines />} />
        <Route path="machines/:id" element={<MachineDetailPage />} />
        <Route path="planning" element={<TechnicianPlanning />} />
        <Route path="planning/:id" element={<PlanningDetailPage />} />
        <Route path="planning/:id/calendar" element={<PlanningCalendarView />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="documents" element={<TechnicianDocuments />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
