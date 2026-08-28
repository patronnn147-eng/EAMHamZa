# AI Assistant (Chat) Visual Redesign

## Context

`ChatInterface.tsx` renders two surfaces:
- `ChatPage` — full-page "Assistant IA" screen (route-mounted), 3-column layout: conversations sidebar | chat | example-questions sidebar.
- `ChatWidget` — floating bubble chat mounted on other pages (e.g. machine detail).

Both currently use flat `bg-primary` / `bg-muted` Tailwind utility colors. The app already ships an unused "Premium Palette Extension" in `index.css` (`--premium-indigo/purple/rose/amber/emerald`, `.bg-gradient-premium`, `.text-gradient-premium`, `.glass-panel`, `.glass-panel-hover`, `.input-glass`, `.animate-premium-fade-in`) — defined but not applied anywhere in this component. This redesign is purely visual/copy — no backend or API changes.

## Problems being fixed

1. Visually flat/generic — plain `bg-primary`/`bg-muted` throughout, large empty dark areas, low visual hierarchy.
2. "Groq LLM" badge exposes the underlying LLM vendor to end users — inconsistent with the project's existing convention of hiding ML internals behind business-facing labels (see CLAUDE.md naming conventions for P1–P6 models).
3. Copy inconsistency — page chrome is French, but the static "Exemples de questions" list (8 items) and "Domains supported" badges in the right sidebar are hardcoded English.
4. Sidebar clutter — every created session appears immediately, including ones with 0 messages (e.g. from `createNewSession`), so abandoned "Nouveau" clicks pile up as dead entries.
5. `ChatWidget` and `ChatPage` currently already share the same (flat) visual language; this redesign keeps them in sync using the new one.

## Design

### 1. Shared visual language (both ChatPage and ChatWidget)

Reuse existing tokens from `index.css` — nothing new is added:
- `bg-gradient-premium` (indigo → purple → rose) replaces flat `bg-primary` on: user message bubbles, send button, FAB (ChatWidget closed state), "Nouveau" button, active-session ring, avatar rings.
- `.glass-panel` + `.glass-panel-hover` replace flat `bg-muted/*` on: assistant message bubbles, example-question cards.
- `.input-glass` replaces the plain `Input` background/border on the chat input field (kept as the shadcn `Input` component, styled via `className`).
- `.animate-premium-fade-in` applied to each newly-rendered message.
- No new CSS is written; only `className` changes in `ChatInterface.tsx`.

### 2. Header

- Remove the `Badge` reading "Groq LLM" (`<Bot /> Groq LLM`).
- Replace with a small pill: a pulsing dot (`animate-pulse`, gradient-colored) + text "Assistant actif". No vendor/model name surfaced.
- Sparkle icon in the `CardTitle`/`h1` gets `text-gradient-premium` treatment (or a gradient-filled icon container) instead of flat `text-primary`.

### 3. ChatPage — conversations sidebar

- Active session: replace `bg-primary/10 border-primary/30` with a gradient-ring treatment (e.g. `ring-1 ring-offset-0` using a gradient border via a wrapping div, or `border-transparent bg-gradient-premium/10` + gradient left-bar accent) — implementation detail left to whichever reads cleanest in code, but the effect must be a visibly gradient (not flat-blue) active indicator.
- "Nouveau" button: gradient fill (`bg-gradient-premium text-white hover:opacity-90` instead of `variant="outline"`).
- **Empty-session filtering**: sessions with `message_count === 0` are hidden from the rendered list UNLESS `s.id === currentSessionId` (so a just-created active session stays visible while the user is typing into it, but abandoned empty sessions from previous visits don't clutter the list). This is a pure render-time filter on the existing `sessions` array — no change to fetch/create/delete logic.

### 4. ChatPage — message list

- User bubble: `bg-gradient-premium text-white` (was `bg-primary text-primary-foreground`).
- Assistant bubble: `.glass-panel` (was `bg-muted/60 backdrop-blur-sm border`); hover gets `.glass-panel-hover`.
- Avatar circles: gradient ring/fill instead of flat `from-primary/20 to-primary/40`.
- Empty state icon container: gradient glow ring instead of flat `bg-primary/10`.
- Loading indicator dots: cycle through the gradient stops instead of flat `bg-primary`.
- Each message wrapper gets `.animate-premium-fade-in`.

### 5. ChatPage — input bar

- `Input` gets `.input-glass` styling via className (keeps existing placeholder/value/onChange wiring).
- Send button: gradient fill.
- Attach (upload) button: unchanged behavior, minor border/hover polish to match glass surfaces.

### 6. ChatPage — right sidebar ("Exemples de questions")

- Translate the hardcoded 8-item English array to French, matching existing app vocabulary:
  - "Show machines in Zone A" → "Machines en Zone A"
  - "Show critical alerts" → "Alertes critiques"
  - "Pending work orders" → "Ordres de travail en attente"
  - "Show me interventions" → "Voir les interventions"
  - "Show plannings for this week" → "Plannings de la semaine"
  - "Machines needing repair" → "Machines à réparer"
  - "Show high priority alerts" → "Alertes haute priorité"
  - "Work orders by CHEFTECH" → "Ordres de travail par CHEFTECH"
- Translate "Domains supported" → "Domaines couverts"; badge labels: "Work Orders" → "Ordres de travail", "Alerts" → "Alertes", "Interventions" → "Interventions" (unchanged), "Plannings" → "Plannings" (unchanged), "Machines" unchanged.
- Buttons get gradient-border hover instead of flat ghost hover.

### 7. ChatWidget (floating bubble)

Same treatment, scoped to the widget's smaller surface:
- Closed-state FAB: `bg-gradient-premium` instead of flat `bg-primary`.
- Header: same badge/icon gradient treatment as ChatPage (no "Groq" text ever appeared here, so just apply the gradient icon).
- Message bubbles: same gradient (user) / glass (assistant) swap as ChatPage.
- Input: `.input-glass`.
- No layout/structural changes to the widget (still a fixed bottom-right card, same open/minimize/close behavior).

### 8. Out of scope

- No changes to `RenderedMessage`'s table/list rendering logic, sources panel, or tool-call badges — only their container's background/border may inherit the glass treatment implicitly via parent bubble styling; no logic changes.
- No changes to session fetch/create/delete/rename API calls or backend.
- No changes to `useDocUpload` / document-upload dialog behavior or its own visual style (out of scope — not mentioned as a pain point).

## Testing / verification

- Visual-only change with no new state logic beyond the empty-session filter. Verification is manual: run the dev server, open the Assistant IA page and the floating widget, confirm:
  - No "Groq" text visible anywhere in the UI.
  - All example-question text is French.
  - Creating a new empty conversation still shows it (as the current selection) in the sidebar. Switching to a different session hides that now-abandoned empty one from the list (filter is `message_count === 0 && id !== currentSessionId`), matching "hide abandoned empty sessions."
  - Dark theme contrast remains acceptable (glass panels still readable against `--background`).
