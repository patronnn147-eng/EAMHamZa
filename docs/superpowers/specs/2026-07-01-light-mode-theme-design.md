# Light/Dark Theme Toggle — Design Spec

## Choices

- **Theme style:** Theme A — Clean White (white cards, `#f8fafc` page bg, `#1e40af` navy header/accent)
- **Toggle placement:** Inside avatar dropdown menu in `Header.tsx`
- **Default theme:** `dark` (preserves current behavior for existing users)

---

## Architecture

### ThemeContext (`src/contexts/ThemeContext.tsx`)

```tsx
interface ThemeContextValue {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}
```

- `localStorage` key: `'theme'` (already written by `App.tsx` — same key, now with `'light'` | `'dark'` values)
- On mount: reads localStorage, falls back to `'dark'`
- Applies: `document.documentElement.classList.toggle('dark', theme === 'dark')`
- Export: `ThemeContext`, `ThemeProvider`, `useTheme`

### App.tsx

Remove:
```tsx
document.documentElement.classList.add('dark');
localStorage.setItem('theme', 'dark');
```

Add: wrap router tree with `<ThemeProvider>`. ThemeProvider handles the `classList` application itself on mount/change.

### index.css — `:root` (light mode)

`:root` already has light vars but `--background` is pure white and `--primary` is very dark navy. Update to Theme A:

```css
:root {
  /* Theme A overrides */
  --background: 210 40% 97%;          /* #f8fafc — off-white page bg */
  --card: 0 0% 100%;                  /* white cards */
  --primary: 226 70% 40%;             /* #1e40af navy accent */
  --primary-foreground: 0 0% 100%;
  --border: 214 32% 91%;              /* #e2e8f0 subtle borders */
  --input: 214 32% 91%;
  --sidebar-background: 0 0% 100%;
  /* All other :root vars stay as-is — already suitable for light */
}
```

`.dark` block — **no changes**.

### index.css — Light-mode bulk overrides

Layout/Header/Sidebar have their own semantic className fixes (see below). For the remaining 120+ component files with hardcoded dark Tailwind classes, add light-mode CSS overrides:

```css
/* Light mode: override hardcoded dark Tailwind containers */
:root:not(.dark) .glass-panel,
:root:not(.dark) [class*="bg-slate-9"],
:root:not(.dark) [class*="bg-slate-8"],
:root:not(.dark) [class*="bg-blue-95"],
:root:not(.dark) [class*="bg-blue-9"],
:root:not(.dark) [class*="bg-slate-10"] {
  background-color: white !important;
  border-color: #e2e8f0 !important;
}

:root:not(.dark) [class*="text-blue-1"],
:root:not(.dark) [class*="text-blue-2"],
:root:not(.dark) [class*="text-blue-3"] {
  color: #1e293b !important;
}

:root:not(.dark) .glass-panel {
  box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}
```

These use CSS attribute substring selectors on Tailwind class names — broad coverage without touching individual component files.

### Header.tsx

**Background fix** — replace hardcoded dark gradient with theme-aware:
```tsx
// Old:
className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-900 border-b border-blue-800 ..."

// New (use dark: prefix for dark-only styles):
className="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:via-blue-900 dark:to-slate-900 border-b border-slate-200 dark:border-blue-800 ..."
```

Light mode header background: white with subtle bottom border. Title text becomes dark.

**Title text fix:**
```tsx
// Old:
<h1 className="text-xl font-bold text-white">Asset Management</h1>

// New:
<h1 className="text-xl font-bold text-white dark:text-white text-slate-900">Asset Management</h1>
```

Wait — `dark:` prefix takes precedence when `.dark` is on `<html>`. So: `className="text-xl font-bold text-slate-900 dark:text-white"`.

**Toggle in avatar dropdown** — add after `DropdownMenuSeparator`, before logout:
```tsx
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

// Inside component:
const { theme, toggleTheme } = useTheme();

// In DropdownMenuContent:
<DropdownMenuItem onClick={toggleTheme} className="text-blue-100 focus:bg-blue-800/40 dark:text-blue-100 text-slate-700">
  {theme === 'dark'
    ? <><Sun className="mr-2 h-4 w-4" /><span>Mode Clair</span></>
    : <><Moon className="mr-2 h-4 w-4" /><span>Mode Sombre</span></>
  }
</DropdownMenuItem>
<DropdownMenuSeparator />
```

Place the toggle item **above** the logout item.

**Notification dropdown bg fix:**
```tsx
// Old:
className="bg-slate-900 border-blue-800 w-80"

// New:
className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-80"
```

