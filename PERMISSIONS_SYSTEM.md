# Role-Based Access Control (RBAC) System

## Overview

This system implements a comprehensive role-based access control (RBAC) with user-friendly permission restrictions. When users attempt actions they're not authorized for, they see disabled buttons and clear warning popups explaining the restrictions.

## 🎯 Key Features

- **Role-Aware UI**: Buttons automatically disable based on user permissions
- **Clear Feedback**: Warning popups explain exactly what actions are restricted
- **Visual Indicators**: Locked icons and disabled states provide immediate feedback
- **Fallback Content**: Alternative content shown when entire sections are restricted
- **TypeScript Safety**: Full type safety for permission checking

## 🏗️ Architecture

### 1. Permission Hook (`usePermissions.ts`)

Central hook that provides:
- `hasPermission(permission)` - Check specific permission
- `canCreate(resource)`, `canRead(resource)`, `canUpdate(resource)`, `canDelete(resource)` - CRUD helpers
- `getPermissionMessage(action, resource)` - User-friendly error messages
- `userRole` - Current user's role

### 2. PermissionButton Component

A drop-in replacement for Button that:
- Automatically disables if user lacks permission
- Shows warning popup on click attempt
- Displays lock icon for restricted actions
- Provides clear role-based messaging

```tsx
<PermissionButton
  permission="update"
  resource="machines"
  onClick={() => updateMachine(id)}
>
  Update Machine
</PermissionButton>
```

### 3. PermissionGuard Component

Wraps entire sections to:
- Hide/show content based on permissions
- Provide fallback content for restricted areas
- Show overlay with lock icon for visual feedback

```tsx
<PermissionGuard permission="create" resource="users" fallback={
  <div>You cannot create users</div>
}>
  <UserCreationForm />
</PermissionGuard>
```

## 🎭 Roles and Permissions

### ADMIN
- ✅ **Full Access**: All CRUD operations on all resources
- ✅ **System Management**: User management, archives, AI hub
- ✅ **No Restrictions**: Complete system control

### CHEFTECH (Chef Technique)
- ✅ **Read**: View technicians, machines, interventions, work orders
- ✅ **Update**: Machine status only
- ❌ **Create/Delete**: Cannot create or delete resources
- ❌ **User Management**: Cannot manage users

### CHETOP (Chef des Opérations)
- ✅ **Read**: View all resources except sensitive data
- ✅ **Create**: Work orders and planning
- ✅ **Update**: Work orders and planning
- ❌ **Delete**: Cannot delete resources
- ❌ **Technical Operations**: Cannot modify machines or interventions

### TECHNICIEN
- ✅ **Read**: View assigned work orders, machines, interventions
- ✅ **Update**: Update assigned work order status, machine status
- ✅ **Create**: Create intervention reports
- ❌ **Global Access**: Cannot see other technicians' data
- ❌ **Management**: No user or resource management

## 📋 Permission Matrix

| Resource | Action | ADMIN | CHEFTECH | CHETOP | TECHNICIEN |
|----------|--------|-------|----------|--------|------------|
| **Users** | Create | ✅ | ❌ | ❌ | ❌ |
| | Read | ✅ | ✅ (tech only) | ✅ | ❌ |
| | Update | ✅ | ❌ | ❌ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ |
| **Machines** | Create | ✅ | ❌ | ❌ | ❌ |
| | Read | ✅ | ✅ | ✅ | ✅ (assigned) |
| | Update | ✅ | ✅ (status) | ❌ | ✅ (assigned) |
| | Delete | ✅ | ❌ | ❌ | ❌ |
| **Work Orders** | Create | ✅ | ❌ | ✅ | ❌ |
| | Read | ✅ | ✅ | ✅ | ✅ (assigned) |
| | Update | ✅ | ✅ (assign) | ✅ | ✅ (assigned) |
| | Delete | ✅ | ❌ | ❌ | ❌ |
| **Interventions** | Create | ✅ | ❌ | ❌ | ✅ |
| | Read | ✅ | ✅ | ✅ | ✅ (own) |
| | Update | ✅ | ❌ | ❌ | ✅ (own) |
| | Delete | ✅ | ❌ | ❌ | ❌ |
| **Planning** | Create | ✅ | ❌ | ✅ | ❌ |
| | Read | ✅ | ✅ | ✅ | ✅ (own) |
| | Update | ✅ | ❌ | ✅ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ |
| **Reports** | Read | ✅ | ✅ (tech) | ✅ (ops) | ✅ (own) |
| **Archives** | Create | ✅ | ❌ | ❌ | ❌ |
| | Read | ✅ | ✅ | ✅ | ❌ |
| | Update | ✅ | ❌ | ❌ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ |

