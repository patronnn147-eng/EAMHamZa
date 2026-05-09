---
phase: 12-cheftech-alert-response-workflow-page
plan: "03"
status: complete
---

## What was done

Wired routing and navigation for the ChefTechAlertWorkflow page.

### AppRoutes.tsx
- Added import: `import ChefTechAlertWorkflow from '@/modules/cheftech/ChefTechAlertWorkflow';` (line 59)
- Added route after `/alerts` route:
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
- Existing `/alerts` route unchanged (still accessible to ADMIN, CHEFTECH, CHETOP, TECHNICIEN)

### Sidebar.tsx
- Added to CHEFTECH nav block (line 83), immediately after 'Alertes Prédictives':
  ```typescript
  { name: 'Centre des alertes', href: '/cheftech/alerts', icon: Bell },
  ```
- 'Alertes Prédictives' entry unchanged
- Bell icon reused (already imported)
- ADMIN, CHETOP, TECHNICIEN blocks untouched
