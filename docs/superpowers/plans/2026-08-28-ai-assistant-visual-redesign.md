# AI Assistant Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the AI Assistant chat UI (`ChatPage` full-page screen and the floating `ChatWidget`) to use the app's existing but unused "premium" gradient/glass design tokens, remove the exposed "Groq" vendor name, translate hardcoded English copy to French, and stop listing abandoned empty conversations in the sidebar.

**Architecture:** Single-file change to `app/frontend/src/modules/shared/ChatInterface.tsx`. One small pure helper function (`filterVisibleSessions`) gets extracted and unit-tested; everything else is `className`/JSX/copy edits — no new components, no API/backend changes.

**Tech Stack:** React + TypeScript, Tailwind CSS (existing custom utilities in `app/frontend/src/index.css`), shadcn/ui components, Vitest for the one unit test.

## Global Constraints

- No new CSS — reuse `bg-gradient-premium`, `.glass-panel`, `.glass-panel-hover`, `.input-glass`, `.animate-premium-fade-in`, and the `--premium-indigo/purple/rose` CSS vars already defined in `app/frontend/src/index.css`.
- No "Groq" (or any LLM vendor name) may appear anywhere in the rendered UI.
- All example-question / label copy must be French, matching the rest of the page.
- No backend/API changes. No changes to `RenderedMessage`'s table/list rendering logic, the sources panel, tool-call badges, or the doc-upload dialog.
- Sessions with `message_count === 0` are hidden from the sidebar list unless they are the currently-selected session.
- Follow the codebase's existing convention for these tokens: `.glass-panel`/`.input-glass` are applied to raw `<div>`/`<input>` elements (see `app/frontend/src/modules/shared/AuditLogViewer.tsx`), not layered onto shadcn `<Card>`/`<Input>` components, to avoid CSS cascade conflicts between the custom utility and the shadcn component's own background/border classes.
- Reference design: `docs/superpowers/specs/2026-08-28-ai-assistant-visual-redesign-design.md`.

---

### Task 1: Extract and test `filterVisibleSessions` helper

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (add exported function near the top, after the `ChatSessionSummary` interface at line 77)
- Create: `app/frontend/src/modules/shared/ChatInterface.helpers.test.ts`

**Interfaces:**
- Produces: `filterVisibleSessions(sessions: ChatSessionSummary[], currentSessionId: string | null): ChatSessionSummary[]` — used by Task 2 to filter the sidebar's rendered list.

- [ ] **Step 1: Write the failing test**

Create `app/frontend/src/modules/shared/ChatInterface.helpers.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { filterVisibleSessions } from './ChatInterface';

const session = (id: string, message_count: number) => ({
  id,
  title: id,
  message_count,
});

describe('filterVisibleSessions', () => {
  it('keeps sessions that have at least one message', () => {
    const sessions = [session('a', 3), session('b', 1)];
    expect(filterVisibleSessions(sessions, null)).toEqual(sessions);
  });

  it('drops empty sessions that are not the current selection', () => {
    const sessions = [session('a', 3), session('b', 0)];
    expect(filterVisibleSessions(sessions, null)).toEqual([session('a', 3)]);
  });

  it('keeps an empty session when it is the current selection', () => {
    const sessions = [session('a', 3), session('b', 0)];
    expect(filterVisibleSessions(sessions, 'b')).toEqual(sessions);
  });

  it('keeps an empty session when another empty one is selected (only the selected one survives)', () => {
    const sessions = [session('a', 0), session('b', 0)];
    expect(filterVisibleSessions(sessions, 'b')).toEqual([session('b', 0)]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `app/frontend/`): `npx vitest run src/modules/shared/ChatInterface.helpers.test.ts`
Expected: FAIL — `filterVisibleSessions` is not exported from `./ChatInterface`.

- [ ] **Step 3: Add the function**

In `app/frontend/src/modules/shared/ChatInterface.tsx`, immediately after the `ChatSessionSummary` interface (after line 77, before the `// ─── Utility: parse markdown tables` comment), add:

