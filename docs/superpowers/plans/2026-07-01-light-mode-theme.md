# Light/Dark Theme Toggle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a light/dark theme toggle to the EAM app so users can switch between the current dark blue theme and Theme A (Clean White), with the toggle in the avatar dropdown menu.

**Architecture:** A new `ThemeContext` manages the active theme, applies `dark` class to `<html>`, and persists to `localStorage`. `App.tsx` wraps the tree with `ThemeProvider`. Layout shells and the Header/Sidebar are updated with `dark:` Tailwind prefixes. A CSS bulk-override block handles the long tail of hardcoded dark classes across remaining components.

**Tech Stack:** React 18 + TypeScript, Tailwind CSS (class-based dark mode via `darkMode: ["class"]`), Vite, lucide-react icons.

## Global Constraints

- Default theme MUST be `'dark'` — existing users see no change on first load.
- `localStorage` key is `'theme'` — already used by `App.tsx`; same key, now supports `'light'` | `'dark'`.
- Dark mode: zero visual regression — `.dark` CSS block unchanged.
- Toggle label: `'Mode Clair'` (when dark, clicking switches to light) / `'Mode Sombre'` (when light, clicking switches to dark).
- Theme A light mode: page bg `#f8fafc`, cards white, accent navy `#1e40af`.
- No new npm packages — only lucide-react icons already installed.
- All TypeScript: run `npx tsc --noEmit` from `app/frontend/` after every task to verify zero errors.
- Build command: `npm run build` from `app/frontend/`.

---

### Task 1: ThemeContext + App.tsx wiring

**Files:**
- Create: `app/frontend/src/contexts/ThemeContext.tsx`
- Modify: `app/frontend/src/App.tsx`

**Interfaces:**
- Produces: `ThemeProvider` (wraps the app), `useTheme()` returning `{ theme: 'light' | 'dark', toggleTheme: () => void }`
- Consumed by: Task 4 (Header uses `useTheme`)

- [ ] **Step 1: Create ThemeContext.tsx**

Create `app/frontend/src/contexts/ThemeContext.tsx` with this exact content:

```tsx
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'light' ? 'light' : 'dark';
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
```

- [ ] **Step 2: Update App.tsx**

Replace the entire content of `app/frontend/src/App.tsx` with:

```tsx
import { Toaster } from '@/components/ui/sonner';
import { Toaster as ToasterUI } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { DataSyncProvider } from './contexts/DataSyncContext';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { AppRoutes } from './app/routing';
import { ChatWidget } from './modules/shared/ChatInterface';

const queryClient = new QueryClient();

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <DataSyncProvider>
            <TooltipProvider>
              <Toaster />
              <ToasterUI />
              <BrowserRouter>
                <AppRoutes />
                <ChatWidget />
              </BrowserRouter>
            </TooltipProvider>
          </DataSyncProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
```

Changes from original: removed `useEffect` import and the hardcoded dark setup block, added `ThemeProvider` import and wrapper. `ThemeProvider` now handles `classList` and `localStorage` itself.

- [ ] **Step 3: TypeScript check**

```bash
cd app/frontend && npx tsc --noEmit
```

Expected: 0 errors. If you see `Cannot find module '@/contexts/ThemeContext'`, check the file was created at `src/contexts/ThemeContext.tsx`.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/contexts/ThemeContext.tsx app/frontend/src/App.tsx
git commit -m "feat(theme): add ThemeContext, wire ThemeProvider into App"
```

---

### Task 2: CSS variables and light-mode bulk overrides

**Files:**
- Modify: `app/frontend/src/index.css`

**Interfaces:**
- Consumes: nothing
- Produces: `:root` Theme A variables + `.glass-panel` and hardcoded-dark Tailwind class overrides for light mode

- [ ] **Step 1: Update `:root` CSS variables for Theme A**

In `app/frontend/src/index.css`, find the `:root` block inside `@layer base` (lines 19–76). Replace these specific variable lines:

```css
/* BEFORE (lines 20, 29, 30, 44, 45, 50) */
--background: 0 0% 100%;
--primary: 222.2 47.4% 11.2%;
--primary-foreground: 210 40% 98%;
--border: 214.3 31.8% 91.4%;
--input: 214.3 31.8% 91.4%;
--sidebar-background: 0 0% 98%;
```

```css
/* AFTER */
--background: 210 40% 97%;        /* #f8fafc — off-white page background */
--primary: 226 70% 40%;           /* #1e40af — navy blue accent */
--primary-foreground: 0 0% 100%;
--border: 214 32% 91%;            /* #e2e8f0 — subtle light borders */
--input: 214 32% 91%;
--sidebar-background: 0 0% 100%;  /* white sidebar */
```

Leave all other `:root` variables untouched. Leave the `.dark` block entirely untouched.

- [ ] **Step 2: Add light-mode bulk overrides**

After the closing `}` of `@layer utilities { ... }` block (after line 176 in the original file), append this new block:

```css
/* ==========================================================================
   Light-mode overrides for hardcoded dark Tailwind classes
   Covers components that use bg-slate-9xx, bg-blue-9xx, bg-slate-10xx
   directly without dark: prefix. The 6 layout files are fixed with dark:
   prefixes in their JSX; this block handles the remaining long tail.
   ========================================================================== */
