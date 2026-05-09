---
phase: 12-cheftech-alert-response-workflow-page
plan: "02"
status: complete
---

## What was done

Updated `app/frontend/src/modules/cheftech/ChefTechAlertWorkflow.tsx` with full triage panel (Sheet), assign/dismiss handlers, and technician availability check.

### New imports added
- Sheet, SheetContent, SheetHeader, SheetTitle from `@/components/ui/sheet`
- Select, SelectContent, SelectItem, SelectTrigger, SelectValue from `@/components/ui/select`
- Calendar from `@/components/ui/calendar`
- Popover, PopoverContent, PopoverTrigger from `@/components/ui/popover`
- Checkbox from `@/components/ui/checkbox`
- Label from `@/components/ui/label`
- Separator from `@/components/ui/separator`
- useToast from `@/hooks/use-toast`
- ToastAction from `@/components/ui/toast`
- CalendarIcon, AlertTriangle (as TriangleWarning) from lucide-react

### New state
- `triageForm` — technicienId, priority, dueDate, createWO
- `techOpenWOs` — open work order count for selected technician
- `techLoadingCheck` — availability check loading state
- `assigning` — assign button loading state

### checkTechAvailability(techId)
- Fetches `GET /api/v1/entities/ordres_travail?query={assigned_to: techId}&limit=100`
- Filters out TERMINE/ANNULE statuts
- Sets techOpenWOs count
- Triggers orange warning: "Technicien occupé (X OT en cours)"

### handleAssign(alert)
- Optimistic update: sets `is_linked_to_wo: true` → moves card to Technician lane
- Closes panel immediately
- Calls `POST /api/v1/alerts/{id}/create-work-order` with created_by, assigned_to, priority, due_date
- On API error: rolls back is_linked_to_wo, shows destructive toast

### handleDismiss(alert)
- Optimistic remove from alerts list
- Closes panel
- Shows toast with "Annuler" ToastAction (3s window)
- Undo: restores alert to state, dismisses toast
- After 3s: calls `PATCH /api/v1/alerts/{id}/dismiss` with user_id

### Triage Panel (Sheet)
- Opens on any card click; title changes to "Modifier l'assignation" in editMode
- Section 1: severity badge, alert type, machine name, message, created_at timestamp
- Section 2: technician Select (with availability warning), priority Select, due date Popover+Calendar, Créer OT checkbox
- Section 3: "Ignorer alerte" (dismiss) + "Assigner & Notifier" (disabled until tech selected)
- closePanel() helper resets all triage state on close

### Edit mode
- Technician lane card edit button → handleCardClick(alert, true)
- Opens same triage panel with editMode=true
- Form pre-fills with empty values (createWO=false)
