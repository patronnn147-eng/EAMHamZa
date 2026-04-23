# Audit Log Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the `/audit-log` page with the "Orchestrated Void" aesthetic (glass panels, Manrope/Inter/Space Grotesk typography, electric cyan accents) and enforce CHEFTECH scope restriction server-side.

**Architecture:** Backend-first approach: (1) Add CHEFTECH scope filtering and user_search param to audit service/routes, (2) Update frontend styling tokens (fonts, colors, glass effects), (3) Rewrite AuditLogViewer component with the new design while reusing existing API calls. Frontend role-based UI is cosmetic only—server enforces all restrictions.

**Tech Stack:** Python/FastAPI, SQLAlchemy, React 18, TypeScript, Tailwind CSS, shadcn/ui, Material Symbols Outlined, Google Fonts (Manrope/Inter/Space Grotesk)

---

## Files to Modify

### Backend (Python / FastAPI)
- `app/backend/services/audit.py` — Add `user_search` param, ensure CHEFTECH scope filter applies
- `app/backend/modules/shared/routes/audit.py` — Pass `current_user.role` to service, add `user_search` query param, allow CHEFTECH on `/export`

### Frontend (React / TypeScript / Tailwind)
- `app/frontend/index.html` — Add Google Fonts links
- `app/frontend/tailwind.config.ts` — Extend colors and fontFamily
- `app/frontend/src/index.css` — Add glass-panel utilities and effects
- `app/frontend/src/modules/shared/AuditLogViewer.tsx` — Complete rewrite with new design
- `app/frontend/src/contexts/AuthContext.tsx` — Verify user role is exposed (read-only check)

---

## Task 1: Backend — Add user_search Parameter to Audit Service

**Files:**
- Modify: `app/backend/services/audit.py:218-276`
- Test: Manual API testing via curl

- [ ] **Step 1: Verify user_search parameter exists in get_audit_log signature**

The `user_search` parameter already exists at line 232. Verify the implementation at lines 260-264:

```python
if user_search:
    # SQLite-compatible case-insensitive substring match
    pattern = f"%{user_search.lower()}%"
    query = query.where(func.lower(AuditLog.user_name).like(pattern))
    count_query = count_query.where(func.lower(AuditLog.user_name).like(pattern))
```

- [ ] **Step 2: Test user_search functionality manually**

Run the backend server, then test:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "http://localhost:8000/api/v1/audit/log?user_search=Admin" | jq '.items[].user_name'
```

Expected: Returns only entries where user_name contains "Admin" (case-insensitive)

- [ ] **Step 3: Commit the verification**

```bash
git add app/backend/services/audit.py
git commit -m "feat: verify user_search param exists in audit service"
```

---

## Task 2: Backend — Ensure CHEFTECH Scope Filter Applies Correctly

**Files:**
- Modify: `app/backend/services/audit.py:200-215` (verify `_apply_cheftech_scope` method)
- Test: Manual API testing with CHEFTECH token

- [ ] **Step 1: Verify _apply_cheftech_scope method exists and is correct**

The method already exists at lines 200-215. Verify it filters correctly:

```python
def _apply_cheftech_scope(self, query, count_query):
    """Restrict queries to CHEFTECH-visible rows: work_order/intervention entities
    OR actions performed by TECHNICIEN users."""
    from sqlalchemy import select, or_
    from models.utilisateurs import Utilisateurs, UserRole

    technician_ids_subq = select(Utilisateurs.id).where(
        Utilisateurs.role == UserRole.TECHNICIEN
    )
    scope_clause = or_(
        AuditLog.entity_type.in_([AuditEntityType.WORK_ORDER,
                                   AuditEntityType.INTERVENTION]),
        AuditLog.user_id.in_(technician_ids_subq),
    )
    return query.where(scope_clause), count_query.where(scope_clause)
```

- [ ] **Step 2: Verify CHEFTECH filter is applied in get_audit_log**

Check lines 266-268:

```python
if user_role == UserRole.CHEFTECH:
    query, count_query = self._apply_cheftech_scope(query, count_query)