:root:not(.dark) .glass-panel {
  background-color: white !important;
  border-color: #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
}

:root:not(.dark) [class*="bg-slate-9"],
:root:not(.dark) [class*="bg-slate-10"],
:root:not(.dark) [class*="bg-blue-95"],
:root:not(.dark) [class*="bg-blue-9"] {
  background-color: white !important;
  border-color: #e2e8f0 !important;
}

:root:not(.dark) [class*="text-blue-1"],
:root:not(.dark) [class*="text-blue-2"],
:root:not(.dark) [class*="text-blue-3"] {
  color: #1e293b !important;
}

:root:not(.dark) [class*="border-blue-8"] {
  border-color: #e2e8f0 !important;
}
```

- [ ] **Step 3: TypeScript check (CSS changes don't affect TS, but verify build)**

```bash
cd app/frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/index.css
git commit -m "feat(theme): Theme A CSS vars + light-mode bulk overrides"
```

---

### Task 3: Layout shells — replace hardcoded dark gradients

**Files:**
- Modify: `app/frontend/src/components/layout/Layout.tsx`
- Modify: `app/frontend/src/components/layout/TechnicianLayout.tsx`

**Interfaces:**
- Consumes: `useTheme` NOT needed here — purely className changes
- Produces: layout shells that use `bg-background` (CSS var) instead of hardcoded dark gradients

- [ ] **Step 1: Fix Layout.tsx**

In `app/frontend/src/components/layout/Layout.tsx`, replace line 15:

```tsx
// BEFORE:
<div className="min-h-screen bg-gradient-to-b from-slate-950 via-blue-950 to-slate-950">
  <div className="fixed inset-0 mesh-gradient opacity-30 -z-10" />
```

```tsx
// AFTER:
<div className="min-h-screen bg-background">
  <div className="fixed inset-0 mesh-gradient opacity-30 -z-10 hidden dark:block" />
```

Two changes: `bg-background` (resolves to `#f8fafc` in light, dark in `.dark`), and `hidden dark:block` on the mesh-gradient overlay (the overlay uses hardcoded dark HSL values that look wrong on white).

- [ ] **Step 2: Fix TechnicianLayout.tsx**

In `app/frontend/src/components/layout/TechnicianLayout.tsx`, replace line 33:

```tsx
// BEFORE:
<div className="min-h-screen bg-gradient-to-b from-slate-950 via-blue-950 to-slate-950">
  <div className="fixed inset-0 mesh-gradient opacity-30 -z-10" />
```

```tsx
// AFTER:
<div className="min-h-screen bg-background">
  <div className="fixed inset-0 mesh-gradient opacity-30 -z-10 hidden dark:block" />
```

Identical fix as Layout.tsx.

- [ ] **Step 3: TypeScript check**

```bash
cd app/frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/layout/Layout.tsx app/frontend/src/components/layout/TechnicianLayout.tsx
git commit -m "feat(theme): layout shells use bg-background, hide dark mesh overlay in light mode"
```

---

### Task 4: Header — theme toggle + dark: className fixes

**Files:**
- Modify: `app/frontend/src/components/layout/Header.tsx`

**Interfaces:**
- Consumes: `useTheme` from `@/contexts/ThemeContext` (Task 1)
- Produces: toggle item in avatar dropdown; header bg/text/border adapts to theme

- [ ] **Step 1: Add useTheme import and Sun/Moon icons**

In `app/frontend/src/components/layout/Header.tsx`, update the imports block.

Replace:
```tsx
import { Bell, LogOut, User, Menu, PanelLeftClose } from 'lucide-react';
import { useSidebar } from '@/hooks/useSidebar';
```

With:
```tsx
import { Bell, LogOut, User, Menu, PanelLeftClose, Sun, Moon } from 'lucide-react';
import { useSidebar } from '@/hooks/useSidebar';
import { useTheme } from '@/contexts/ThemeContext';
```

- [ ] **Step 2: Destructure useTheme inside component**

Inside `export default function Header()`, after the existing `const { collapsed, toggle } = useSidebar();` line, add:

```tsx
const { theme, toggleTheme } = useTheme();
```

- [ ] **Step 3: Fix header element className**

Replace line 168:
```tsx
// BEFORE:
<header className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-900 border-b border-blue-800 sticky top-0 z-50 backdrop-blur-md">
```

