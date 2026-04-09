# Sagemcom EAM Platform — Complete Design System & Reproduction Prompt

> **Purpose:** This document is a comprehensive prompt you can give to any AI code editor to reproduce the exact same website design, layout, and style as the Sagemcom EAM Platform built here.

---

## 1. Project Overview

**Name:** Sagemcom EAM (Enterprise Asset Management) Platform  
**Type:** Full-stack GMAO (Gestion de Maintenance Assistée par Ordinateur) web application  
**Language:** French UI labels for admin/internal pages, English for the public landing page  
**Tech Stack:** React 18 + TypeScript + Vite 5 + Tailwind CSS v3 + shadcn/ui components  
**Icon Library:** Lucide React  
**Chart Library:** Recharts  
**Routing:** React Router DOM v6  

---

## 2. Overall Visual Identity

### 2.1 Design Philosophy
- **Dark glassmorphism** aesthetic — frosted glass panels floating over a deep blue gradient background
- **Futuristic, enterprise-grade** look with neon cyan accents and subtle purple highlights
- All UI elements feel like transparent panels with soft blur and light borders
- Smooth hover animations with lift effects (translateY) and shadow intensification
- No harsh edges — everything uses generous border-radius (`1rem` / `rounded-2xl`)

### 2.2 Background
```css
body {
  background: linear-gradient(to bottom-right, #0f172a /* slate-900 */, #1e3a5f /* blue-900 */, #1e293b /* slate-800 */);
  background-attachment: fixed;
  min-height: 100vh;
}
```
This gradient is **fixed** (doesn't scroll), creating an immersive dark environment across all pages.

---

## 3. Color System (All HSL)

### 3.1 Core Tokens (CSS Custom Properties)
```css
:root {
  /* Base */
  --background: 220 25% 8%;           /* Near-black with blue undertone */
  --foreground: 210 20% 98%;          /* Near-white */

  /* Cards & Panels */
  --card: 220 25% 12%;                /* Slightly lighter dark */
  --card-foreground: 210 20% 98%;

  /* Popovers & Dropdowns */
  --popover: 220 25% 12%;
  --popover-foreground: 210 20% 98%;

  /* Primary — Electric Cyan */
  --primary: 200 100% 50%;            /* #0099ff — vibrant cyan-blue */
  --primary-foreground: 220 25% 8%;   /* Dark text on primary */
  --primary-glow: 200 100% 70%;       /* Lighter cyan for gradients & glow */

  /* Secondary */
  --secondary: 220 25% 15%;
  --secondary-foreground: 210 20% 98%;

  /* Muted */
  --muted: 220 25% 10%;
  --muted-foreground: 210 10% 65%;    /* Soft gray for secondary text */

  /* Accent — Vivid Purple */
  --accent: 280 100% 60%;             /* Used sparingly for secondary highlights */
  --accent-foreground: 210 20% 98%;

  /* Destructive — Red */
  --destructive: 0 75% 55%;
  --destructive-foreground: 210 20% 98%;

  /* Borders & Inputs */
  --border: 220 25% 20%;              /* Subtle dark borders */
  --input: 220 25% 15%;
  --ring: 200 100% 50%;               /* Focus ring = primary cyan */

  --radius: 1rem;
}
```

### 3.2 Semantic Color Usage
| Element | Color | Notes |
|---------|-------|-------|
| Page background | `from-slate-900 via-blue-900 to-slate-800` | Fixed gradient |
| Card/panel backgrounds | `rgba(255,255,255,0.1)` with blur | Glassmorphism |
| Primary text | `text-white` | All main text is white |
| Secondary text | `text-white/80` | Slightly transparent |
| Muted/tertiary text | `text-white/60` or `text-white/70` | |
| Faint text | `text-white/40` or `text-white/50` | Timestamps, hints |
| Borders | `border-white/10` or `border-white/20` | Semi-transparent white |
| Hover backgrounds | `bg-white/10` or `hover:bg-white/10` | Subtle highlight |
| Active/selected states | `bg-primary/20 border-primary/30` | Cyan tint |
| Success indicators | `text-green-400`, `bg-green-500/20` | |
| Warning indicators | `text-yellow-400`, `bg-yellow-500/20` | |
| Error/destructive | `text-red-400`, `bg-red-500/20` | |
| Info indicators | `text-blue-400`, `bg-blue-500/20` | |
| Purple accents | `text-purple-400`, `bg-purple-500/20` | |

---

## 4. Glassmorphism System

### 4.1 Base Glass Effect
```css
.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}
```

### 4.2 Glass Hover Effect
```css
.glass-hover {
  transition: all 0.3s ease;
}
.glass-hover:hover {
  box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
  transform: translateY(-2px);
}
```

### 4.3 Glass Card (Combined)
```css
.glass-card {
  /* Combines glass + glass-hover + rounded-2xl + p-6 */
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
  border-radius: 1rem;
  padding: 1.5rem;
  transition: all 0.3s ease;
}
.glass-card:hover {
  box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
  transform: translateY(-2px);
}
```

### 4.4 Glass Button
```css
.glass-button {
  /* glass + glass-hover + rounded-xl + px-6 py-3 + gradient background */
  background: linear-gradient(135deg, hsl(200 100% 50%), hsl(200 100% 70%));
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  padding: 0.75rem 1.5rem;
  font-weight: 500;
  color: white;
}
```

### 4.5 Gradient Text
```css
.gradient-text {
  background: linear-gradient(135deg, hsl(200 100% 50%), hsl(200 100% 70%));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

---

## 5. Typography

- **Font Family:** System sans-serif stack (no custom fonts loaded)
- **Headings:** Bold (`font-bold`), white text
- **Hero title:** `text-5xl md:text-7xl font-bold text-white` with `gradient-text` on key words
- **Section titles:** `text-4xl md:text-5xl font-bold text-white` with gradient-text accent on a word
- **Card titles:** `text-2xl font-semibold` or `text-xl font-bold text-white`
- **Body text:** `text-white/80` or `text-white/70`, `leading-relaxed`
- **Small/secondary:** `text-sm text-white/60`
- **Tiny/timestamps:** `text-xs text-white/50` or `text-white/40`

---

## 6. Layout Patterns

### 6.1 Landing Page (Public)
Structure: `Header → HeroSection → OverviewCards → FeatureHighlights → TestimonialsSection → Footer`

- **Header:** Fixed top bar with glass effect, logo left, nav center, login button right
- **Hero:** Full-screen centered glass card with gradient title, subtitle, 2 CTA buttons, stats row
- **Overview Cards:** 4-column grid of glass stat cards with icon + value + change percentage
- **Feature Highlights:** 2-column grid of feature cards (icon + title + description + bullet benefits + "Learn more" link)
- **Stats Banner:** Glass card with 3-column grid of icon + title + description
- **Testimonials:** Impact stats bar + 3-column testimonial cards with star rating, quote, avatar
- **Footer:** Glass footer with 6-column grid (company info, 4 link columns), newsletter signup, social links

### 6.2 Admin Panel (Dashboard & Sub-pages)
Structure: `Sidebar (fixed left) + Header (fixed top) + Main Content (scrollable)`

- **Sidebar:** Fixed left, glass background, variable width (mini/compact/normal/wide)
- **Header:** Fixed top, glass, spans from sidebar edge to right edge
- **Content:** `pt-16 p-6`, scrollable, `max-w-7xl mx-auto`
- Main content margin adjusts with sidebar: `ml-16 / ml-48 / ml-64 / ml-80`

### 6.3 Auth Pages (SignIn/SignUp)
- Centered glass card on gradient background
- Back button top-left
- Logo + form fields + social login buttons
- Form inputs: `bg-white/10 border-white/20 text-white placeholder-white/40 rounded-xl`

---

## 7. Component Specifications

### 7.1 Admin Sidebar
- **Sizes:** mini (64px / `w-16`), compact (192px / `w-48`), normal (256px / `w-64`), wide (320px / `w-80`)
- **Background:** Glass effect, full height, fixed position
- **Logo:** 32x32 cyan rounded square with "S" letter, plus company name when space allows
- **Nav Items:** Icon + text, `px-3 py-2.5`, `rounded-lg`
  - Normal: `text-white/80`
  - Hover: `hover:bg-white/10 hover:text-white`
  - Active: `bg-primary/20 text-white border border-primary/30` with a cyan dot indicator (`w-2 h-2 bg-primary rounded-full`) on the right
- **User Profile:** Absolute bottom, glass-card with avatar circle (gradient background) + name + email
- **Menu Items:** Dashboard, Utilisateurs, Assets, Ordres de travail, Archive, Plannings, Interventions, Rapports, Activité, Notifications, Paramètres

### 7.2 Admin Header
- Fixed top bar, glass background, adjusts left position based on sidebar size
- **Left:** Sidebar size toggle (chevron left/right buttons in `bg-white/10 rounded-lg p-1` container) + page title
- **Center:** Search input (`bg-white/10 border-white/20 text-white placeholder:text-white/60`)
- **Right:** Refresh button, notification bell with red badge (`bg-destructive`), user dropdown menu
- **User dropdown:** Glass background, items: Profil, Paramètres, separator, Déconnexion

### 7.3 Stat Card
```
┌─────────────────────────────────────┐
│ Label (text-sm text-white/80)       │
│ VALUE (text-3xl font-bold white)    │  [Icon in gradient
│ +12% (green/red text-sm)           │   rounded-xl box]
│ Subtitle (text-sm text-white/60)   │
└─────────────────────────────────────┘
```
- Glass card with glass-hover effect
- Icon container: `w-12 h-12 bg-gradient-primary rounded-xl` with white icon inside
- Trend: green for positive (`text-green-400`), red for negative (`text-red-400`)

### 7.4 Quick Actions Grid
- Glass card containing a `grid-cols-2 md:grid-cols-4 lg:grid-cols-6` grid
- Each action: `Button variant="outline"` with `h-auto p-4 flex-col glass-hover border-white/20 text-white hover:bg-white/10`
- Icon (`w-6 h-6 mb-2`) above label (`text-sm`)
- Actions: Nouvel utilisateur, Nouvelle machine, Nouvel ordre, Sauvegarde, Rapport audit, Planning urgence

### 7.5 Data Tables
- Wrapped in glass-card
- **Header row:** Search input + role/status filter dropdown + action buttons (Export, Add new)
- **Table container:** `rounded-lg overflow-hidden bg-white/5 backdrop-blur-sm`
- **Table headers:** `text-white/80 font-medium`, row border `border-white/10`
- **Table rows:** `border-b border-white/5 hover:bg-white/5`
- **User cells:** Avatar circle (gradient background with initial) + name + email
- **Status badges:** Colored with opacity backgrounds:
  - Active/Actif: `bg-green-500/20 text-green-400 border-green-500/30`
  - Inactive/Inactif: `bg-gray-500/20 text-gray-400 border-gray-500/30`
  - Pending/En attente: `bg-yellow-500/20 text-yellow-400 border-yellow-500/30`
- **Role badges:**
  - Admin: `bg-red-500/20 text-red-400 border-red-500/30`
  - ChefOp: `bg-blue-500/20 text-blue-400 border-blue-500/30`
  - ChefTech: `bg-green-500/20 text-green-400 border-green-500/30`
  - Technicien: `bg-yellow-500/20 text-yellow-400 border-yellow-500/30`
  - Opérateur: `bg-purple-500/20 text-purple-400 border-purple-500/30`
- **Actions column:** DropdownMenu with Eye (Voir), Edit (Modifier), Trash (Supprimer in red)
- **Footer:** Results count + rows per page text in `text-white/60`

### 7.6 Activity Feed
- Glass card, right sidebar column
- Header: "Activité récente" with "Tout voir" ghost button
- Each item: `p-3 rounded-lg bg-white/5 hover:bg-white/10`
  - Left: 32px circle (`bg-white/10 backdrop-blur`) with colored icon
  - Right: User name + type badge + action text + details + timestamp
- Activity type colors:
  - create → `text-green-400`
  - edit → `text-blue-400`
  - login → `text-purple-400`
  - validate → `text-emerald-400`
  - warning → `text-yellow-400`

### 7.7 Performance Section
- Glass card with 3-column grid
- Each: title (`font-medium text-white`) + Progress bar (`h-3`) + percentage text (`text-white/70`)

### 7.8 System Status Card
- Glass card with stacked status rows
- Each row: `p-3 rounded-lg` with colored background (`bg-green-500/20`, `bg-blue-500/20`, `bg-yellow-500/20`)
- Left: white label, Right: colored status text

### 7.9 Feature Cards (Landing Page)
- 2-column grid, glass-card with `border-white/10 hover:border-white/20`
- Layout: gradient icon box (left) + content (right)
- Icon container: `p-4 rounded-2xl bg-gradient-to-br` with different gradients per card:
  - `from-blue-500 to-cyan-500`
  - `from-green-500 to-emerald-500`
  - `from-purple-500 to-pink-500`
  - `from-orange-500 to-red-500`
- Benefits list: cyan dot (`w-1.5 h-1.5 rounded-full bg-primary`) + text

### 7.10 Testimonial Cards
- 3-column grid, glass cards, full height
- Star rating row (5 yellow stars, `text-yellow-400 fill-current`)
- Quote icon (`text-primary/40`), italic quote text (`text-white/80`)
- Avatar: `w-12 h-12 rounded-full bg-gradient-to-br from-primary to-primary-glow` with initials
- Name (`font-semibold text-white`), role (`text-white/60`), company (`text-white/40`)

### 7.11 Landing Page Header
- Fixed top, full width, glass with `border-b border-white/10`
- Logo: Building2 icon + "Sagemcom" / "EAM Platform"
- Nav: Ghost buttons (`text-white/80 hover:text-white hover:bg-white/10`)
- Login: Glass button with LogIn icon

### 7.12 Footer
- Glass with `border-t border-white/10`
- 6-column grid: company info (2 cols) + 4 link sections
- Company: logo + description + contact info (email, phone, location)
- Link sections: Product, Company, Support, Legal — each with 4 links
- Newsletter: glass-card with email input + Subscribe button
- Bottom: copyright + social icons (GitHub, LinkedIn, Twitter)

### 7.13 Form Inputs (Auth & Admin)
```css
/* Standard glass input */
input {
  width: 100%;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  placeholder-color: rgba(255, 255, 255, 0.4);
}
input:focus {
  outline: none;
  border-color: hsl(200 100% 50%); /* primary */
  background: rgba(255, 255, 255, 0.15);
}
```

### 7.14 Dialogs / Modals
- Glass background (`glass border-white/20`)
- White text throughout
- Form fields use same glass input style
- Action buttons: primary (cyan) for confirm, outline for cancel

### 7.15 Select Dropdowns
- Trigger: `bg-white/10 border-white/20 text-white`
- Content: `glass border-white/20`
- Items: `text-white hover:bg-white/10`

---

## 8. Dashboard Layout (Admin)

```
┌──────────┬────────────────────────────────────────────────────────────────┐
│          │  [◄ ►] Sagemcom EAM Admin Panel   [🔍 Search...]  [🔄] [🔔3] [👤▾] │
│  SIDEBAR │────────────────────────────────────────────────────────────────│
│          │                                                                │
│  [Logo]  │   Sagemcom EAM Admin Panel (centered title)                   │
│          │   Système de gestion des actifs et contrôles administratifs    │
│  ──────  │                                                                │
│ Dashboard│   ┌─────────── Actions rapides ──────────────────────────┐     │
│ Users    │   │ [+User] [+Machine] [+Ordre] [Save] [Audit] [Plan]  │     │
│ Assets   │   └──────────────────────────────────────────────────────┘     │
│ Work Ord │                                                                │
│ Archive  │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                        │
│ Plannings│   │Stats │ │Stats │ │Stats │ │Stats │  (4-col grid × 2 rows) │
│ Interv.  │   └──────┘ └──────┘ └──────┘ └──────┘                        │
│ Rapports │                                                                │
│ Activity │   ┌──── 2/3 width ────────────┐ ┌──── 1/3 width ────┐        │
│ Notif.   │   │ Performance Overview      │ │ Activity Feed     │        │
│ Settings │   │ [Progress bars × 3]       │ │ [Activity items]  │        │
│          │   ├───────────────────────────┤ ├────────────────────┤        │
│  ──────  │   │ Management Table          │ │ System Status     │        │
│ [Profile]│   │ [Search] [Filter] [+Add]  │ │ [Status rows]     │        │
│          │   │ [Data table with actions] │ │                    │        │
│          │   └───────────────────────────┘ └────────────────────┘        │
│          │                                                                │
│          │   ┌──────────── Footer ────────────────────────────┐          │
│          │   │ [Logo] Sagemcom EAM  © 2024  [Aide] [Terms]   │          │
│          │   └────────────────────────────────────────────────┘          │
└──────────┴────────────────────────────────────────────────────────────────┘
```

---

## 9. Page Inventory & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Landing/Index | Public marketing page with hero, features, testimonials |
| `/signin` | Sign In | Glass card login form with social auth |
| `/signup` | Sign Up | Glass card registration form |
| `/admin` | Admin Dashboard | Main dashboard with stats, quick actions, tables, activity |
| `/admin/users` | Users Management | Full CRUD table for users with detail/edit/delete modals |
| `/admin/assets` | Assets Management | CRUD for machines/equipment with status tracking |
| `/admin/work-orders` | Work Orders | CRUD for maintenance orders |
| `/admin/interventions` | Interventions | CRUD for intervention records |
| `/admin/plannings` | Plannings | Maintenance scheduling management |
| `/admin/rapports` | Reports | Report generation and viewing |
| `/admin/archive` | Archive | Document archival system |
| `/admin/activity` | Activity & Notifications | Activity log + notification center (two-tab layout) |
| `/class-diagram` | Class Diagram | ASCII UML class diagram of the system |

---

## 10. Data Model (Class Diagram)

### 10.1 Core Entities

**Utilisateur (User)**
- Fields: id, nom, email, telephone, role, departement, statut, derniereConnexion, dateCreation, avatar
- Methods: creer(), modifier(), supprimer(), authentifier(), changerMotDePasse()

**Actif (Asset)**
- Fields: id, identifiant, nom, type (TypeActif), emplacement, statut (StatutActif), dateAcquisition, valeur, fabricant, modele, numeroSerie, garantie
- Methods: creer(), modifier(), supprimer(), planifierMaintenance()

**OrdreTravail (Work Order)**
- Fields: id, identifiant, titre, description, type (TypeOT), priorite, statut (StatutOT), dateCreation, dateEcheance, assigneA, actifId
- Methods: creer(), modifier(), assigner(), cloturer(), annuler()

**Intervention**
- Fields: id, identifiant, type (TypeIntervention), description, dateDebut, dateFin, duree, statut (StatutInterv), technicien, actifId, ordreId, notes, coutMain, coutPieces
- Methods: creer(), modifier(), terminer(), annuler()

**Planning**
- Fields: id, identifiant, dateDebut, dateFin, type (TypePlanning), assigneA[], statut (StatutPlanning), description, priorite, ordresTravail[]
- Methods: creer(), modifier(), annuler(), terminer()

**Rapport (Report)**
- Fields: id, titre, type (TypeRapport), dateGeneration, periode, contenu, format (FormatRapport), genererPar
- Methods: generer(), exporter(), partager(), archiver()

**Archive**
- Fields: id, identifiant, typeDocument, titre, dateArchivage, taille, categorie, sourceId, sourceType
- Methods: archiver(), restaurer(), supprimer(), telecharger()

**PieceRechange (Spare Part)**
- Fields: id, reference, nom, description, quantiteStock, seuilMinimum, prixUnitaire, fournisseur, emplacement
- Methods: commander(), ajusterStock(), alerteStock()

**Notification**
- Fields: id, titre, message, type (TypeNotif), priorite, dateCreation, lu, destinataire, lien
- Methods: envoyer(), marquerLu(), supprimer()

### 10.2 Enumerations

| Enum | Values |
|------|--------|
| Role | ADMINISTRATEUR, CHEF_OPERATEUR, CHEF_TECHNICIEN, TECHNICIEN, OPERATEUR |
| StatutUser | ACTIF, INACTIF, EN_ATTENTE |
| TypeActif | MACHINE, EQUIPEMENT, VEHICULE, OUTILLAGE, INFRASTRUCTURE |
| StatutActif | OPERATIONNEL, EN_PANNE, EN_MAINTENANCE, HORS_SERVICE |
| TypeOT | MAINTENANCE_PREV, MAINTENANCE_CORR, INSPECTION, REPARATION, INSTALLATION |
| StatutOT | OUVERT, EN_COURS, EN_ATTENTE, TERMINE, ANNULE |
| Priorite | BASSE, MOYENNE, ELEVEE, URGENTE |
| TypeIntervention | PREVENTIVE, CORRECTIVE, PREDICTIVE, CONDITIONNELLE, AMELIORATIVE |
| StatutIntervention | PLANIFIEE, EN_COURS, TERMINEE, ANNULEE, REPORTEE |
| TypePlanning | MAINT_PREVENTIVE, MAINT_CORRECTIVE, INTERV_URGENTE, INSPECTION |
| StatutPlanning | PLANIFIE, EN_COURS, TERMINE, ANNULE |
| TypeNotif | URGENT, WARNING, INFO, SUCCESS |
| TypeRapport | ACTIVITE, MAINTENANCE, PERFORMANCE, INTERVENTION, INVENTAIRE |
| FormatRapport | PDF, EXCEL, CSV, HTML |

### 10.3 Entity Relationships
- Utilisateur → many Interventions, OrdreTravail, Planning, Notification
- Actif → many Interventions, OrdreTravail, Planning
- OrdreTravail → many Interventions, linked to one Actif, part of Planning
- Intervention → uses many PieceRechange, generates Archive records
- Rapport → generated from OrdreTravail/Intervention data

---

## 11. Interaction Patterns

### 11.1 Sidebar Toggle
- Header contains `◄ ►` buttons to cycle through sidebar sizes: mini → compact → normal → wide
- Sidebar and main content transitions use `transition-all duration-300`
- In mini mode: icons only, no text
- In compact mode: truncated labels (first word only), smaller text
- In normal/wide mode: full labels + active indicator dot

### 11.2 CRUD Operations
Every management page (Users, Assets, Work Orders, Interventions) follows the same pattern:
1. **List view:** Glass card with search, filters, table, pagination info
2. **Create:** Dialog/modal with glass-styled form
3. **View detail:** Detail modal showing all fields in a structured layout
4. **Edit:** Same form as create, pre-filled
5. **Delete:** Confirmation dialog with destructive action

### 11.3 Notifications
- Bell icon in header with red badge showing unread count
- Activity page has dedicated notifications tab
- Each notification: title, message, type badge, timestamp, read/unread state
- Types color-coded: URGENT (red), WARNING (yellow), INFO (blue), SUCCESS (green)

### 11.4 Form Patterns
- Labels: `text-sm font-medium text-white`
- Inputs: glass-style (`bg-white/10 border-white/20 text-white`)
- Select dropdowns: same glass style
- Buttons: Primary action (cyan gradient), Cancel (outline glass)
- Validation feedback via toast notifications (sonner)

---

## 12. Responsive Breakpoints

| Breakpoint | Behavior |
|-----------|----------|
| Mobile (`<md`) | Single column, sidebar hidden or mini, hamburger menu |
| Tablet (`md`) | 2-column grids, compact sidebar |
| Desktop (`lg`) | Full layout, 3-4 column grids, normal sidebar |
| Wide (`2xl`) | `max-w-7xl` container, wide sidebar option |

Key responsive classes used:
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`
- `hidden md:flex` / `hidden lg:flex` for progressive disclosure
- `text-5xl md:text-7xl` for hero scaling

---

## 13. Animation & Transitions

| Element | Animation |
|---------|-----------|
| Glass cards | `transition: all 0.3s ease` — hover lifts by 2px with enhanced shadow |
| Sidebar | `transition-all duration-300` — smooth width changes |
| Header | `transition-all duration-300` — adjusts to sidebar |
| Navigation links | `transition-colors` — smooth color changes |
| CTA arrow icon | `group-hover:translate-x-1 transition-transform` |
| Accordion | `accordion-down 0.2s ease-out` / `accordion-up 0.2s ease-out` |
| Badge notifications | Static red dot (no animation) |

---

## 14. Dependencies & Libraries

```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.26.2",
  "@tanstack/react-query": "^5.56.2",
  "tailwindcss": "^3.4.11",
  "tailwindcss-animate": "^1.0.7",
  "lucide-react": "^0.462.0",
  "recharts": "^2.12.7",
  "class-variance-authority": "^0.7.1",
  "clsx": "^2.1.1",
  "tailwind-merge": "^2.5.2",
  "sonner": "^1.5.0",
  "date-fns": "^3.6.0",
  "zod": "^3.23.8",
  "react-hook-form": "^7.53.0",
  "@hookform/resolvers": "^3.9.0",
  "cmdk": "^1.0.0",
  "vaul": "^0.9.3",
  "embla-carousel-react": "^8.3.0",
  "input-otp": "^1.2.4",
  "react-day-picker": "^8.10.1",
  "react-resizable-panels": "^2.1.3",
  "next-themes": "^0.3.0"
}
```

**UI Components:** shadcn/ui (all components pre-installed)

---

## 15. Key Design Rules

1. **Never use raw color classes** — always use semantic tokens (`bg-primary`, `text-foreground`, etc.) or `white/opacity` patterns
2. **All panels are glass** — use `glass-card` class or equivalent styles
3. **Dark theme only** — there is no light mode (`:root` is already dark)
4. **Text is always white** with varying opacity for hierarchy
5. **Borders are always semi-transparent white** (`border-white/10` to `border-white/20`)
6. **Icons come from Lucide** — consistent `w-4 h-4` to `w-8 h-8` sizing
7. **Status/role indicators** use colored backgrounds at 20% opacity with matching text at full color
8. **All interactive elements** have hover states (background change or lift effect)
9. **French labels** for admin interface, English for landing page
10. **Avatar circles** use `bg-gradient-primary rounded-full` with initial letters

---

## 16. File Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui primitives (button, card, dialog, table, etc.)
│   ├── AdminSidebar.tsx  # Collapsible sidebar with navigation
│   ├── AdminHeader.tsx   # Top header bar with search, notifications, user menu
│   ├── StatCard.tsx      # Reusable stat card component
│   ├── ActivityFeed.tsx  # Activity timeline component
│   ├── ManagementTable.tsx # User management table with filters
│   ├── Header.tsx        # Public landing page header
│   ├── HeroSection.tsx   # Landing page hero
│   ├── OverviewCards.tsx  # Landing page stat cards
│   ├── FeatureHighlights.tsx # Landing page features
│   ├── TestimonialsSection.tsx # Landing page testimonials
│   ├── Footer.tsx        # Landing page footer
│   └── forms/            # Detail modals and form components
│       ├── AssetForm.tsx / AssetDetailModal.tsx
│       ├── UserForm.tsx / UserDetailModal.tsx
│       ├── WorkOrderForm.tsx / WorkOrderDetailModal.tsx
│       ├── InterventionForm.tsx / InterventionDetailModal.tsx
│       └── DeleteConfirmationDialog.tsx
├── pages/
│   ├── Index.tsx         # Landing page
│   ├── SignIn.tsx        # Login page
│   ├── SignUp.tsx        # Registration page
│   ├── AdminDashboard.tsx # Main admin dashboard
│   ├── Users.tsx         # User management (CRUD)
│   ├── Assets.tsx        # Asset management (CRUD)
│   ├── WorkOrders.tsx    # Work order management (CRUD)
│   ├── Interventions.tsx # Intervention management (CRUD)
│   ├── Plannings.tsx     # Planning management
│   ├── Rapports.tsx      # Reports
│   ├── Archive.tsx       # Document archive
│   ├── Activity.tsx      # Activity log & notifications
│   ├── ClassDiagram.tsx  # System class diagram
│   └── NotFound.tsx      # 404 page
├── hooks/
│   ├── use-mobile.tsx
│   └── use-toast.ts
├── lib/
│   └── utils.ts          # cn() utility for class merging
├── index.css             # Design system tokens & glassmorphism utilities
├── App.tsx               # Router configuration
└── main.tsx              # Entry point
```

---

*This prompt contains every design decision, color value, layout pattern, component specification, and data model used in the Sagemcom EAM Platform. Use it to reproduce the exact same website in any React-based editor.*