```ts
export function filterVisibleSessions(
  sessions: ChatSessionSummary[],
  currentSessionId: string | null
): ChatSessionSummary[] {
  return sessions.filter((s) => s.message_count > 0 || s.id === currentSessionId);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/modules/shared/ChatInterface.helpers.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx app/frontend/src/modules/shared/ChatInterface.helpers.test.ts
git commit -m "feat(chat): add filterVisibleSessions helper to hide abandoned empty sessions"
```

---

### Task 2: Wire the filter into the sidebar + restyle it

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatPage` component, lines ~824, ~850-859, ~864-897)

**Interfaces:**
- Consumes: `filterVisibleSessions` from Task 1.

- [ ] **Step 1: Compute the visible list before the render return**

Find (around line 823-824):

```tsx
  return (
    <div className="space-y-6">
```

Replace with:

```tsx
  const visibleSessions = filterVisibleSessions(sessions, currentSessionId);

  return (
    <div className="space-y-6">
```

- [ ] **Step 2: Use `visibleSessions` in the sidebar list**

Find (around line 864-869):

```tsx
                {sessions.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-6">
                    Aucune conversation.
                  </p>
                )}
                {sessions.map((s) => {
                  const active = s.id === currentSessionId;
                  return (
```

Replace with:

```tsx
                {visibleSessions.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-6">
                    Aucune conversation.
                  </p>
                )}
                {visibleSessions.map((s) => {
                  const active = s.id === currentSessionId;
                  return (
```

- [ ] **Step 3: Restyle the "Nouveau" button with the gradient**

Find (around line 850-859):

```tsx
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1"
              onClick={() => createNewSession({ select: true })}
              title="Nouvelle conversation"
            >
              <Plus className="h-3.5 w-3.5" />
              Nouveau
            </Button>
```

Replace with:

```tsx
            <Button
              size="sm"
              className="h-8 gap-1 bg-gradient-premium text-white border-0 hover:opacity-90 transition-opacity"
              onClick={() => createNewSession({ select: true })}
              title="Nouvelle conversation"
            >
              <Plus className="h-3.5 w-3.5" />
              Nouveau
            </Button>
```

- [ ] **Step 4: Restyle the active-session row with a gradient accent bar**

Find (around line 872-889), the row `className` and the opening of its children:

```tsx
                    <div
                      key={s.id}
                      className={`group flex items-center gap-1 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors ${
                        active
                          ? 'bg-primary/10 text-foreground border border-primary/30'
                          : 'hover:bg-muted/60'
                      }`}
                      role="button"
                      tabIndex={0}
                      onClick={() => selectSession(s.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          selectSession(s.id);
                        }
                      }}
                    >
                      <MessageSquare className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
```

Replace with:

```tsx
                    <div
                      key={s.id}
                      className={`group relative flex items-center gap-1 rounded-md px-2 py-2 pl-3 text-sm cursor-pointer transition-colors overflow-hidden ${
                        active ? 'bg-white/[0.04] text-foreground' : 'hover:bg-muted/60'
                      }`}
                      role="button"
                      tabIndex={0}
                      onClick={() => selectSession(s.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          selectSession(s.id);
                        }
                      }}
                    >
                      {active && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-premium rounded-full shadow-[0_0_15px_rgba(139,92,246,0.8)]" />
                      )}
                      <MessageSquare className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
```

(This accent-bar pattern matches the existing active-nav-item indicator in `app/frontend/src/components/layout/Sidebar.tsx:236`.)

- [ ] **Step 5: Manual verification**

Start the dev server (from `app/frontend/`, backend already running via `make up` on `localhost:8000`):

```bash
VITE_API_BASE_URL=http://localhost:8000 VITE_PORT=5173 npm run dev
```

Open `http://localhost:5173`, log in (hamza.mbarki2002@gmail.com / hA123456), navigate to the Assistant IA page. Confirm: "Nouveau" button has a purple/indigo→rose gradient fill; clicking it creates and selects a session; no other empty sessions are listed; the active session shows a glowing gradient bar on its left edge.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "feat(chat): restyle conversations sidebar with premium gradient + hide empty sessions"
```

---

### Task 3: Header — remove Groq branding, add gradient icon

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatPage` component, lines ~826-840)

- [ ] **Step 1: Replace the header block**

Find (around line 826-840):

```tsx
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            Assistant IA
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Powered by Groq — interrogez vos machines, ordres de travail, alertes et plannings
          </p>
        </div>
        <Badge variant="outline" className="text-xs">
          <Bot className="h-3 w-3 mr-1" />
          Groq LLM
        </Badge>
      </div>
```

Replace with:

```tsx
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-premium">
              <Sparkles className="h-4 w-4 text-white" />
            </span>
            Assistant IA
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Interrogez vos machines, ordres de travail, alertes et plannings en langage naturel
          </p>
        </div>
        <Badge variant="outline" className="text-xs gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gradient-premium opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-gradient-premium" />
          </span>
          Assistant actif
        </Badge>
      </div>
```

- [ ] **Step 2: Manual verification**

Reload `http://localhost:5173` (Assistant IA page). Confirm the word "Groq" is gone from the header entirely (title, subtitle, badge), the badge now reads "Assistant actif" with a small pulsing dot, and the sparkle icon sits in a gradient-filled rounded square.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "fix(chat): remove Groq vendor branding from Assistant IA header"
```

---

### Task 4: Message list restyle (bubbles, avatars, empty state, loading dots)

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatPage` component, lines ~939-1018)

- [ ] **Step 1: Empty-state icon**

Find (around line 939-941):

```tsx
                    <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
                      <Sparkles className="h-8 w-8 text-primary" />
                    </div>
```

Replace with:

```tsx
                    <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-[radial-gradient(circle,hsl(var(--premium-indigo)/0.18),hsl(var(--premium-purple)/0.08)_70%)] shadow-[0_0_30px_rgba(139,92,246,0.15)] mb-4">
                      <Sparkles className="h-8 w-8 text-[hsl(var(--premium-indigo))]" />
                    </div>
```

- [ ] **Step 2: User message bubble + avatar**

Find (around line 959-967):

```tsx
                      <div className="flex justify-end">
                        <div className="flex items-end gap-2 max-w-[75%]">
                          <div className="bg-primary text-primary-foreground px-4 py-3 rounded-2xl rounded-br-md text-sm">
                            {msg.content}
                          </div>
                          <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                            <User className="h-4 w-4 text-primary-foreground" />
                          </div>
                        </div>
                      </div>
```

Replace with:

```tsx
                      <div className="flex justify-end">
                        <div className="flex items-end gap-2 max-w-[75%]">
                          <div className="bg-gradient-premium text-white px-4 py-3 rounded-2xl rounded-br-md text-sm animate-premium-fade-in">
                            {msg.content}
                          </div>
                          <div className="h-9 w-9 rounded-full bg-gradient-premium flex items-center justify-center flex-shrink-0">
                            <User className="h-4 w-4 text-white" />
                          </div>
                        </div>
                      </div>
```

- [ ] **Step 3: Assistant message bubble + avatar**

Find (around line 970-974):

```tsx
                      <div className="flex items-end gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center flex-shrink-0">
                          <Bot className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 bg-muted/60 backdrop-blur-sm px-5 py-4 rounded-2xl rounded-bl-md border min-w-0">
```

Replace with:

```tsx
                      <div className="flex items-end gap-3 animate-premium-fade-in">
                        <div className="h-10 w-10 rounded-full bg-[radial-gradient(circle,hsl(var(--premium-indigo)/0.35),hsl(var(--premium-purple)/0.2)_70%)] flex items-center justify-center flex-shrink-0">
                          <Bot className="h-5 w-5 text-[hsl(var(--premium-indigo))]" />
                        </div>
                        <div className="flex-1 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-[rgba(0,255,242,0.25)] hover:shadow-[0_0_20px_rgba(0,255,242,0.1)] backdrop-blur-[12px] transition-all px-5 py-4 rounded-2xl rounded-bl-md min-w-0">
```

- [ ] **Step 4: Loading indicator**

Find (around line 1004-1018):

```tsx
                  <div className="flex items-center gap-3 pl-13">
                    <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                      <Bot className="h-5 w-5 text-muted-foreground animate-pulse" />
                    </div>
                    <div className="bg-muted/60 px-4 py-3 rounded-2xl rounded-bl-md border">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                        <span className="text-sm text-muted-foreground">L'IA réfléchit...</span>
                      </div>
                    </div>
                  </div>
```

Replace with:

```tsx
                  <div className="flex items-center gap-3 pl-13">
                    <div className="h-10 w-10 rounded-full bg-[radial-gradient(circle,hsl(var(--premium-indigo)/0.35),hsl(var(--premium-purple)/0.2)_70%)] flex items-center justify-center">
                      <Bot className="h-5 w-5 text-[hsl(var(--premium-indigo))] animate-pulse" />
                    </div>
                    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-[12px] px-4 py-3 rounded-2xl rounded-bl-md">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="h-2 w-2 rounded-full bg-[hsl(var(--premium-indigo))] animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="h-2 w-2 rounded-full bg-[hsl(var(--premium-purple))] animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="h-2 w-2 rounded-full bg-[hsl(var(--premium-rose))] animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                        <span className="text-sm text-muted-foreground">L'IA réfléchit...</span>
                      </div>
                    </div>
                  </div>
```

- [ ] **Step 5: Manual verification**

Reload the Assistant IA page. Send a message (e.g. "Alertes critiques" from the empty-state suggestions). Confirm: the empty-state icon has a soft purple glow; your message bubble is a solid indigo→purple→rose gradient; the assistant's reply bubble has a subtle glass look and glows faintly on hover; the "L'IA réfléchit..." dots cycle indigo→purple→rose while loading.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "feat(chat): restyle message bubbles, avatars and loading indicator with premium tokens"
```

---

### Task 5: Input bar restyle

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatPage` component, lines ~1026-1057)

- [ ] **Step 1: Replace the input bar**

Find (around line 1026-1057):

```tsx
            <div className="p-4 border-t bg-muted/30">
              <form
                onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
                className="flex gap-3"
              >
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  className="h-12 w-12 flex-shrink-0"
                  onClick={() => setShowDocUpload(true)}
                  title="Importer un document dans la base RAG"
                >
                  <Plus className="h-5 w-5" />
                </Button>
                <Input
                  placeholder="Tapez votre question... (ex: Machines en panne dans Zone A)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="text-base h-12"
                />
                <Button
                  type="submit"
                  size="lg"
                  disabled={loading || !input.trim()}
                  className="h-12 px-6"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </Button>
              </form>
            </div>
```

Replace with:

```tsx
            <div className="p-4 border-t border-white/[0.08] bg-transparent">
              <form
                onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
                className="flex gap-3"
              >
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  className="h-12 w-12 flex-shrink-0 border-white/[0.12] hover:border-[rgba(0,255,242,0.4)]"
                  onClick={() => setShowDocUpload(true)}
                  title="Importer un document dans la base RAG"
                >
                  <Plus className="h-5 w-5" />
                </Button>
                <input
                  placeholder="Tapez votre question... (ex: Machines en panne dans Zone A)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="input-glass flex-1 text-base h-12 px-4"
                />
                <Button
                  type="submit"
                  size="lg"
                  disabled={loading || !input.trim()}
                  className="h-12 px-6 bg-gradient-premium text-white border-0 hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </Button>
              </form>
            </div>
```

(Swapped the shadcn `<Input>` for a raw `<input>` styled with `.input-glass`, matching the established pattern in `AuditLogViewer.tsx`. The `Input` import is removed in Task 7 once its last usage in `ChatWidget` is also replaced.)

- [ ] **Step 2: Manual verification**

Reload the Assistant IA page. Confirm the text field has a dark glass look (not the default shadcn input border), focuses with a cyan ring, and the send button is gradient-filled with a disabled/faded state when empty.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "feat(chat): restyle Assistant IA input bar with glass input and gradient send button"
```

---

### Task 6: Right sidebar — translate copy, restyle hover

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatPage` component, lines ~1117-1150)

- [ ] **Step 1: Translate the example-questions array**

Find (around line 1117-1126):

```tsx
              {[
                'Show machines in Zone A',
                'Show critical alerts',
                'Pending work orders',
                'Show me interventions',
                'Show plannings for this week',
                'Machines needing repair',
                'Show high priority alerts',
                'Work orders by CHEFTECH',
              ].map((s, i) => (
```

Replace with:

```tsx
              {[
                'Machines en Zone A',
                'Alertes critiques',
                'Ordres de travail en attente',
                'Voir les interventions',
                'Plannings de la semaine',
                'Machines à réparer',
                'Alertes haute priorité',
                'Ordres de travail par CHEFTECH',
              ].map((s, i) => (
```

- [ ] **Step 2: Restyle the button hover**

Find (around line 1127-1136):

```tsx
                <Button
                  key={i}
                  variant="ghost"
                  className="w-full justify-start text-left h-auto py-2.5 text-sm text-muted-foreground hover:text-foreground"
                  onClick={() => handleSubmit(s)}
                >
```

Replace with:

```tsx
                <Button
                  key={i}
                  variant="ghost"
                  className="w-full justify-start text-left h-auto py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-white/[0.04] border border-transparent hover:border-[rgba(139,92,246,0.3)] transition-colors"
                  onClick={() => handleSubmit(s)}
                >
```

- [ ] **Step 3: Translate "Domains supported" section**

Find (around line 1139-1150):

```tsx
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Domains supported
              </p>
              <div className="flex flex-wrap gap-1.5">
                {['Machines', 'Work Orders', 'Alerts', 'Interventions', 'Plannings'].map((d) => (
```

Replace with:

```tsx
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Domaines couverts
              </p>
              <div className="flex flex-wrap gap-1.5">
                {['Machines', 'Ordres de travail', 'Alertes', 'Interventions', 'Plannings'].map((d) => (
```

- [ ] **Step 4: Manual verification**

Reload the Assistant IA page. Confirm every string in the right "Exemples de questions" panel is French, hovering a suggestion shows a faint purple border/glow, and "Domaines couverts" badges read in French.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "fix(chat): translate Assistant IA example-questions panel to French"
```

---

### Task 7: ChatWidget parity (floating bubble)

**Files:**
- Modify: `app/frontend/src/modules/shared/ChatInterface.tsx` (`ChatWidget` component, lines ~411-537; import line 4)

- [ ] **Step 1: FAB (closed state)**

Find (around line 411-420):

```tsx
      <Button
        className="fixed bottom-4 right-4 h-14 w-14 rounded-full shadow-2xl z-50 bg-primary hover:bg-primary/90"
        onClick={() => setIsOpen(true)}
        size="icon"
      >
        <Sparkles className="h-6 w-6" />
      </Button>
```

Replace with:

```tsx
      <Button
        className="fixed bottom-4 right-4 h-14 w-14 rounded-full shadow-2xl z-50 bg-gradient-premium border-0 hover:opacity-90 transition-opacity"
        onClick={() => setIsOpen(true)}
        size="icon"
      >
        <Sparkles className="h-6 w-6 text-white" />
      </Button>
```

- [ ] **Step 2: Header**

Find (around line 424-430):

```tsx
      <CardHeader className="pb-2 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Assistant IA
          </CardTitle>
```

Replace with:

```tsx
      <CardHeader className="pb-2 border-b border-white/[0.08] bg-white/[0.02]">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-gradient-premium">
              <Sparkles className="h-3.5 w-3.5 text-white" />
            </span>
            Assistant IA
          </CardTitle>
```

- [ ] **Step 3: User message bubble + avatar**

Find (around line 461-467):

```tsx
                      <div className="bg-primary text-primary-foreground px-3 py-2 rounded-2xl rounded-br-md text-sm">
                        {msg.content}
                      </div>
                      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                        <User className="h-4 w-4 text-primary-foreground" />
                      </div>
```

Replace with:

```tsx
                      <div className="bg-gradient-premium text-white px-3 py-2 rounded-2xl rounded-br-md text-sm">
                        {msg.content}
                      </div>
                      <div className="h-8 w-8 rounded-full bg-gradient-premium flex items-center justify-center flex-shrink-0">
                        <User className="h-4 w-4 text-white" />
                      </div>
```

- [ ] **Step 4: Assistant avatar + bubble**

Find (around line 471-475):

```tsx
                  <div className="flex items-end gap-2 max-w-[85%]">
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="bg-muted/80 backdrop-blur-sm px-4 py-3 rounded-2xl rounded-bl-md border">
```

Replace with:

```tsx
                  <div className="flex items-end gap-2 max-w-[85%]">
                    <div className="h-8 w-8 rounded-full bg-[radial-gradient(circle,hsl(var(--premium-indigo)/0.35),hsl(var(--premium-purple)/0.2)_70%)] flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-[hsl(var(--premium-indigo))]" />
                    </div>
                    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-[12px] px-4 py-3 rounded-2xl rounded-bl-md">
```

- [ ] **Step 5: Input bar**

Find (around line 513-537):

```tsx
          <div className="p-4 border-t bg-muted/20">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
              className="flex gap-2"
            >
              <Button
                type="button"
                size="icon"
                variant="outline"
                onClick={() => setShowDocUpload(true)}
                title="Importer un document dans la base RAG"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Input
                placeholder="Ask about machines, alerts..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>
```

Replace with:

```tsx
          <div className="p-4 border-t border-white/[0.08] bg-transparent">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
              className="flex gap-2"
            >
              <Button
                type="button"
                size="icon"
                variant="outline"
                className="border-white/[0.12] hover:border-[rgba(0,255,242,0.4)]"
                onClick={() => setShowDocUpload(true)}
                title="Importer un document dans la base RAG"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <input
                placeholder="Posez une question sur les machines, alertes..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                className="input-glass flex-1 px-3"
              />
              <Button
                type="submit"
                size="icon"
                disabled={loading || !input.trim()}
                className="bg-gradient-premium text-white border-0 hover:opacity-90 transition-opacity disabled:opacity-40"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>
```

- [ ] **Step 6: Remove the now-unused `Input` import**

Find (line 4):

```tsx
import { Input } from '@/components/ui/input';
```

Delete this line (both usages of shadcn `<Input>` in this file — ChatPage's input from Task 5, and ChatWidget's here — are now raw `<input className="input-glass ...">` elements).

- [ ] **Step 7: Manual verification**

Navigate to any machine detail page (e.g. via the Machines list) to see the floating widget. Confirm: closed FAB is gradient-filled; opening it shows the same gradient header icon; sending a message shows gradient user bubble / glass assistant bubble; input field has the glass look; placeholder text is French.

- [ ] **Step 8: Run the frontend build to confirm no leftover references to the removed import**

Run (from `app/frontend/`): `npx tsc --noEmit`
Expected: no errors related to `Input` or `ChatInterface.tsx`.

- [ ] **Step 9: Commit**

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "feat(chat): apply premium visual language to floating ChatWidget for parity with Assistant IA page"
```

---

### Task 8: Final verification pass

**Files:** none (verification only; fix forward in this task's own commit if something's off)

- [ ] **Step 1: Run the full unit test suite**

Run (from `app/frontend/`): `npm run test`
Expected: all tests pass, including the 4 new `filterVisibleSessions` tests.

- [ ] **Step 2: Type-check**

Run (from `app/frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Walk the spec's verification checklist live**

With the Vite dev server still running (`http://localhost:5173`), logged in:
- Search the rendered Assistant IA page and the floating widget for the text "Groq" — must find none.
- Confirm every visible string in the example-questions panel and domain badges is French.
- Create a new conversation, don't send anything, switch to a different existing conversation — confirm the empty one you left disappears from the sidebar list.
- Toggle OS/browser dark mode off and on (or use devtools) — confirm text stays readable against the glass panels in both.

- [ ] **Step 4: Rebuild the Docker frontend image so the containerized app matches**

```bash
cd "C:/Users/Admin/Downloads/EAM/EAMSagemCom" && docker compose build frontend && docker compose up -d frontend
```

Then re-check `http://localhost:3000` (the containerized, production-built app) shows the same redesign.

- [ ] **Step 5: Stop the local Vite dev server**

It was only needed for iterative verification; the containerized frontend (Task 4 above) is the app's normal run path.

No commit for this task unless Step 3 surfaces a bug — if it does, fix it in `ChatInterface.tsx`, re-run Steps 1-3, then:

```bash
git add app/frontend/src/modules/shared/ChatInterface.tsx
git commit -m "fix(chat): address issue found in final Assistant IA redesign verification pass"
```
