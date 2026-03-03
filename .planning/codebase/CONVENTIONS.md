# Coding Conventions

**Analysis Date:** 2026-03-03

## Naming Patterns

### Files

**TypeScript/React:**
- Components: PascalCase - `WorkOrderFormDialog.tsx`, `LoadingSpinner.tsx`
- Hooks: camelCase with `use` prefix - `useWorkOrders.ts`, `useMachines.ts`
- Utilities: camelCase - `utils.ts`, `date.ts`, `api.ts`
- Types: PascalCase - `types.ts`
- Context: PascalCase with `Context` suffix - `AuthContext.tsx`, `DataSyncContext.tsx`

**Python (Backend):**
- Snake_case for all files - `auth.py`, `ordres_travail.py`, `ml_predictive.py`
- Modules: lowercase - `services/`, `routers/`, `models/`

### Functions

**TypeScript:**
- Hooks: camelCase starting with `use` - `useWorkOrders()`, `useMachines()`
- Event handlers: camelCase starting with `handle` - `handleSubmit()`, `handleDelete()`, `handleOpenDialog()`
- API/data fetching: camelCase - `fetchData()`, `getData()`
- Utility functions: camelCase - `toDateInputValue()`, `cn()`

**Python:**
- Async functions: snake_case - `initialize_admin_user()`, `get_password_hash()`
- Service methods: snake_case - `create_work_order()`, `get_machines()`

### Variables

**TypeScript:**
- State: camelCase - `workOrders`, `filteredWorkOrders`, `searchTerm`
- Props: camelCase - `options: UseWorkOrdersOptions`
- Constants: UPPER_SNAKE_CASE for env vars - `API_BASE_URL`
- Types/Interfaces: PascalCase - `Machine`, `OrdreTravail`, `Planning`

**Python:**
- Variables: snake_case - `admin_id`, `admin_user_email`
- Constants: UPPER_SNAKE_CASE
- Models: PascalCase - `Utilisateurs`, `UserRole`

## Code Style

### Formatting

**TypeScript:**
- Tool: ESLint with TypeScript ESLint plugin
- Config: `eslint.config.js` - uses `@eslint/js`, `typescript-eslint`, `react-hooks`, `react-refresh`
- Key rules:
  - `react-hooks/rules-of-hooks`: enforced
  - `react-refresh/only-export-components`: warn
  - `@typescript-eslint/no-unused-vars`: off
- Run: `npm run lint`

**Python:**
- Tool: Not explicitly configured, follows PEP 8 conventions
- Import organization: standard library → third-party → local

### Styling

**CSS Framework:** Tailwind CSS v3.4.11
- Config: `tailwind.config.ts`
- Prefix: none
- Uses CSS custom properties via `hsl(var(--*))` pattern
- Component variants via `class-variance-authority` (cva)

**Class Merging:**
- Utility: `tailwind-merge` + `clsx` via `cn()` function in `src/lib/utils.ts`

## Import Organization

### TypeScript/React

```typescript
// 1. React/Next imports
import { useEffect, useMemo, useState } from 'react';

// 2. External libraries
import { client } from '@/lib/api';
import { toDateInputValue } from '@/lib/date';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';

// 3. Types
import type { Machine, OrdreTravail } from '@/lib/types';

// 4. Local components/hooks
// (relative imports for co-located modules)
```

### Path Aliases

- `@/*` maps to `src/*` - configured in `tsconfig.json`

### Python

```python
# 1. Standard library
import logging
import time
from datetime import datetime, timezone

# 2. Third-party
from fastapi import FastAPI
from sqlalchemy import select

# 3. Local imports
from core.config import settings
from models.utilisateurs import Utilisateurs
from services.database import db_manager
```

## Error Handling

### TypeScript/React

**Pattern - try/catch with typed errors:**
```typescript
try {
  // API call
} catch (error: unknown) {
  const detail =
    (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail ||
    (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
    (error as { message?: string }).message;

  toast({
    title: 'Error',
    description: detail || 'Failed to save work order',
    variant: 'destructive',
  });
}
```

**Pattern - null checks:**
```typescript
const workOrdersList = workOrdersResponse.data.items || [];
const machinesList = machinesResponse.data.items || [];
```

**Pattern - Optional chaining:**
```typescript
planningId = rel?.planning_id ?? null;
```