```tsx
// AFTER:
<header className="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:via-blue-900 dark:to-slate-900 border-b border-slate-200 dark:border-blue-800 sticky top-0 z-50 backdrop-blur-md">
```

- [ ] **Step 4: Fix sidebar toggle button**

Replace the Button at lines 172–180:
```tsx
// BEFORE:
className="text-blue-100 hover:text-white hover:bg-blue-800/40"
```

```tsx
// AFTER:
className="text-slate-600 dark:text-blue-100 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-blue-800/40"
```

- [ ] **Step 5: Fix app title text color**

Replace line 187:
```tsx
// BEFORE:
<h1 className="text-xl font-bold text-white">Asset Management</h1>
```

```tsx
// AFTER:
<h1 className="text-xl font-bold text-slate-900 dark:text-white">Asset Management</h1>
```

- [ ] **Step 6: Fix role badge**

Replace lines 192–194:
```tsx
// BEFORE:
<span className="text-sm text-blue-100 bg-blue-600/30 border border-blue-500/30 px-3 py-1 rounded-full">
```

```tsx
// AFTER:
<span className="text-sm text-slate-700 dark:text-blue-100 bg-blue-100 dark:bg-blue-600/30 border border-blue-200 dark:border-blue-500/30 px-3 py-1 rounded-full">
```

- [ ] **Step 7: Fix notification dropdown background**

Replace line 208 (DropdownMenuContent for Bell):
```tsx
// BEFORE:
<DropdownMenuContent align="end" className="bg-slate-900 border-blue-800 w-80">
```

```tsx
// AFTER:
<DropdownMenuContent align="end" className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-80">
```

- [ ] **Step 8: Fix unread notification item highlight**

Replace line 225 (DropdownMenuItem inside notifications map):
```tsx
// BEFORE:
className={`flex flex-col items-start p-4 cursor-pointer ${!notif.lu ? 'bg-blue-900/30' : ''}`}
```

```tsx
// AFTER:
className={`flex flex-col items-start p-4 cursor-pointer ${!notif.lu ? 'bg-blue-50 dark:bg-blue-900/30' : ''}`}
```

- [ ] **Step 9: Fix avatar dropdown background**

Replace line 249 (DropdownMenuContent for user avatar):
```tsx
// BEFORE:
<DropdownMenuContent align="end" className="bg-slate-900 border-blue-800 w-56">
```

```tsx
// AFTER:
<DropdownMenuContent align="end" className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-56">
```

- [ ] **Step 10: Fix email text color in dropdown**

Replace line 254:
```tsx
// BEFORE:
<p className="text-xs text-blue-300">{user.email}</p>
```

```tsx
// AFTER:
<p className="text-xs text-blue-600 dark:text-blue-300">{user.email}</p>
```

- [ ] **Step 11: Add theme toggle item + fix logout item**

Replace lines 258–262 (the DropdownMenuSeparator + logout item):
```tsx
// BEFORE:
<DropdownMenuSeparator />
<DropdownMenuItem onClick={handleLogout} className="text-blue-100 focus:bg-blue-800/40">
  <LogOut className="mr-2 h-4 w-4" />
  <span>Log out</span>
</DropdownMenuItem>
```

```tsx
// AFTER:
<DropdownMenuItem
  onClick={toggleTheme}
  className="text-slate-700 dark:text-blue-100 focus:bg-slate-100 dark:focus:bg-blue-800/40 cursor-pointer"
>
  {theme === 'dark' ? (
    <><Sun className="mr-2 h-4 w-4" /><span>Mode Clair</span></>
  ) : (
    <><Moon className="mr-2 h-4 w-4" /><span>Mode Sombre</span></>
  )}
</DropdownMenuItem>
<DropdownMenuSeparator />
<DropdownMenuItem onClick={handleLogout} className="text-slate-700 dark:text-blue-100 focus:bg-slate-100 dark:focus:bg-blue-800/40">
  <LogOut className="mr-2 h-4 w-4" />
  <span>Log out</span>
</DropdownMenuItem>
```

- [ ] **Step 12: TypeScript check**

