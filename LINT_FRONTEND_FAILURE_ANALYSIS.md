# Lint Frontend Job Failure Analysis

**Workflow:** Source Code Security  
**Job ID:** 82565749522  
**Status:** ❌ Failed  
**Date:** 2026-06-21T11:22:05Z  
**Workflow File:** `.github/workflows/source-security.yml`  
**Job URL:** https://github.com/hamzAmbarki2/EAMSagemCom/actions/runs/27902676314/job/82565749522

---

## Root Cause

The **lint-frontend** job failed due to **133 ESLint errors** detected in the React/TypeScript frontend codebase. The errors are primarily from the `@typescript-eslint/no-explicit-any` rule, which enforces type safety by preventing the use of the `any` type annotation. Additionally, there is 1 **critical React Hooks violation** that breaks the rules of hooks.

---

## Error Summary

**Total Errors:** 133
- **132 errors:** `@typescript-eslint/no-explicit-any` — Using `any` type instead of specific types
- **1 error:** `react-hooks/rules-of-hooks` — Hook called conditionally

**Exit Code:** 1 (Process failed)

---

## Detailed Error Log

### React Hooks Violation (Critical)

```
/home/runner/work/EAMSagemCom/EAMSagemCom/app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx
  70:22  error  React Hook "useRef" is called conditionally. React Hooks must be called in the exact same order in every component render  react-hooks/rules-of-hooks
```

**Why this is critical:** React Hooks must be called unconditionally in the exact same order on every render. Calling hooks inside conditionals (if statements, loops, etc.) breaks React's internal hook tracking mechanism and causes subtle bugs.

---

### TypeScript Explicit Any Errors (132 instances)

The `@typescript-eslint/no-explicit-any` rule detects 132 instances of the `any` type throughout your frontend codebase. Here are the files with the most violations:

#### **PDCACanbanBoard.tsx** — 17 errors
```
34:48   error  Unexpected any. Specify a different type
82:48   error  Unexpected any. Specify a different type
83:50   error  Unexpected any. Specify a different type
85:53   error  Unexpected any. Specify a different type
103:37  error  Unexpected any. Specify a different type
104:54  error  Unexpected any. Specify a different type
125:34  error  Unexpected any. Specify a different type
145:36  error  Unexpected any. Specify a different type
167:39  error  Unexpected any. Specify a different type
186:29  error  Unexpected any. Specify a different type
187:30  error  Unexpected any. Specify a different type
209:29  error  Unexpected any. Specify a different type
210:30  error  Unexpected any. Specify a different type
315:29  error  Unexpected any. Specify a different type
360:25  error  Unexpected any. Specify a different type
435:25  error  Unexpected any. Specify a different type
480:25  error  Unexpected any. Specify a different type
536:20  error  Unexpected any. Specify a different type
```

#### **RAGDocuments.tsx** — 10 errors
```
153:17  error  Unexpected any. Specify a different type
191:17  error  Unexpected any. Specify a different type
227:17  error  Unexpected any. Specify a different type
274:17  error  Unexpected any. Specify a different type
298:17  error  Unexpected any. Specify a different type
327:17  error  Unexpected any. Specify a different type
349:17  error  Unexpected any. Specify a different type
629:64  error  Unexpected any. Specify a different type
753:64  error  Unexpected any. Specify a different type
```

#### **MLIntelligenceTab.tsx** — 4 errors
```
38:24   error  Unexpected any. Specify a different type
305:21  error  Unexpected any. Specify a different type
689:77  error  Unexpected any. Specify a different type
808:74  error  Unexpected any. Specify a different type
```

#### **MachineDetailPage.tsx** — 5 errors
```
56:24   error  Unexpected any. Specify a different type
188:25  error  Unexpected any. Specify a different type
308:76  error  Unexpected any. Specify a different type
332:55  error  Unexpected any. Specify a different type
359:90  error  Unexpected any. Specify a different type
```

#### **CertificateModule.tsx** — 8 errors
```
593:17  error  Unexpected any. Specify a different type
593:73  error  Unexpected any. Specify a different type
656:21  error  Unexpected any. Specify a different type
657:18  error  Unexpected any. Specify a different type
1069:64 error  Unexpected any. Specify a different type
```

#### **AnomalieModule.tsx** — 5+ errors
Multiple instances of the `any` type throughout the file.

