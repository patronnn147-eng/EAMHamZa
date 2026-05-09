# Phase 12: ChefTech Alert Response Workflow — Research

**Confidence:** HIGH (direct codebase inspection)
**Date:** 2026-05-09

---

## Summary

Build a 3-swimlane alert triage page for ChefTech. All required backend APIs exist. Reusable frontend assets are available. One API correction from CONTEXT.md: use `GET /api/v1/cheftech/techniciens` (not the admin-only planning endpoint) for the technician dropdown.

---

## Existing Assets — HIGH Confidence

### Frontend Components Available

| Asset | Path | Usage |
|-------|------|-------|
| `severityConfig` | `app/frontend/src/modules/shared/AlertsPanel.tsx:37-82` | Copy/extract — colors, borders, icons, badge classes for all 4 severities |
| `Sheet` (slide panel) | `app/frontend/src/components/ui/sheet.tsx` | `Sheet`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetClose` from Radix Dialog |
| `Select` | `app/frontend/src/components/ui/select.tsx` | Technician dropdown, priority dropdown |
| `Button`, `Badge`, `Card`, `Checkbox` | `app/frontend/src/components/ui/` | Standard form controls |
| `useToast` | `app/frontend/src/hooks/use-toast.ts` | Undo dismiss — pass `action` prop to toast for "Annuler" button |
| `useAuth` | `app/frontend/src/contexts/AuthContext.tsx` | `user.id` for dismiss API call; `user.role` for access guard |
| `DatePicker` / `Calendar` | `app/frontend/src/components/ui/calendar.tsx` + `popover.tsx` | Due date picker in triage panel |

### Established Patterns

**Auth & Fetch:**
```typescript
const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