### Python/FastAPI

**Pattern - HTTPException with status codes:**
```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Machine non trouvée")
raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle TECHNICIEN requis.")
raise HTTPException(status_code=400, detail="Invalid statut. Allowed: {sorted(valid_statuses)}")
```

**Pattern - Try/except with re-raise:**
```python
try:
    result = await db.execute(select(Utilisateurs).where(...))
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

## Logging

### Python

**Framework:** Python `logging` module

**Setup:** In `app/backend/main.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
```

**Usage:**
```python
logger = logging.getLogger(__name__)
logger.info("=== Application startup initiated ===")
logger.debug(f"Admin user {admin_id} already exists")
logger.warning(f"RabbitMQ connection failed: {e}")
```

### TypeScript

**Framework:** Console logging (`console.log`, `console.error`, `console.debug`)

**Note:** The codebase contains extensive debug logging in API code:
```typescript
console.log('🔧 DEBUG: Adding auth header, token exists:', !!token);
console.log('🔧 DEBUG: apiCall.invoke called with:', config);
```

## Comments

### TypeScript

**JSDoc/TSDoc:** Not heavily used in codebase

**Inline comments:** Used sparingly for complex logic
```typescript
// Ensure the model file exists for the test environment
MODEL_PATH = os.path.join(...)
```

### Python

**Docstrings:** Used for main functions
```python
async def initialize_admin_user():
    """Initialize admin user if not exists"""
    ...
```

**Inline comments:** Used for complex operations
```python
# Check if admin user already exists (by email)
result = await db.execute(select(Utilisateurs).where(...))
```

## Function Design

### Size Guidelines

**TypeScript:**
- Custom hooks typically large (300-500 lines) - see `useWorkOrders.ts` (457 lines)
- Components generally smaller, using composition
- Single-responsibility within hooks (separate fetch, handlers, state)

**Python:**
- Router handlers typically 50-150 lines
- Service functions 20-80 lines
- Separation of concerns: routes → services → models

### Parameters

**TypeScript:**
- Options object pattern for hooks:
```typescript
type UseWorkOrdersOptions = {
  attachments: File[];
  clearAttachments: () => void;
  userRole?: string;
};

export const useWorkOrders = (options: UseWorkOrdersOptions) => { ... }
```

**Python:**
- Typed parameters with defaults:
```python
async def get_machines(db: AsyncSession, skip: int = 0, limit: int = 100):
```

### Return Values

**TypeScript:**
- Custom hooks return object with all state and handlers
```typescript
return {
  workOrders,
  machines,
  filteredWorkOrders,
  loading,
  handleOpenDialog,
  handleSubmit,
  handleDelete,
  refresh: fetchData,
};
```

**Python:**
- FastAPI handlers return Pydantic models or dicts
- Services return database models

## Module Design

### TypeScript Exports

**Pattern - Named exports:**
```typescript
export const useWorkOrders = (options: UseWorkOrdersOptions) => { ... }
export function cn(...inputs: ClassValue[]) { ... }
export { Button, buttonVariants };
```

**Pattern - Index files for barrel exports:**
```typescript
// src/modules/shared/work-orders/index.ts
export * from './hooks/useWorkOrders';
export * from './components';
export * from './utils';
```

### Python Exports

**Pattern - Module-level router:**
```python
# routers/ordres.py
router = APIRouter()

@router.get("/ordres")
async def get_ordres():
    ...
```

## React Component Patterns

### Component Structure

**Pattern - Compound components with variants:**
```typescript
// Using class-variance-authority (cva)
const buttonVariants = cva(
  "inline-flex items-center justify-center...",
  {
    variants: {
      variant: {
        default: "bg-primary...",
        destructive: "bg-destructive...",
        outline: "border border-input...",
      },
      size: { ... }
    },
    defaultVariants: { ... }
  }
);
```

**Pattern - React.forwardRef for ref forwarding:**
```typescript
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";
```

### State Management

**Pattern - Zustand for global state:**
- Used in project (`zustand` v4.5.0 in dependencies)

**Pattern - React Query for server state:**
- Used via `@tanstack/react-query` v5.56.2

**Pattern - Context for app state:**
- `AuthContext.tsx` - authentication state
- `DataSyncContext.tsx` - real-time data synchronization

---

*Convention analysis: 2026-03-03*
