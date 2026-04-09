# Asset Management Software - Development Plan

## Design Guidelines

### Design References
- **Asana.com**: Clean task management interface
- **Monday.com**: Visual workflow boards
- **Style**: Modern Professional + Dashboard + Enterprise Software

### Color Palette
- Primary: #2563EB (Blue - primary actions)
- Secondary: #64748B (Slate - secondary elements)
- Success: #10B981 (Green - completed status)
- Warning: #F59E0B (Amber - pending status)
- Danger: #EF4444 (Red - urgent priority)
- Background: #F8FAFC (Light Gray)
- Text: #0F172A (Dark Slate), #64748B (Gray - secondary)

### Typography
- Heading1: Inter font-weight 700 (32px)
- Heading2: Inter font-weight 600 (24px)
- Heading3: Inter font-weight 600 (18px)
- Body/Normal: Inter font-weight 400 (14px)
- Body/Emphasis: Inter font-weight 600 (14px)
- Navigation: Inter font-weight 500 (14px)

### Key Component Styles
- **Buttons**: Primary blue (#2563EB), white text, 6px rounded, hover: darken 10%
- **Cards**: White background, 1px border (#E2E8F0), 8px rounded, subtle shadow
- **Forms**: Light inputs with border, focus: blue accent ring
- **Status Badges**: Rounded pills with color-coded backgrounds
- **Tables**: Striped rows, hover highlight, sortable headers

### Layout & Spacing
- Dashboard: Grid layout with metric cards and charts
- Content padding: 24px
- Card spacing: 16px gaps
- Section padding: 32px vertical

### Images to Generate
1. **dashboard-hero.jpg** - Modern office workspace with computers and equipment (Style: photorealistic, bright professional)
2. **machine-placeholder.jpg** - Industrial machinery in factory setting (Style: photorealistic, industrial)
3. **maintenance-icon.png** - Wrench and gear icon for maintenance (Style: minimalist icon, blue accent)
4. **report-background.jpg** - Clean desk with documents and laptop (Style: photorealistic, professional)

---

## Development Tasks

### Phase 1: Backend Setup & Database Schema

1. **Database Tables Creation**
   - Create Utilisateur table with role enum (CHETOP, TECHNICIEN, CHEFTECH, ADMIN)
   - Create Machine table with status enum (EN_ATTENTE, EN_COURS, TERMINE, ANNULE)
   - Create Ordre table with basic fields
   - Create OrdreTravail table with priority enum (BASSE, MOYENNE, ÉLEVÉE, URGENTE)
   - Create OrdreIntervention table
   - Create Planning table with type enum (JOURNALIER, HEBDOMADAIRE, MENSUEL, MAINTENANCE)
   - Create Archive table with type enum (DOCUMENT, IMAGE, VIDEO, AUTRE)
   - Create Rapport table
   - Create MaintenancePlanifiée table
   - Set up all relationships and foreign keys

2. **Insert Mock Data**
   - Insert sample users with different roles
   - Insert sample machines with various statuses
   - Insert sample orders and work orders
   - Insert sample planning entries
   - Insert sample reports

3. **ObjectStorage Setup**
   - Create bucket for archive documents
   - Create bucket for machine images

### Phase 2: Authentication & User Management

4. **Authentication System**
   - Install frontend dependencies (@metagptx/web-sdk)
   - Create AuthCallback page for login handling
   - Update App.tsx with auth routes
   - Create login page with form validation
   - Implement logout functionality
   - Add user profile display in header

5. **User Management Interface**
   - Create user list page with table
   - Create user detail/edit form
   - Implement password change functionality
   - Add role-based access control checks

### Phase 3: Core Modules

6. **Machine Management**
   - Create machines list page with filtering
   - Create machine detail page
   - Create machine create/edit form
   - Implement status update functionality
   - Add maintenance date tracking

7. **Order Management**
   - Create orders list page
   - Create order detail page with work orders
   - Create order create/edit form
   - Implement status workflow
   - Link orders to work orders

8. **Work Order Management**
   - Create work orders list with priority filtering
   - Create work order detail page
   - Create work order create/edit form
   - Implement user assignment
   - Implement machine assignment
   - Link to interventions

9. **Planning Module**
   - Create planning calendar view
   - Create planning list view
   - Create planning create/edit form
   - Implement user assignment to planning
   - Show work orders in planning

### Phase 4: Advanced Features

10. **Archive System**
    - Create archive list page
    - Implement file upload to ObjectStorage
    - Create archive detail view
    - Implement document download
    - Add search and filtering

11. **Reporting Module**
    - Create reports list page
    - Create report generation form
    - Implement report viewing
    - Link reports to users and maintenance

12. **Dashboard & Analytics**
    - Create main dashboard with metrics
    - Add charts for machine status distribution
    - Add urgent work orders widget
    - Add upcoming maintenance widget
    - Add recent activities feed
    - Implement role-specific dashboard views

### Phase 5: UI/UX Polish

13. **Navigation & Layout**
    - Create main navigation with role-based menu
    - Create header with user profile
    - Create sidebar navigation
    - Implement breadcrumbs
    - Add responsive mobile menu

14. **Forms & Validation**
    - Add form validation for all forms
    - Implement error handling
    - Add loading states
    - Add success/error toasts

15. **Final Testing & Optimization**
    - Test all CRUD operations
    - Test role-based access
    - Test file upload/download
    - Run lint and build
    - Fix any remaining issues

---

## File Structure

```
/workspace/app/
├── backend/
│   ├── models/          # Auto-generated ORM models
│   ├── routers/         # Auto-generated API routes
│   ├── services/        # Auto-generated business logic
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/      # Shadcn components
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── MainLayout.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── MetricCard.tsx
│   │   │   │   ├── StatusChart.tsx
│   │   │   │   └── RecentActivities.tsx
│   │   │   ├── machines/
│   │   │   │   ├── MachineCard.tsx
│   │   │   │   ├── MachineForm.tsx
│   │   │   │   └── MachineStatusBadge.tsx
│   │   │   ├── orders/
│   │   │   │   ├── OrderCard.tsx
│   │   │   │   └── OrderForm.tsx
│   │   │   ├── workorders/
│   │   │   │   ├── WorkOrderCard.tsx
│   │   │   │   ├── WorkOrderForm.tsx
│   │   │   │   └── PriorityBadge.tsx
│   │   │   ├── planning/
│   │   │   │   ├── PlanningCalendar.tsx
│   │   │   │   └── PlanningForm.tsx
│   │   │   └── archives/
│   │   │       ├── ArchiveList.tsx
│   │   │       └── FileUpload.tsx
│   │   ├── pages/
│   │   │   ├── Index.tsx           # Dashboard
│   │   │   ├── Login.tsx
│   │   │   ├── AuthCallback.tsx
│   │   │   ├── Machines.tsx
│   │   │   ├── MachineDetail.tsx
│   │   │   ├── Orders.tsx
│   │   │   ├── OrderDetail.tsx
│   │   │   ├── WorkOrders.tsx
│   │   │   ├── WorkOrderDetail.tsx
│   │   │   ├── Planning.tsx
│   │   │   ├── Archives.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── Users.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # API client setup
│   │   │   └── types.ts         # TypeScript types
│   │   └── App.tsx
│   └── public/
│       └── assets/              # Generated images
```

---

## Technical Notes

- Use Atoms Backend for authentication, database, and file storage
- All database operations through BackendManager
- File uploads to ObjectStorage buckets
- Role-based access control on both frontend and backend
- Responsive design for mobile and desktop
- Form validation with react-hook-form
- Data fetching with @metagptx/web-sdk