#### **Other Files with `any` Errors:**
- Dashboard.tsx — 2 errors
- IoTDashboard.tsx — 1 error
- PlanningCalendarView.tsx — 2 errors
- PlanningMachinesDialog.tsx — 2 errors
- BriefingBar.tsx — 2 errors
- dashboardFilters.test.ts — 1 error
- MachineModel.tsx — 1 error
- ExplainabilityDrawer.tsx — 1 error
- MachineFormDialog.tsx — 1 error
- PredictivePanel.tsx — 1 error
- ProcurementRecommendationModal.tsx — 2 errors
- healthScore.ts — 3 errors
- TechnicianDashboard.tsx — 1 error

---

## Recommended Solutions

### Option 1: Quick Fix - Downgrade Rule to Warning (Fastest) ⚡

If you want to unblock the workflow immediately while addressing type safety gradually:

**Find your ESLint configuration file:**

```bash
# It's likely one of these:
cat app/frontend/.eslintrc.json
cat app/frontend/.eslintrc.js
cat app/frontend/.eslintrc
```

**Add or modify the rule:**

```json
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "react-hooks/rules-of-hooks": "error"
  }
}
```

This downgrades `any` type violations to warnings, so they won't fail the job. The React hooks violation remains an error.

**After updating, commit and push:**

```bash
git add app/frontend/.eslintrc.json
git commit -m "fix: downgrade no-explicit-any to warning to unblock linting"
git push
```

**Pros:** Unblocks immediately, allows gradual improvement  
**Cons:** Doesn't enforce type safety

---

### Option 2: Fix React Hooks Issue First (Required)

This is a **critical bug** that must be fixed regardless of the `any` issue.

#### **Issue Location:** `app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx` line 70

**Pattern - Conditional Hook Call:**
```typescript
// BEFORE (WRONG - Hook called conditionally):
if (someCondition) {
  const ref = useRef(null);
}

if (anotherCondition) {
  useEffect(() => {
    // effect code
  }, []);
}
```

**Fix - Move Hooks Outside Conditional:**
```typescript
// AFTER (CORRECT - Hooks called unconditionally):
const ref = useRef(null);

useEffect(() => {
  if (anotherCondition) {
    // effect code
  }
}, [anotherCondition]);
```

**Key Rule:** All React Hooks (`useState`, `useEffect`, `useRef`, `useCallback`, etc.) must be called at the top level of your component, in the same order on every render.

---

### Option 3: Replace `any` with Proper Types (Recommended Long-term)

This is the best approach for code quality. Here are common patterns to follow:

#### **Pattern 1: Component Props with Interfaces**

```typescript
// BEFORE:
interface Props {
  data: any;
  onUpdate: (value: any) => void;
  metrics: any;
}

// AFTER:
interface MachineData {
  id: number;
  name: string;
  status: 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';
  healthScore: number;
}

interface Props {
  data: MachineData;
  onUpdate: (value: MachineData) => void;
  metrics: MachineMetrics;
}
```

#### **Pattern 2: Function Parameters**

```typescript
// BEFORE:
const calculateHealth = (metrics: any): any => {
  return metrics.score * 100;
};

// AFTER:
interface Metrics {
  score: number;
  timestamp: Date;
  components: { [key: string]: number };
}

const calculateHealth = (metrics: Metrics): number => {
  return metrics.score * 100;
};
```

#### **Pattern 3: State Values**

```typescript
// BEFORE:
const [data, setData] = useState<any>(null);
const [loading, setLoading] = useState<any>(false);
const [error, setError] = useState<any>(null);

// AFTER:
interface PartData {
  id: number;
  name: string;
  price: number;
}

const [data, setData] = useState<PartData | null>(null);
const [loading, setLoading] = useState<boolean>(false);
const [error, setError] = useState<string | null>(null);
```

#### **Pattern 4: API Response Types**

```typescript
// BEFORE:
const fetchMachineData = async (id: number): Promise<any> => {
  const response = await api.get(`/machines/${id}`);
  return response.data;
};

// AFTER:
interface MachineResponse {
  id: number;
  name: string;
  status: string;
  lastMaintenance: string;
  healthScore: number;
}

const fetchMachineData = async (id: number): Promise<MachineResponse> => {
  const response = await api.get(`/machines/${id}`);
  return response.data as MachineResponse;
};
```

