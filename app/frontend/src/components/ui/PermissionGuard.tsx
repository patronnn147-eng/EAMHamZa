import React from 'react';
import { 
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Lock, AlertTriangle } from 'lucide-react';
import { usePermissions } from '@/hooks/usePermissions';

interface PermissionGuardProps {
  children: React.ReactNode;
  permission: 'create' | 'read' | 'update' | 'delete';
  resource: string;
  fallback?: React.ReactNode;
  showWarning?: boolean;
}

export function PermissionGuard({
  children,
  permission,
  resource,
  fallback,
  showWarning = true
}: PermissionGuardProps) {
  const { canCreate, canRead, canUpdate, canDelete, getPermissionMessage, userRole } = usePermissions();

  const hasPermission = React.useMemo(() => {
    switch (permission) {
      case 'create':
        return canCreate(resource);
      case 'read':
        return canRead(resource);
      case 'update':
        return canUpdate(resource);
      case 'delete':
        return canDelete(resource);
      default:
        return false;
    }
  }, [permission, resource, canCreate, canRead, canUpdate, canDelete]);

  if (hasPermission) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  if (!showWarning) {
    return null;
  }

  const permissionMessage = getPermissionMessage(permission, resource);

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <div className="relative inline-block">
          <div className="opacity-50 pointer-events-none">
            {children}
          </div>
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-80 rounded-md">
            <Lock className="w-6 h-6 text-gray-500" />
          </div>
        </div>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Accès non autorisé
          </AlertDialogTitle>
          <AlertDialogDescription className="text-left">
            <p className="mb-2">{permissionMessage}</p>
            <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
              <p className="text-sm font-medium text-amber-800 mb-1">Rôle actuel: {userRole}</p>
              <p className="text-xs text-amber-700">
                Pour accéder à cette fonctionnalité, vous devez avoir un rôle avec les permissions appropriées.
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Compris</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
