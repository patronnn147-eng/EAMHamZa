import { useAuth } from '@/contexts/AuthContext';

/**
 * Permission system for Phase 1: Preventive Planning Cycle
 * 
 * Implements all 4 permission approaches:
 * - A. Hide: Completely hide unauthorized elements
 * - B. Disable: Disable with tooltip
 * - C. Show + Message: Show action, display error on click  
 * - D. Hybrid: Disabled state + inline message in forms
 */

// User roles in the system
export type UserRole = 'ADMIN' | 'CHEFTECH' | 'CHETOP' | 'TECHNICIEN';

// Permission matrix for planning/work order actions
export const PERMISSIONS = {
  // Planning permissions
  'planning:create': ['ADMIN'],
  'planning:submit': ['CHEFTECH'],
  'planning:approve': ['ADMIN'],
  'planning:reject': ['ADMIN'],
  'planning:delete': ['ADMIN'],
  'planning:read': ['ADMIN', 'CHEFTECH', 'CHETOP', 'TECHNICIEN'],
  
  // Work order permissions
  'workorder:create': ['CHEFTECH', 'CHETOP', 'TECHNICIEN'],
  'workorder:validate': ['ADMIN', 'CHEFTECH', 'TECHNICIEN'],
  'workorder:validate-by-admin': ['ADMIN'], // CHETOP work requires admin validation
  'workorder:close': ['ADMIN'],
  'workorder:start': ['TECHNICIEN'],
  'workorder:complete': ['TECHNICIEN'],
  'workorder:delete': ['ADMIN'],
  
  // Intervention permissions
  'intervention:create': ['TECHNICIEN', 'CHETOP'],
  'intervention:validate': ['ADMIN', 'CHEFTECH'],
} as const;

export type Permission = keyof typeof PERMISSIONS;

/**
 * Hook to check if current user has a specific permission
 */
export const useHasPermission = (permission: Permission): boolean => {
  const { user } = useAuth();
  
  if (!user) return false;
  
  const allowedRoles = PERMISSIONS[permission];
  return allowedRoles.includes(user.role as UserRole);
};

/**
 * Hook to get the current user's role
 */
export const useUserRole = (): UserRole | null => {
  const { user } = useAuth();
  return (user?.role as UserRole) ?? null;
};

/**
 * Check if user has ANY of the given permissions
 */
export const useHasAnyPermission = (permissions: Permission[]): boolean => {
  return permissions.some(p => useHasPermission(p));
};

/**
 * Check if user has ALL of the given permissions  
 */
export const useHasAllPermissions = (permissions: Permission[]): boolean => {
  return permissions.every(p => useHasPermission(p));
};

// French permission messages
export const PERMISSION_MESSAGES = {
  default: "Vous n'avez pas la permission pour cette action",
  'planning:create': "Seul l'administrateur peut créer un planning",
  'planning:submit': "Seul le Chef Technique peut soumettre un planning",
  'planning:approve': "Seul l'administrateur peut approuver un planning",
  'planning:reject': "Seul l'administrateur peut rejeter un planning",
  'planning:delete': "Seul l'administrateur peut supprimer un planning",
  'workorder:create': "Vous n'avez pas la permission de créer un ordre de travail",
  'workorder:validate': "Vous n'avez pas la permission de valider un ordre de travail",
  'workorder:validate-by-admin': "Seul l'administrateur peut valider les ordres de travail créés par CHETOP",
  'workorder:close': "Seul l'administrateur peut clore un ordre de travail",
  'workorder:start': "Vous ne pouvez pas démarrer cet ordre de travail",
  'workorder:complete': "Vous ne pouvez pas compléter cet ordre de travail",
  'workorder:delete': "Seul l'administrateur peut supprimer un ordre de travail",
  'intervention:create': "Vous n'avez pas la permission de créer une intervention",
  'intervention:validate': "Vous n'avez pas la permission de valider une intervention",
};

export const getPermissionMessage = (permission: Permission): string => {
  return PERMISSION_MESSAGES[permission] || PERMISSION_MESSAGES.default;
};