#### **Pattern 5: Event Handlers**

```typescript
// BEFORE:
const handleChange = (event: any) => {
  console.log(event.target.value);
};

// AFTER:
import { ChangeEvent } from 'react';

const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
  console.log(event.target.value);
};
```

#### **Pattern 6: Array Operations**

```typescript
// BEFORE:
const items: any[] = [];
const filtered = items.map((item: any) => item.id);

// AFTER:
interface Item {
  id: number;
  name: string;
}

const items: Item[] = [];
const filtered = items.map((item: Item) => item.id);
```

---

## Implementation Strategy

### **Phase 1: Unblock Immediately (5 minutes)**

1. Update `.eslintrc.json` to downgrade `any` to `warn`
2. Fix the React hooks violation in `MachineHero3D.tsx`
3. Commit and push
4. Workflow passes

```bash
# Step 1: Fix the react hooks issue
# Edit: app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx
# Move useRef call outside any conditional

# Step 2: Update eslint config
# Edit: app/frontend/.eslintrc.json
# Change @typescript-eslint/no-explicit-any from "error" to "warn"

git add .
git commit -m "fix: resolve critical hooks violation and downgrade any type warnings"
git push
```

### **Phase 2: Gradual Type Safety Improvement (Ongoing)**

Create a plan to fix high-priority files:

1. **Week 1:** Fix PDCACanbanBoard.tsx (17 errors) + RAGDocuments.tsx (10 errors)
2. **Week 2:** Fix remaining module files (AnomalieModule, CertificateModule, etc.)
3. **Week 3:** Fix component files and utilities
4. **Week 4:** Upgrade `any` rule back to `error` in ESLint config

```bash
# Example: Fix one file at a time
git checkout -b feature/fix-types-pdca

# Edit: app/frontend/src/modules/shared/machines/components/PDCACanbanBoard.tsx
# Replace all `any` with specific types

git commit -m "fix: replace any types with specific types in PDCACanbanBoard"
git push origin feature/fix-types-pdca
# Create PR and merge after review
```

---

## Workflow Configuration

The lint-frontend job is configured in `.github/workflows/source-security.yml`:

```yaml
lint-frontend:
  name: Lint Frontend (eslint)
  runs-on: ubuntu-latest
  needs: [audit-frontend]
  continue-on-error: true  # Non-blocking, but still reports errors
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "22"
    - uses: pnpm/action-setup@v4
      with:
        version: latest
    - name: Install dependencies
      working-directory: app/frontend
      run: pnpm install --frozen-lockfile
    - name: Run ESLint
      working-directory: app/frontend
      run: pnpm run lint
```

**Note:** Even though `continue-on-error: true`, the job is still showing as failed in the logs.

---

## Files Most Affected (Priority Order)

| File | Error Count | Priority |
|------|-------------|----------|
| PDCACanbanBoard.tsx | 17 | High |
| RAGDocuments.tsx | 10 | High |
| CertificateModule.tsx | 8 | Medium |
| AnomalieModule.tsx | 5+ | Medium |
| MachineDetailPage.tsx | 5 | Medium |
| MLIntelligenceTab.tsx | 4 | Medium |
| healthScore.ts | 3 | Medium |
| Others | ~78 | Low |

---

## Quick Verification

After making changes, verify locally:

```bash
cd app/frontend

# Check ESLint errors
pnpm run lint

# If using npm
npm run lint
```

The output should show significantly fewer errors after applying the fixes.

---

## Summary of Actions

### **Immediate (Today):**
1. ✅ Fix React hooks violation in `MachineHero3D.tsx` line 70
2. ✅ Downgrade `@typescript-eslint/no-explicit-any` to `warn` in `.eslintrc.json`
3. ✅ Commit and push

### **Short-term (This week):**
- Start replacing `any` types in high-priority files (PDCACanbanBoard, RAGDocuments)
- Create specific TypeScript interfaces for your data structures

### **Long-term (Ongoing):**
- Gradually replace all remaining `any` types
- Upgrade the rule back to `error` once clean
- Maintain type safety going forward

---

**Generated:** 2026-06-21  
**Workflow URL:** https://github.com/hamzAmbarki2/EAMSagemCom/actions/runs/27902676314/job/82565749522