## 🚀 Usage Examples

### Basic Permission Button
```tsx
import { PermissionButton } from '@/components/ui/PermissionButton';

// This button will be disabled for non-ADMIN users
<PermissionButton permission="delete" resource="users">
  Delete User
</PermissionButton>
```

### Section Protection
```tsx
import { PermissionGuard } from '@/components/ui/PermissionGuard';

// Entire section hidden for non-authorized users
<PermissionGuard permission="create" resource="machines" fallback={
  <div className="text-gray-500">Machine creation not available</div>
}>
  <MachineCreationForm />
</PermissionGuard>
```

### Custom Permission Checking
```tsx
import { usePermissions } from '@/hooks/usePermissions';

function Component() {
  const { canUpdate, userRole } = usePermissions();
  
  if (!canUpdate('machines')) {
    return <div>Cannot update machines</div>;
  }
  
  return <MachineUpdateForm />;
}
```

## 🎨 User Experience

### When Permission is **GRANTED**:
- Normal button appearance and functionality
- Action executes as expected
- No visual indication of restrictions

### When Permission is **DENIED**:
- **Button appears disabled** with opacity and lock icon
- **Hover tooltip** shows "Action non autorisée pour le rôle [ROLE]"
- **Click triggers warning popup** with:
  - Clear message: "Vous n'êtes pas autorisé à [action] [resource] avec votre rôle ([ROLE])."
  - Current role display
  - Explanation of permission requirements
- **Fallback content** can be provided for entire sections

## 🔧 Implementation Details

### Permission Types
```typescript
type Permission = 
  | 'create_users'
  | 'read_users'
  | 'update_users'
  | 'delete_users'
  | 'create_machines'
  | 'read_machines'
  | 'update_machines'
  | 'delete_machines'
  // ... etc for all resources
```

### Role Configuration
```typescript
const ROLE_PERMISSIONS = {
  ADMIN: ['all_permissions'],
  CHEFTECH: ['read_users', 'read_machines', 'update_machines', ...],
  CHETOP: ['read_users', 'create_work_orders', 'update_work_orders', ...],
  TECHNICIEN: ['read_machines', 'update_machines', 'create_interventions', ...]
};
```

### Backend Integration
The frontend permissions mirror the backend role-based access control:
```python
@router.get("/cheftech/dashboard")
async def get_dashboard_stats(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    # Backend enforces same permissions
```

## 🔄 Extending the System

### Adding New Resources
1. Add permission types to `Permission` union
2. Update `ROLE_PERMISSIONS` matrix
3. Add backend route protection
4. Update frontend components

### Adding New Roles
1. Add role to `UserRole` enum
2. Define permissions in `ROLE_PERMISSIONS`
3. Update backend verification functions
4. Add frontend role checks

## 🎯 Best Practices

1. **Always use PermissionButton** for user actions
2. **Wrap sensitive sections** with PermissionGuard
3. **Provide meaningful fallbacks** for restricted content
4. **Test with all roles** to ensure proper restrictions
5. **Keep permission messages** user-friendly and clear
6. **Use consistent naming** for resources and actions

## 🚨 Security Notes

- Frontend restrictions are for UX only
- Backend enforces all permissions independently
- Never trust frontend permission checks
- Always validate permissions on the server side
- Use JWT tokens with role claims for authentication