```bash
cd app/frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 13: Commit**

```bash
git add app/frontend/src/components/layout/Header.tsx
git commit -m "feat(theme): header theme-aware classNames + toggle in avatar dropdown"
```

---

### Task 5: Sidebar — dark: className fixes

**Files:**
- Modify: `app/frontend/src/components/layout/Sidebar.tsx`

**Interfaces:**
- Consumes: nothing (purely className changes)
- Produces: sidebar that renders white in light mode, dark blue in dark mode

- [ ] **Step 1: Fix sidebar card wrapper**

In `app/frontend/src/components/layout/Sidebar.tsx`, replace line 200:

```tsx
// BEFORE:
className="flex-1 flex flex-col min-h-0 bg-gradient-to-b from-slate-900/95 to-blue-950/95 m-3 rounded-2xl shadow-2xl border border-blue-800/30 overflow-hidden transition-all duration-500 backdrop-blur-md"
```

```tsx
// AFTER:
className="flex-1 flex flex-col min-h-0 bg-white dark:bg-gradient-to-b dark:from-slate-900/95 dark:to-blue-950/95 m-3 rounded-2xl shadow-2xl border border-slate-200 dark:border-blue-800/30 overflow-hidden transition-all duration-500 backdrop-blur-md"
```

- [ ] **Step 2: Fix section heading**

Replace line 203:
```tsx
// BEFORE:
className="text-[10px] font-bold text-blue-400/60 uppercase tracking-[0.2em] opacity-80"
```

```tsx
// AFTER:
className="text-[10px] font-bold text-slate-400 dark:text-blue-400/60 uppercase tracking-[0.2em] opacity-80"
```

- [ ] **Step 3: Fix collapse button**

Replace lines 210–213:
```tsx
// BEFORE:
className="p-1 rounded-md text-blue-300/70 hover:text-blue-100 hover:bg-blue-800/40 transition-colors"
```

```tsx
// AFTER:
className="p-1 rounded-md text-slate-400 dark:text-blue-300/70 hover:text-slate-700 dark:hover:text-blue-100 hover:bg-slate-100 dark:hover:bg-blue-800/40 transition-colors"
```

- [ ] **Step 4: Fix active nav link class**

In the `cn(...)` call for `<Link>` (lines 224–229), replace the active branch:

```tsx
// BEFORE (active branch):
'bg-blue-600/40 text-blue-50 border-l-2 border-blue-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
```

```tsx
// AFTER (active branch):
'bg-blue-100 dark:bg-blue-600/40 text-blue-700 dark:text-blue-50 border-l-2 border-blue-500 dark:border-blue-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
```

- [ ] **Step 5: Fix inactive nav link class**

Replace the inactive branch in the same `cn(...)`:

```tsx
// BEFORE (inactive branch):
'text-blue-200/70 hover:bg-blue-800/30 hover:text-blue-50'
```

```tsx
// AFTER (inactive branch):
'text-slate-600 dark:text-blue-200/70 hover:bg-slate-100 dark:hover:bg-blue-800/30 hover:text-slate-900 dark:hover:text-blue-50'
```

- [ ] **Step 6: Fix nav icon className**

Replace lines 234–237 (the `cn(...)` on `<item.icon>`):

```tsx
// BEFORE:
className={cn(
  isActive ? 'text-white scale-110' : 'text-blue-400/70 group-hover:text-blue-200',
  'mr-3 flex-shrink-0 h-5 w-5 transition-all duration-300 group-hover:rotate-3'
)}
```

```tsx
// AFTER:
className={cn(
  isActive
    ? 'text-blue-600 dark:text-white scale-110'
    : 'text-slate-400 dark:text-blue-400/70 group-hover:text-slate-700 dark:group-hover:text-blue-200',
  'mr-3 flex-shrink-0 h-5 w-5 transition-all duration-300 group-hover:rotate-3'
)}
```

- [ ] **Step 7: TypeScript check**

```bash
cd app/frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 8: Build check**

```bash
cd app/frontend && npm run build
```

Expected: build succeeds, no TypeScript errors, no missing imports. Chunk size warnings are OK.

- [ ] **Step 9: Commit**

```bash
git add app/frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(theme): sidebar theme-aware classNames for light/dark modes"
```

---

## Manual Smoke Test (run after all 5 tasks)

Start the dev server:
```bash
make up
# or: cd app/frontend && npm run dev
```

Navigate to `http://localhost:3000`. Log in as any user.

**Dark mode (default):**
1. Page loads → dark blue theme, identical to before all changes. ✓
2. Open avatar dropdown (top-right) → see "Mode Clair" with Sun icon above separator line. ✓
3. `localStorage['theme']` === `'dark'`. ✓

**Switch to light:**
4. Click "Mode Clair" → page instantly switches to white/light theme. ✓
5. Header turns white with dark text, navy border. ✓
6. Sidebar card turns white with slate text, blue active highlight. ✓
7. Page background is `#f8fafc` off-white. ✓
8. Avatar dropdown now shows "Mode Sombre" with Moon icon. ✓
9. `localStorage['theme']` === `'light'`. ✓

**Persistence:**
10. Reload page → light mode persists. ✓

**Switch back:**
11. Click "Mode Sombre" → returns to dark theme instantly. ✓
12. Reload → dark persists. ✓

**No regression check:**
13. Navigate to Planning, Work Orders, ML Dashboard pages in dark mode — identical to pre-change. ✓