```

- [ ] **Step 3: Test CHEFTECH scope filter manually**

```bash
# As CHEFTECH — should return ONLY work_order/intervention entries or TECHNICIEN-authored
curl -H "Authorization: Bearer $CHEFTECH_TOKEN" \
     "http://localhost:8000/api/v1/audit/log?limit=50" | jq '.items[].entity_type' | sort -u
```

Expected: Only `["intervention", "work_order"]` plus any actions where user is TECHNICIEN

- [ ] **Step 4: Commit the verification**

```bash
git add app/backend/services/audit.py
git commit -m "feat: verify CHEFTECH scope filter in audit service"
```

---

## Task 3: Backend — Update Audit Routes to Pass user_role

**Files:**
- Modify: `app/backend/modules/shared/routes/audit.py:45-98`
- Test: Manual API testing

- [ ] **Step 1: Update get_audit_log route to pass user_role**

Modify the route handler at lines 45-98:

```python
@router.get("/log", response_model=dict)
async def get_audit_log(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
    user_search: Optional[str] = Query(None, description="Search by username"),  # ADD THIS
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get audit log entries with filters"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(status_code=403, detail="Only admin can view audit logs")
    
    service = AuditService(db)
    result = await service.get_audit_log(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action_type=action_type,
        from_date=from_date,
        to_date=to_date,
        user_search=user_search,  # ADD THIS
        user_role=current_user.role,  # ADD THIS
        skip=skip,
        limit=limit,
    )
    # ... rest of the function unchanged
```

- [ ] **Step 2: Update get_audit_stats route to pass user_role**

Modify the route at lines 132-146:

```python
@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get audit log statistics"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(status_code=403, detail="Only admin can view audit stats")
    
    service = AuditService(db)
    stats = await service.get_audit_stats(entity_type, entity_id)
    return stats
```

Note: Stats endpoint doesn't need user_role passed since it's filtered by entity_type/entity_id only. The CHEFTECH scope is applied at the log level.

- [ ] **Step 3: Update export route to allow CHEFTECH**

Modify the route at lines 148-181:

```python
@router.get("/export")
async def export_audit_log(
    entity_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    user_search: Optional[str] = Query(None, description="Search by username"),  # ADD THIS
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Export audit log to CSV"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:  # CHANGE THIS
        raise HTTPException(status_code=403, detail="Only admin can export audit logs")
    
    service = AuditService(db)
    result = await service.get_audit_log(
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
        user_search=user_search,  # ADD THIS
        user_role=current_user.role,  # ADD THIS
        skip=0,
        limit=10000,
    )
    # ... rest of function unchanged
```

- [ ] **Step 4: Test the updated routes**

```bash
# Test user_search
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "http://localhost:8000/api/v1/audit/log?user_search=Admin" | jq '.items | length'

# Test CHEFTECH export access
curl -H "Authorization: Bearer $CHEFTECH_TOKEN" \
     "http://localhost:8000/api/v1/audit/export" | jq '.count'
```

- [ ] **Step 5: Commit the changes**

```bash
git add app/backend/modules/shared/routes/audit.py
git commit -m "feat: pass user_role to audit service, allow CHEFTECH export"
```

---

## Task 4: Frontend — Add Google Fonts to index.html

**Files:**
- Modify: `app/frontend/index.html:1-23`

- [ ] **Step 1: Add font links to the head section**

Modify `app/frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="https://public-frontend-cos.metadl.com/mgx/img/favicon_atoms.ico" type="image/x-icon">
  <title>Asset Management System</title>
  <meta name="description" content="Comprehensive asset and maintenance management system for industrial operations" />
  <meta name="author" content="MGX" />

  <meta property="og:title" content="Asset Management System" />
  <meta property="og:description" content="Comprehensive asset and maintenance management system for industrial operations" />
  <meta property="og:type" content="website" />

  <!-- Google Fonts: Manrope, Inter, Space Grotesk -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
  
  <!-- Material Symbols Outlined -->
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet">

</head>

<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>

</html>
```

- [ ] **Step 2: Verify fonts load correctly**

Start the frontend dev server and check the Network tab in DevTools:

```bash
cd app/frontend
npm run dev
```

Expected: All font files load successfully (no 404s)

- [ ] **Step 3: Commit the changes**

```bash
git add app/frontend/index.html
git commit -m "feat: add Google Fonts and Material Symbols"
```

---

## Task 5: Frontend — Extend Tailwind Config with Design Tokens

**Files:**
- Modify: `app/frontend/tailwind.config.ts:1-93`

- [ ] **Step 1: Update tailwind.config.ts with new colors and fonts**

```typescript
import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";
import tailwindcssAspectRatio from "@tailwindcss/aspect-ratio";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        display: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['"Space Grotesk"', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
        // New Material Design 3 tokens for "Orchestrated Void" aesthetic
        surface: '#0b1326',
        'surface-container-lowest': '#060e20',
        'surface-container-low': '#131b2e',
        'surface-container': '#171f33',
        'surface-container-high': '#222a3d',
        'surface-container-highest': '#2d3449',
        'surface-bright': '#31394d',
        'surface-dim': '#0b1326',
        'on-surface': '#dae2fd',
        'on-surface-variant': '#bfc7d5',
        'primary-container': '#0099ff',
        'on-primary-container': '#002f54',
        'audit-error': '#ffb4ab',
        'audit-success': '#34d399',
        'audit-update': '#38bdf8',
        'outline-variant': '#3f4753',
        'outline': '#89919e',
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "1.5rem",
        "2xl": "1rem",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [tailwindcssAnimate, tailwindcssAspectRatio],
} satisfies Config;
```

- [ ] **Step 2: Verify Tailwind build succeeds**

```bash
cd app/frontend
npm run build
```

Expected: No TypeScript or Tailwind errors

- [ ] **Step 3: Commit the changes**

```bash
git add app/frontend/tailwind.config.ts
git commit -m "feat: add Material Design 3 tokens for audit log design"
```

---

## Task 6: Frontend — Add Glass Panel Utilities to CSS

**Files:**
- Modify: `app/frontend/src/index.css:1-227`

- [ ] **Step 1: Add glass-panel and related utilities**

Add to the `@layer utilities` section (after line 153):

```css
@layer utilities {
  .glass {
    @apply bg-white/10 backdrop-blur-[var(--glass-blur)] border border-white/20;
  }

  .glass-dark {
    @apply bg-black/40 backdrop-blur-[var(--glass-blur)] border border-white/10;
  }

  /* Orchestrated Void: Glass Panel */
  .glass-panel {
    background: rgba(11, 19, 38, 0.4);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(137, 145, 158, 0.15);
    box-shadow: 0px 24px 48px -12px rgba(0, 153, 255, 0.08);
  }

  .audit-entry-hover-lift {
    @apply hover:-translate-y-1 transition-transform duration-200;
  }

  .shadow-cyan-bloom {
    box-shadow: 0px 24px 48px -12px rgba(0, 153, 255, 0.08);
  }

  .text-gradient-premium {
    @apply bg-clip-text text-transparent bg-gradient-to-r from-[hsl(var(--premium-indigo))] via-[hsl(var(--premium-purple))] to-[hsl(var(--premium-rose))];
  }

  .bg-gradient-premium {
    @apply bg-gradient-to-br from-[hsl(var(--premium-indigo))] via-[hsl(var(--premium-purple))] to-[hsl(var(--premium-rose))];
  }

  .animate-premium-fade-in {
    animation: premium-fade-in 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }

  @keyframes premium-fade-in {
    from {
      opacity: 0;
      transform: translateY(10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .mesh-gradient {
    background: linear-gradient(135deg,
      hsl(217 32% 15%) 0%,
      hsl(212 100% 35%) 25%,
      hsl(217 28% 20%) 50%,
      hsl(212 90% 40%) 75%,
      hsl(217 32% 15%) 100%);
    background-size: 400% 400%;
    animation: mesh-gradient 8s ease infinite;
    position: relative;
  }

  .mesh-gradient::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
      radial-gradient(circle at 20% 50%, rgba(66, 133, 244, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(26, 188, 156, 0.1) 0%, transparent 50%),
      radial-gradient(circle at 40% 20%, rgba(155, 89, 182, 0.1) 0%, transparent 50%);
    animation: gradient-shift 6s ease-in-out infinite;
    pointer-events: none;
  }
}
```

- [ ] **Step 2: Verify CSS builds correctly**

```bash
cd app/frontend
npm run build
```

Expected: No CSS errors

- [ ] **Step 3: Commit the changes**

```bash
git add app/frontend/src/index.css
git commit -m "feat: add glass-panel utilities for audit log"
```

---

## Task 7: Frontend — Rewrite AuditLogViewer Component (Structure)

**Files:**
- Modify: `app/frontend/src/modules/shared/AuditLogViewer.tsx:1-425`
- Test: Visual QA in dev server

- [ ] **Step 1: Create the new component structure**

Replace the entire file with:

```typescript
import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/AuthContext';
import { debounce } from '@/lib/utils';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface AuditEntry {
  id: number;
  action_type: string;
  entity_type: string;
  entity_id: number;
  entity_name?: string;
  user_id?: number;
  user_name?: string;
  changes?: Record<string, { old: any; new: any }>;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  ip_address?: string;
  description?: string;
  created_at: string;
}

interface AuditStats {
  by_action: Record<string, number>;
  by_user: Record<string, number>;
  by_entity: Record<string, number>;
  total: number;
}

const ENTITY_TYPES_ADMIN = ['all', 'machine', 'work_order', 'intervention', 'planning', 'user', 'alert', 'inventory', 'report'];
const ENTITY_TYPES_CHEFTECH = ['all', 'work_order', 'intervention', 'user'];

const ACTION_TYPES = ['all', 'CREATE', 'UPDATE', 'DELETE', 'VIEW'];

const actionColors: Record<string, string> = {
  CREATE: 'emerald',
  UPDATE: 'sky',
  DELETE: 'audit-error',
  VIEW: 'slate',
};

const actionIcons: Record<string, string> = {
  CREATE: 'add_circle',
  UPDATE: 'edit_note',
  DELETE: 'delete',
  VIEW: 'visibility',
};

const entityLabels: Record<string, string> = {
  machine: "Machine",
  work_order: "Work Order",
  intervention: "Intervention",
  planning: "Planning",
  user: "User",
  alert: "Alert",
  inventory: "Inventory",
  report: "Report"
};

export const AuditLogViewer: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const isCheftech = user?.role === 'CHEFTECH';

  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats>({ by_action: {}, by_user: {}, by_entity: {}, total: 0 });
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('all');
  const [actionTypeFilter, setActionTypeFilter] = useState<string>('all');
  const [userSearch, setUserSearch] = useState<string>('');
  const [dateRange, setDateRange] = useState<{ from: string; to: string }>({ from: '', to: '' });

  const entityOptions = isAdmin ? ENTITY_TYPES_ADMIN : ENTITY_TYPES_CHEFTECH;

  // Debounced user search
  const debouncedUserSearch = useCallback(
    debounce((value: string) => {
      setUserSearch(value);
      setPage(0);
    }, 300),
    []
  );

  useEffect(() => {
    fetchAuditLog();
    fetchStats();
  }, [page, entityTypeFilter, actionTypeFilter, userSearch]);

  const fetchAuditLog = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('skip', String(page * 50));
      params.append('limit', '50');
      if (entityTypeFilter !== 'all') params.append('entity_type', entityTypeFilter);
      if (actionTypeFilter !== 'all') params.append('action_type', actionTypeFilter);
      if (userSearch) params.append('user_search', userSearch);
      
      const res = await fetch(`${API}/api/v1/audit/log?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setEntries(data.items || []);
        setTotal(data.total || 0);
      } else {
        console.error('Failed to load audit log');
      }
    } catch (err) {
      console.error('Failed to load audit log', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const params = new URLSearchParams();
      if (entityTypeFilter !== 'all') params.append('entity_type', entityTypeFilter);
      
      const res = await fetch(`${API}/api/v1/audit/stats?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to load stats', err);
    }
  };

  const exportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (entityTypeFilter !== 'all') params.append('entity_type', entityTypeFilter);
      
      const res = await fetch(`${API}/api/v1/audit/export?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([data.csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_log_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Export failed', err);
    }
  };

  const totalPages = Math.ceil(total / 50);

  const relativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} mins ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return `${diffDays} days ago`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f172a] via-[#1e3a5f] to-[#1e293b] font-body">
      {/* Page Header */}
      <header className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-extrabold tracking-tight text-white">Audit Log</h1>
          <p className="text-on-surface-variant font-body mt-2">
            Comprehensive forensic history of system mutations and user actions.
          </p>
          {isCheftech && (
            <Badge variant="outline" className="mt-2 font-label text-[10px] uppercase tracking-widest">
              Scope: Technicians · Work Orders · Interventions
            </Badge>
          )}
        </div>
        <div className="flex gap-4">
          <Button variant="outline" size="icon" className="w-12 h-12 glass-panel rounded-xl" onClick={fetchAuditLog}>
            <span className="material-symbols-outlined">refresh</span>
          </Button>
          {(isAdmin || isCheftech) && (
            <Button variant="outline" className="px-6 h-12 glass-panel border border-primary/20 rounded-xl flex items-center gap-2" onClick={exportCSV}>
              <span className="material-symbols-outlined">download</span>
              Export CSV
            </Button>
          )}
        </div>
      </header>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard label="Total Entries" value={stats.total.toLocaleString()} accent="neutral" trend="+4.2%" />
        <StatCard label="Creates" value={stats.by_action.CREATE?.toLocaleString() || '0'} accent="emerald" suffix="Today" />
        <StatCard label="Updates" value={stats.by_action.UPDATE?.toLocaleString() || '0'} accent="sky" suffix="Today" />
        <StatCard label="Deletes" value={stats.by_action.DELETE?.toLocaleString() || '0'} accent="error" trend="-12%" />
      </div>

      {/* Filter Bar */}
      <div className="glass-panel p-4 rounded-2xl mb-8 flex flex-wrap items-center gap-6">
        <div className="flex-1 min-w-[200px]">
          <label className="block font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 ml-1">
            Entity Type
          </label>
          <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
            <SelectTrigger className="w-full bg-surface-container-lowest border-none rounded-xl text-sm focus:ring-1 focus:ring-primary h-10 px-4">
              <SelectValue placeholder="All Entities" />
            </SelectTrigger>
            <SelectContent>
              {entityOptions.map((type) => (
                <SelectItem key={type} value={type}>
                  {type === 'all' ? 'All Entities' : entityLabels[type] || type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 ml-1">
            Action Type
          </label>
          <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
            <SelectTrigger className="w-full bg-surface-container-lowest border-none rounded-xl text-sm focus:ring-1 focus:ring-primary h-10 px-4">
              <SelectValue placeholder="All Actions" />
            </SelectTrigger>
            <SelectContent>
              {ACTION_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type === 'all' ? 'All Actions' : type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 ml-1">
            User Search
          </label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-lg">
              search
            </span>
            <Input
              className="w-full bg-surface-container-lowest border-none rounded-xl text-sm focus:ring-1 focus:ring-primary h-10 pl-10"
              placeholder="ID or Username"
              onChange={(e) => debouncedUserSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 ml-1">
            Date Range
          </label>
          <div className="flex items-center h-10 glass-panel rounded-xl px-4 text-sm gap-2 cursor-pointer hover:bg-surface-bright transition-colors">
            <span className="material-symbols-outlined text-primary text-lg">calendar_month</span>
            <span>Oct 24 - Oct 31, 2023</span>
          </div>
        </div>
      </div>

      {/* Two-Column Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: List */}
        <div className="lg:col-span-2 space-y-4 max-h-[800px] overflow-y-auto scrollbar-hide pr-2">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No audit entries found
            </div>
          ) : (
            entries.map((entry) => (
              <EntryCard
                key={entry.id}
                entry={entry}
                selected={selectedEntry?.id === entry.id}
                onClick={() => setSelectedEntry(entry)}
                relativeTime={relativeTime}
              />
            ))
          )}
        </div>

        {/* Right Column: Detail Panel */}
        <div className="lg:col-span-1">
          <ForensicDetailsPanel entry={selectedEntry} />
        </div>
      </div>

      {/* Pagination */}
      <div className="mt-8 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {entries.length} of {total} entries
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
            Previous
          </Button>
          <span className="text-sm">Page {page + 1} of {totalPages || 1}</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
};

// Sub-components will be defined in Task 8
```

- [ ] **Step 2: Add the debounce utility if not exists**

Create `app/frontend/src/lib/utils.ts` if it doesn't exist:

```typescript
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd app/frontend
npm run build
```

Expected: No TypeScript errors (sub-components will be added in Task 8)

- [ ] **Step 4: Commit the changes**

```bash
git add app/frontend/src/modules/shared/AuditLogViewer.tsx app/frontend/src/lib/utils.ts
git commit -m "feat: rewrite AuditLogViewer component structure"
```

---

## Task 8: Frontend — Add Sub-components (StatCard, EntryCard, ForensicDetailsPanel)

**Files:**
- Modify: `app/frontend/src/modules/shared/AuditLogViewer.tsx`

- [ ] **Step 1: Add StatCard component**

Add after the main component:

```typescript
interface StatCardProps {
  label: string;
  value: string;
  accent: 'neutral' | 'emerald' | 'sky' | 'error';
  suffix?: string;
  trend?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, accent, suffix, trend }) => {
  const accentColors: Record<string, string> = {
    neutral: 'text-white',
    emerald: 'text-emerald-400',
    sky: 'text-sky-400',
    error: 'text-audit-error',
  };

  const borderColors: Record<string, string> = {
    neutral: 'border-transparent',
    emerald: 'border-emerald-500/20',
    sky: 'border-sky-500/20',
    error: 'border-audit-error/20',
  };

  return (
    <div className={`glass-panel p-6 rounded-2xl relative overflow-hidden group border-l-2 ${borderColors[accent]}`}>
      <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full -mr-8 -mt-8"></div>
      <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <h3 className={`text-3xl font-display font-bold ${accentColors[accent]}`}>{value}</h3>
        {suffix && <span className="text-slate-500 text-xs font-label">{suffix}</span>}
        {trend && (
          <span className={`text-xs font-bold ${trend.startsWith('+') ? 'text-emerald-400' : 'text-error'}`}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Add EntryCard component**

```typescript
interface EntryCardProps {
  entry: AuditEntry;
  selected: boolean;
  onClick: () => void;
  relativeTime: (date: string) => string;
}

const EntryCard: React.FC<EntryCardProps> = ({ entry, selected, onClick, relativeTime }) => {
  const color = actionColors[entry.action_type] || 'slate';
  const icon = actionIcons[entry.action_type] || 'info';

  const borderColors: Record<string, string> = {
    emerald: 'border-l-emerald-500',
    sky: 'border-l-sky-500',
    'audit-error': 'border-l-audit-error',
    slate: 'border-l-slate-500',
  };

  const bgColors: Record<string, string> = {
    emerald: 'bg-emerald-500/10',
    sky: 'bg-sky-500/10',
    'audit-error': 'bg-audit-error/10',
    slate: 'bg-slate-500/10',
  };

  const textColors: Record<string, string> = {
    emerald: 'text-emerald-400',
    sky: 'text-sky-400',
    'audit-error': 'text-audit-error',
    slate: 'text-slate-400',
  };

  return (
    <div
      className={`glass-panel p-5 rounded-2xl border-l-4 ${borderColors[color]} hover:translate-x-1 transition-transform cursor-pointer relative ${
        selected ? 'bg-surface-container-highest/20' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-full ${bgColors[color]} flex items-center justify-center ${textColors[color]}`}>
            <span className="material-symbols-outlined">{icon}</span>
          </div>
          <div>
            <h4 className="font-bold text-white">
              {entry.action_type} {entityLabels[entry.entity_type] || entry.entity_type} #{entry.entity_id}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold">
                {(entry.user_name || 'U').charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-on-surface-variant">{entry.user_name || 'System'}</span>
              <span className="w-1 h-1 rounded-full bg-slate-700"></span>
              <span className="text-xs font-label text-slate-500">{relativeTime(entry.created_at)}</span>
            </div>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full ${bgColors[color]} ${textColors[color]} text-[10px] font-label font-bold uppercase tracking-widest border ${borderColors[color].replace('border-l-', 'border-')}`}>
          {entry.action_type}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 3: Add ForensicDetailsPanel component**

```typescript
interface ForensicDetailsPanelProps {
  entry: AuditEntry | null;
}

const ForensicDetailsPanel: React.FC<ForensicDetailsPanelProps> = ({ entry }) => {
  if (!entry) {
    return (
      <div className="glass-panel p-8 rounded-2xl sticky top-28 shadow-2xl border-primary/5">
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 flex items-center justify-center text-sky-400 mb-4 scale-110">
            <span className="material-symbols-outlined text-4xl">edit_square</span>
          </div>
          <h2 className="text-2xl font-display font-bold text-white">Forensic Details</h2>
          <p className="text-on-surface-variant text-sm mt-1">Select an entry to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-8 rounded-2xl sticky top-28 shadow-2xl border-primary/5">
      <div className="flex flex-col items-center text-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-sky-500/10 flex items-center justify-center text-sky-400 mb-4 scale-110">
          <span className="material-symbols-outlined text-4xl">edit_square</span>
        </div>
        <h2 className="text-2xl font-display font-bold text-white">Forensic Details</h2>
        <p className="text-on-surface-variant text-sm mt-1">
          Entry ID: <span className="font-mono text-primary">AUDIT-{entry.id}-TX</span>
        </p>
      </div>

      <div className="space-y-6">
        <div className="flex justify-between items-center py-3 border-b border-white/5">
          <span className="font-label text-xs uppercase tracking-widest text-slate-500">Operator Role</span>
          <span className="text-sm font-bold text-secondary">SYSTEM_ADMIN</span>
        </div>
        <div className="flex justify-between items-center py-3 border-b border-white/5">
          <span className="font-label text-xs uppercase tracking-widest text-slate-500">IP Address</span>
          <span className="font-mono text-xs text-white">{entry.ip_address || '—'}</span>
        </div>
        <div className="flex justify-between items-center py-3 border-b border-white/5">
          <span className="font-label text-xs uppercase tracking-widest text-slate-500">Entity Affected</span>
          <span className="font-mono text-xs text-sky-400">
            {entry.entity_type.toUpperCase()}_{entry.entity_id}
          </span>
        </div>

        {entry.changes && Object.keys(entry.changes).length > 0 && (
          <div className="mt-8">
            <p className="font-label text-[10px] uppercase tracking-widest text-primary mb-4">Changes Detected</p>
            <div className="space-y-4">
              {Object.entries(entry.changes).map(([field, change]) => (
                <div key={field} className="bg-surface-container-lowest/50 p-4 rounded-xl border border-white/5">
                  <p className="text-[10px] font-label text-slate-500 mb-2 uppercase">Field: {field}</p>
                  <div className="flex items-center gap-3">
                    <span className="text-audit-error line-through text-xs font-mono">
                      {String(change.old || '—')}
                    </span>
                    <span className="material-symbols-outlined text-slate-600 text-sm">arrow_forward</span>
                    <span className="text-emerald-400 font-bold text-xs font-mono">
                      {String(change.new || '—')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Note: Revert Action button omitted - no backend support */}
    </div>
  );
};
```

- [ ] **Step 4: Add MachineHistoryPanel component (restyled)**

```typescript
export const MachineHistoryPanel: React.FC = () => {
  const { machineId } = useParams<{ machineId: string }>();
  const [history, setHistory] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (machineId) {
      fetchMachineHistory();
    }
  }, [machineId]);

  const fetchMachineHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/audit/log/${machineId}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        setHistory(await res.json());
      }
    } catch (err) {
      console.error('Failed to load machine history', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">history</span>
        <h3 className="font-display font-bold text-white">Machine History</h3>
      </div>
      
      {history.length === 0 ? (
        <p className="text-sm text-muted-foreground">No history available</p>
      ) : (
        <div className="space-y-2">
          {history.map((entry) => (
            <div key={entry.id} className="glass-panel p-3 rounded-xl flex items-start gap-3">
              <div className={`w-8 h-8 rounded-full bg-${actionColors[entry.action_type] || 'slate'}-500/10 flex items-center justify-center`}>
                <span className={`material-symbols-outlined text-${actionColors[entry.action_type] || 'slate'}-400 text-sm`}>
                  {actionIcons[entry.action_type]}
                </span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{entry.description || `${entry.action_type} operation`}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <span className="text-on-surface-variant">{entry.user_name || 'System'}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                  <span className="font-label">{new Date(entry.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AuditLogViewer;
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd app/frontend
npm run build
```

Expected: No TypeScript errors

- [ ] **Step 6: Commit the changes**

```bash
git add app/frontend/src/modules/shared/AuditLogViewer.tsx
git commit -m "feat: add StatCard, EntryCard, ForensicDetailsPanel sub-components"
```

---

## Task 9: Verification and Testing

**Files:**
- All modified files

- [ ] **Step 1: Backend static check**

```bash
cd app/backend
python -m py_compile services/audit.py modules/shared/routes/audit.py
```

Expected: No syntax errors

- [ ] **Step 2: Frontend build**

```bash
cd app/frontend
npm run build
```

Expected: No TypeScript or Tailwind errors

- [ ] **Step 3: Test as ADMIN user**

Start the backend and frontend servers, then:
1. Login as ADMIN
2. Navigate to `/audit-log`
3. Verify all entities visible in dropdown
4. Verify Export CSV button visible
5. Verify stats cards show data
6. Click an entry to view forensic details

- [ ] **Step 4: Test as CHEFTECH user**

1. Login as CHEFTECH
2. Navigate to `/audit-log`
3. Verify entity dropdown limited to work_order, intervention, user
4. Verify Export CSV button visible
5. Verify scope chip "Scope: Technicians · Work Orders · Interventions" visible
6. Verify counts are lower than ADMIN view

- [ ] **Step 5: Test user_search functionality**

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "http://localhost:8000/api/v1/audit/log?user_search=Admin" | jq '.items[].user_name'
```

Expected: Returns only entries with "Admin" in username

- [ ] **Step 6: Visual QA**

Open `/audit-log` in dev server and verify:
- Fonts load correctly (Manrope for headings, Inter for body, Space Grotesk for labels)
- Glass panels have correct blur and transparency
- Action colors match design (emerald for CREATE, sky for UPDATE, error for DELETE)
- Hover effects work (translate-x on entry cards)
- Selected entry has different background
- Forensic details panel shows changes with strikethrough old values

- [ ] **Step 7: Commit final verification**

```bash
git add .
git commit -m "chore: verify audit log redesign implementation"
```

---

## Out of Scope (Explicit)

- Automatic IP capture on every write endpoint (separate task)
- Real-time audit stream (WebSocket)
- "Revert Action" functionality (no backend endpoint)
- Entity-history endpoint RBAC migration (separate security task)
- Replacing app's existing Layout/Sidebar (using existing app layout)
