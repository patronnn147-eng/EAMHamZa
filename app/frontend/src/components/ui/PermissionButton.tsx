import React from 'react';
import { Button } from '@/components/ui/button';
import { 
  AlertDialog,
  AlertDialogAction,
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

interface PermissionButtonProps {
  children: React.ReactNode;
  permission: 'create' | 'read' | 'update' | 'delete';
  resource: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
}

export function PermissionButton({
  children,
  permission,
  resource,
  onClick,
  disabled = false,
  variant = 'default',
  size = 'default',
  className = ''
}: PermissionButtonProps) {
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

  const isDisabled = disabled || !hasPermission;
  const permissionMessage = getPermissionMessage(permission, resource);

  if (hasPermission) {
    return (
      <Button
        onClick={onClick}
        disabled={disabled}
        variant={variant}
        size={size}
        className={className}
      >
        {children}
      </Button>
    );
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          disabled={isDisabled}
          variant={variant === 'destructive' ? 'outline' : variant}
          size={size}
          className={`${className} opacity-60 cursor-not-allowed`}
          title={`Action non autorisée pour le rôle ${userRole}`}
        >
          <Lock className="w-4 h-4 mr-2" />
          {children}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Action non autorisée
          </AlertDialogTitle>
          <AlertDialogDescription className="text-left">
            <p className="mb-2">{permissionMessage}</p>
            <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
              <p className="text-sm font-medium text-amber-800 mb-1">Rôle actuel: {userRole}</p>
              <p className="text-xs text-amber-700">
                Pour effectuer cette action, vous devez avoir un rôle avec les permissions appropriées.
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
