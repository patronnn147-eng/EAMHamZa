import React from 'react';
import { Permission, useHasPermission, getPermissionMessage } from '@/hooks/usePermission';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

/**
 * Approach A: Hide - Completely hide unauthorized elements
 * Usage: <HiddenElement permission="planning:approve"><Button>Approve</Button></HiddenElement>
 */
interface HiddenElementProps {
  permission: Permission;
  children: React.ReactNode;
}

export const HiddenElement: React.FC<HiddenElementProps> = ({ permission, children }) => {
  const hasPermission = useHasPermission(permission);
  
  if (!hasPermission) return null;
  
  return <>{children}</>;
};

/**
 * Approach B: Disable - Disable with tooltip on hover
 * Usage: <DisabledButton permission="planning:approve">Approve</DisabledButton>
 */
interface DisabledButtonProps {
  permission: Permission;
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

export const DisabledButton: React.FC<DisabledButtonProps> = ({ 
  permission, 
  children, 
  onClick,
  disabled = false,
  className = ''
}) => {
  const hasPermission = useHasPermission(permission);
  const isDisabled = disabled || !hasPermission;
  const message = getPermissionMessage(permission);
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild disabled={!isDisabled}>
          <button
            onClick={onClick}
            disabled={isDisabled}
            className={className}
            style={{ 
              opacity: isDisabled ? 0.5 : 1, 
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              ...(isDisabled ? { pointerEvents: 'none' } : {})
            }}
          >
            {children}
          </button>
        </TooltipTrigger>
        {isDisabled && (
          <TooltipContent>
            <p>{message}</p>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
};

/**
 * Approach C: Show + Message - Show action, display error on click (with toast)
 * Usage: <PermissionButton permission="planning:approve" onClick={handleApprove}>Approve</PermissionButton>
 */
import { toast } from 'sonner';

interface PermissionButtonProps {
  permission: Permission;
  children: React.ReactNode;
  onClick: () => void;
  className?: string;
}

export const PermissionButton: React.FC<PermissionButtonProps> = ({
  permission,
  children,
  onClick,
  className = ''
}) => {
  const hasPermission = useHasPermission(permission);
  
  const handleClick = () => {
    if (!hasPermission) {
      toast.error(getPermissionMessage(permission));
      return;
    }
    onClick();
  };
  
  return (
    <button onClick={handleClick} className={className}>
      {children}
    </button>
  );
};

/**
 * Approach D: Hybrid - Disabled state + inline message in forms
 * Usage: <HybridFormField permission="planning:approve" label="Statut" />
 */
interface HybridFormFieldProps {
  permission: Permission;
  children: React.ReactNode;
  label?: string;
}

export const HybridFormField: React.FC<HybridFormFieldProps> = ({
  permission,
  children,
  label
}) => {
  const hasPermission = useHasPermission(permission);
  
  if (hasPermission) {
    return <>{children}</>;
  }
  
  return (
    <div className="space-y-2">
      {label && <label className="text-sm font-medium">{label}</label>}
      <div className="p-3 bg-muted/50 rounded-md text-muted-foreground text-sm">
        {getPermissionMessage(permission)}
      </div>
    </div>
  );
};

/**
 * PermissionGuard - Conditionally render children based on permission
 */
interface PermissionGuardProps {
  permission: Permission;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permission,
  fallback = null,
  children
}) => {
  const hasPermission = useHasPermission(permission);
  
  if (!hasPermission) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
};

/**
 * PermissionInlineMessage - Show inline permission message
 */
interface PermissionInlineMessageProps {
  permission: Permission;
  className?: string;
}

export const PermissionInlineMessage: React.FC<PermissionInlineMessageProps> = ({
  permission,
  className = ''
}) => {
  const hasPermission = useHasPermission(permission);
  
  if (hasPermission) return null;
  
  return (
    <p className={`text-sm text-muted-foreground ${className}`}>
      {getPermissionMessage(permission)}
    </p>
  );
};