const res = await fetch(`${API}/api/v1/alerts`, {
  headers: { Authorization: `Bearer ${getToken()}` }
});
```
(From `AlertsPanel.tsx` lines 93-115 — use this exact pattern)

**Dark theme classes:**
- Card background: `bg-[#0f1623]`
- Hover: `hover:bg-[#131c2e]`
- Borders: `border-white/[0.06]`, `border-white/[0.1]` on hover
- Text muted: `text-white/60`, `text-white/40`

**Current user:**
```typescript
const { user } = useAuth(); // user.id, user.role, user.nom
```

---

## API Endpoints — HIGH Confidence

### Alerts
```
GET  /api/v1/alerts                          → List active alerts (no auth restriction beyond JWT)
PATCH /api/v1/alerts/{id}/dismiss            → body: { user_id: number }
POST  /api/v1/alerts/{id}/create-work-order  → body: { created_by, assigned_to?, priority?, due_date?, title?, description? }
```

**Alert response shape:**
```typescript
{
  id: number,
  alert_id: string,
  machine_id: number,
  alert_type: string,        // "RUL_ALERT" | "FAILURE_PREDICTION" | "ANOMALY_DETECTION"
  severity: string,          // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  message: string,
  rul_days?: number,
  failure_probability?: number,  // 0.0–1.0
  is_active: boolean,
  is_linked_to_wo: boolean,
  work_order_id?: number,
  priority?: string,
  created_at: string,        // ISO datetime
  dismissed_at?: string,
  dismissed_by?: number
}
```

### Technicians (CHEFTECH-accessible ✓)
```
GET /api/v1/cheftech/techniciens?page=1&size=100
```
Response: `PaginatedResponse<TechnicianResponse>` → `{ items: [{id, nom, email, role}], total, page, ... }`

⚠️ **Do NOT use** `GET /api/v1/plannings/users/by-role/TECHNICIEN` — requires ADMIN role.

### Technician availability (open work orders)
```
GET /api/v1/entities/ordres_travail?query={"assigned_to": {techId}}&limit=100
```
Filter client-side for statut ≠ "TERMINE" and ≠ "ANNULE" to count open WOs.

### Machines (for name resolution)
```typescript
// Use SDK client for batch machine fetch:
const res = await client.entities.machines.query({ query: {}, limit: 500 });
// → { data: { items: [{id, nom, ...}] } }
```
Build a `Map<number, string>` (id → name) on load. Reference by `alert.machine_id`.

---

## Swimlane Logic — Client-Side

Single `GET /api/v1/alerts` call, split into 3 lanes:

```typescript
const systemLane = alerts.filter(a =>
  ['MEDIUM', 'LOW'].includes(a.severity) && !a.is_linked_to_wo
);

const cheftechLane = alerts.filter(a =>
  ['CRITICAL', 'HIGH'].includes(a.severity) && !a.is_linked_to_wo
);

const technicianLane = alerts.filter(a => a.is_linked_to_wo);
```

---

## Triage Panel — Sheet Component

```tsx
<Sheet open={!!selectedAlert} onOpenChange={(open) => !open && setSelectedAlert(null)}>
  <SheetContent side="right" className="w-[360px] bg-[#0f1623] border-white/[0.06]">
    <SheetHeader>
      <SheetTitle>Triage — {selectedAlert?.machine_name}</SheetTitle>
    </SheetHeader>
    {/* 3 sections: summary, assign, actions */}
  </SheetContent>
</Sheet>
```

---

## Technician Availability Check

When ChefTech opens dropdown and selects tech → fetch their open WOs:

```typescript
const checkTechAvailability = async (techId: number) => {
  const res = await fetch(`${API}/api/v1/entities/ordres_travail?query=${JSON.stringify({assigned_to: techId})}&limit=100`, ...);
  const data = await res.json();
  const openWOs = (data.items || []).filter(
    wo => !['TERMINE', 'ANNULE'].includes(wo.statut)
  );
  return openWOs.length;
};
```

Show warning if `openWOs.length > 0`: inline orange text + ⚠ icon. ChefTech can still assign.

---

## Undo Dismiss Implementation

Use toast with action button. Dismiss fires AFTER undo window:

```typescript
// 1. Optimistically remove from local state
setAlerts(prev => prev.filter(a => a.id !== alertId));

// 2. Show toast with undo
let undone = false;
const { dismiss } = toast({
  title: 'Alerte supprimée',
  action: (
    <ToastAction altText="Annuler" onClick={() => {
      undone = true;
      setAlerts(prev => [...prev, alert]); // restore
      dismiss();
    }}>
      Annuler
    </ToastAction>
  ),
});

// 3. After 3s, if not undone, call API
setTimeout(async () => {
  if (!undone) {
    await fetch(`${API}/api/v1/alerts/${alertId}/dismiss`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUserId }),
    });
  }
}, 3000);
```

---

## Optimistic Assign & Move

```typescript
const handleAssign = async (alert, formData) => {
  // 1. Move card: remove from cheftechLane, add to technicianLane
  setAlerts(prev => prev.map(a =>
    a.id === alert.id ? { ...a, is_linked_to_wo: true } : a
  ));

  // 2. Close panel
  setSelectedAlert(null);

  // 3. Call API
  await fetch(`${API}/api/v1/alerts/${alert.id}/create-work-order`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      created_by: currentUserId,
      assigned_to: formData.technicienId,
      priority: formData.priority,
      due_date: formData.dueDate,
    }),
  });
};
```

---

## Routing & Navigation Integration

**AppRoutes.tsx** — add after line 262 (current `/alerts` route):
```tsx
<Route
  path="/cheftech/alerts"
  element={
    <ProtectedRoute allowedRoles={['CHEFTECH']}>
      <Layout>
        <ChefTechAlertWorkflow />
      </Layout>
    </ProtectedRoute>
  }
/>
```

**Sidebar.tsx** — add in CHEFTECH block (after `Alertes Prédictives` at ~line 82):
```typescript
{ name: 'Centre des alertes', href: '/cheftech/alerts', icon: Bell },
```

---

## Machine Name Resolution — Pattern

```typescript
// On component mount, parallel fetch
const [alerts, machinesMap] = await Promise.all([
  fetchAlerts(),
  fetchMachinesMap(),
]);

async function fetchMachinesMap(): Promise<Map<number, string>> {
  const res = await client.entities.machines.query({ query: {}, limit: 500 });
  const map = new Map<number, string>();
  for (const m of res.data.items || []) {
    map.set(m.id, m.nom || `Machine #${m.id}`);
  }
  return map;
}

// Usage in card:
const machineName = machinesMap.get(alert.machine_id) ?? `Machine #${alert.machine_id}`;
// Display: "Convoyeur B-72 (#42)"
```

---

## Potential Pitfalls

1. **`severityConfig` is defined locally in AlertsPanel.tsx** — copy it into the new component or extract to `src/lib/alertUtils.ts` shared util (preferred)
2. **Sheet `side="right"` with dark bg** — needs explicit `bg-[#0f1623]` override, default is white
3. **Toast `action` prop** — requires `ToastAction` from `@/components/ui/toast`, not a plain button
4. **Relative timestamp** — use `date-fns/formatDistanceToNow` or simple manual diff; `date-fns` already in project (`package.json`)
5. **`client.entities.machines.query` uses SDK pattern** — different from direct `fetch()`. Both work; use SDK for machines, direct `fetch()` for alerts/cheftech routes
6. **Technician lane edit mode** — open Sheet in edit mode by setting `editMode: true` in state alongside `selectedAlert`

---

## File Plan

| File | Action |
|------|--------|
| `app/frontend/src/modules/cheftech/ChefTechAlertWorkflow.tsx` | CREATE — main page component |
| `app/frontend/src/lib/alertUtils.ts` | CREATE — extract `severityConfig` + helper types |
| `app/frontend/src/app/routing/AppRoutes.tsx` | MODIFY — add route |
| `app/frontend/src/components/layout/Sidebar.tsx` | MODIFY — add nav entry |

---

## RESEARCH COMPLETE