**User dropdown bg fix** (same `DropdownMenuContent`):
```tsx
// Old:
className="bg-slate-900 border-blue-800 w-56"

// New:
className="bg-white dark:bg-slate-900 border-slate-200 dark:border-blue-800 w-56"
```

**Sidebar toggle button fix:**
```tsx
// Old:
className="text-blue-100 hover:text-white hover:bg-blue-800/40"

// New:
className="text-slate-600 dark:text-blue-100 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-blue-800/40"
```

**Role badge fix:**
```tsx
// Old:
className="text-sm text-blue-100 bg-blue-600/30 border border-blue-500/30 ..."

// New:
className="text-sm text-slate-700 dark:text-blue-100 bg-blue-100 dark:bg-blue-600/30 border border-blue-200 dark:border-blue-500/30 ..."
```

### Layout.tsx

```tsx
// Old:
className="min-h-screen bg-gradient-to-b from-slate-950 via-blue-950 to-slate-950"

// New:
className="min-h-screen bg-background"
```

`bg-background` uses `hsl(var(--background))` — resolves to `#f8fafc` in light, dark blue in `.dark`.

### Sidebar.tsx

Sidebar card wrapper:
```tsx
// Old:
className="flex-1 flex flex-col min-h-0 bg-gradient-to-b from-slate-900/95 to-blue-950/95 m-3 rounded-2xl shadow-2xl border border-blue-800/30 ..."

// New:
className="flex-1 flex flex-col min-h-0 bg-white dark:bg-gradient-to-b dark:from-slate-900/95 dark:to-blue-950/95 m-3 rounded-2xl shadow-2xl border border-slate-200 dark:border-blue-800/30 ..."
```

Section heading:
```tsx
// Old:
className="text-[10px] font-bold text-blue-400/60 ..."

// New:
className="text-[10px] font-bold text-slate-400 dark:text-blue-400/60 ..."
```

Nav links:
```tsx
// Active link — Old:
'bg-blue-600/40 text-blue-50 border-l-2 border-blue-400 ...'

// Active link — New:
'bg-blue-600/20 dark:bg-blue-600/40 text-blue-700 dark:text-blue-50 border-l-2 border-blue-500 dark:border-blue-400 ...'

// Inactive link — Old:
'text-blue-200/70 hover:bg-blue-800/30 hover:text-blue-50'

// Inactive link — New:
'text-slate-600 dark:text-blue-200/70 hover:bg-slate-100 dark:hover:bg-blue-800/30 hover:text-slate-900 dark:hover:text-blue-50'
```

Nav icon:
```tsx
// Old:
isActive ? 'text-white scale-110' : 'text-blue-400/70 group-hover:text-blue-200'

// New:
isActive ? 'text-blue-600 dark:text-white scale-110' : 'text-slate-400 dark:text-blue-400/70 group-hover:text-slate-700 dark:group-hover:text-blue-200'
```

Sidebar collapse button:
```tsx
// Old:
className="p-1 rounded-md text-blue-300/70 hover:text-blue-100 hover:bg-blue-800/40 ..."

// New:
className="p-1 rounded-md text-slate-400 dark:text-blue-300/70 hover:text-slate-700 dark:hover:text-blue-100 hover:bg-slate-100 dark:hover:bg-blue-800/40 ..."
```

---

## File Map

| File | Action | Change |
|------|--------|--------|
| `src/contexts/ThemeContext.tsx` | **Create** | ThemeContext, ThemeProvider, useTheme |
| `src/App.tsx` | **Modify** | Remove hardcoded dark; wrap with ThemeProvider |
| `src/index.css` | **Modify** | Update `:root` Theme A vars; add light-mode bulk overrides |
| `src/components/layout/Header.tsx` | **Modify** | Theme toggle in dropdown; dark: prefixed classNames |
| `src/components/layout/Layout.tsx` | **Modify** | `bg-background` replaces hardcoded gradient |
| `src/components/layout/Sidebar.tsx` | **Modify** | dark: prefixed classNames throughout |
| `src/components/layout/TechnicianLayout.tsx` | **Modify** | `bg-background` replaces hardcoded gradient (same fix as Layout.tsx) |

---

## Behaviour

- App loads → reads `localStorage['theme']` → defaults to `'dark'` if unset
- User opens avatar dropdown → clicks "Mode Clair" → theme switches to light instantly, `localStorage` updated
- Page refresh → persists to chosen theme
- Dark mode: identical to current app (no regression)
- Light mode: Theme A (white/navy) with ~80% coverage from direct fixes + bulk CSS overrides for long tail

---

## Out of Scope

- Per-page or per-component theme overrides
- System-preference auto-detection (`prefers-color-scheme`)
- Animated theme transition effects
- Any changes to the ML, backend, or notebook code
