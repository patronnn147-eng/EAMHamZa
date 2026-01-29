import { useAuth } from '@/contexts/AuthContext';

export type Permission = 
  | 'create_users'
  | 'read_users'
  | 'update_users'
  | 'delete_users'
  | 'create_machines'
  | 'read_machines'
  | 'update_machines'
  | 'delete_machines'
  | 'create_work_orders'
  | 'read_work_orders'
  | 'update_work_orders'
  | 'delete_work_orders'
  | 'create_interventions'
  | 'read_interventions'
  | 'update_interventions'
  | 'delete_interventions'
  | 'create_planning'
  | 'read_planning'
  | 'update_planning'
  | 'delete_planning'
  | 'read_reports'
  | 'create_archives'
  | 'read_archives'
  | 'update_archives'
  | 'delete_archives'
  | 'access_ai_hub';

interface RolePermissions {
  [key: string]: Permission[];
}

const ROLE_PERMISSIONS: RolePermissions = {
  ADMIN: [
    'create_users', 'read_users', 'update_users', 'delete_users',
    'create_machines', 'read_machines', 'update_machines', 'delete_machines',
    'create_work_orders', 'read_work_orders', 'update_work_orders', 'delete_work_orders',
    'create_interventions', 'read_interventions', 'update_interventions', 'delete_interventions',
    'create_planning', 'read_planning', 'update_planning', 'delete_planning',
    'read_reports',
    'create_archives', 'read_archives', 'update_archives', 'delete_archives',
    'access_ai_hub'
  ],
  CHEFTECH: [
    'read_users', // Can view technicians only
    'read_machines', 'update_machines', // Can update machine status
    'read_work_orders', 'update_work_orders', // Can view and assign technicians
    'read_interventions', // Can view all interventions
    'read_planning', // Read-only access
    'read_reports', // Technical reports only
    'read_archives' // Read-only access
  ],
  CHETOP: [
    'read_users', // Can view all users
    'read_machines', // View machine status
    'create_work_orders', 'read_work_orders', 'update_work_orders', // Can create and manage work orders
    'read_interventions', // View intervention reports
    'create_planning', 'read_planning', 'update_planning', // Full planning control
    'read_reports', // Operations reports
    'read_archives' // Read-only access
  ],
  TECHNICIEN: [
    'read_machines', 'update_machines', // Can update assigned machine status
    'read_work_orders', 'update_work_orders', // Can view and update assigned work orders
    'create_interventions', 'read_interventions', 'update_interventions', // Can create intervention reports
    'read_planning', // View own schedule only
    'read_reports' // Can view own intervention reports
  ]
};

export function usePermissions() {
  const { user } = useAuth();
  const userRole = user?.role;

  const hasPermission = (permission: Permission): boolean => {
    if (!userRole) return false;
    return ROLE_PERMISSIONS[userRole]?.includes(permission) || false;
  };

  const canCreate = (resource: string): boolean => {
    return hasPermission(`create_${resource}` as Permission);
  };

  const canRead = (resource: string): boolean => {
    return hasPermission(`read_${resource}` as Permission);
  };

  const canUpdate = (resource: string): boolean => {
    return hasPermission(`update_${resource}` as Permission);
  };

  const canDelete = (resource: string): boolean => {
    return hasPermission(`delete_${resource}` as Permission);
  };

  const getPermissionMessage = (action: string, resource: string): string => {
    const actionMap = {
      create: 'créer',
      read: 'voir',
      update: 'modifier',
      delete: 'supprimer'
    };
    
    const resourceMap = {
      users: 'des utilisateurs',
      machines: 'des machines',
      work_orders: 'des ordres de travail',
      interventions: 'des interventions',
      planning: 'du planning',
      reports: 'des rapports',
      archives: 'des archives'
    };

    return `Vous n'êtes pas autorisé à ${actionMap[action as keyof typeof actionMap] || action} ${resourceMap[resource as keyof typeof resourceMap] || resource} avec votre rôle (${userRole}).`;
  };

  return {
    hasPermission,
    canCreate,
    canRead,
    canUpdate,
    canDelete,
    getPermissionMessage,
    userRole
  };
}
