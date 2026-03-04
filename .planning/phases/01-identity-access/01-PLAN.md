---
phase: 01-identity-access
plan: '01'
type: execute
wave: '1'
depends_on: []
files_modified:
  - app/backend/core/auth.py
  - app/backend/modules/auth/auth.py
  - app/backend/dependencies/auth.py
  - app/backend/routers/admin_users.py
  - app/backend/models/utilisateurs.py
  - app/frontend/src/lib/auth.ts
  - app/frontend/src/contexts/AuthContext.tsx
  - app/frontend/src/app/routing/ProtectedRoute.tsx
  - app/frontend/src/app/routing/AppRoutes.tsx
autonomous: true
requirements:
  - IA-01
  - IA-02
  - IA-03
  - IA-04
user_setup: []

must_haves:
  truths:
    - Users can register and receive pending status until admin approval
    - Users can login with valid credentials and receive JWT tokens
    - Protected API endpoints validate both authentication and role
    - Frontend routes redirect unauthorized users
    - Admins can approve, deactivate, and manage users
  artifacts:
    - path: app/backend/modules/auth/auth.py
      provides: Auth endpoints (login, register, refresh, logout)
    - path: app/backend/dependencies/auth.py
      provides: Role-based access dependencies
    - path: app/backend/routers/admin_users.py
      provides: User management CRUD endpoints
    - path: app/frontend/src/contexts/AuthContext.tsx
      provides: Frontend auth state with refresh token handling
    - path: app/frontend/src/app/routing/ProtectedRoute.tsx
      provides: Route guards for protected pages
  key_links:
    - from: app/frontend/src/contexts/AuthContext.tsx
      to: app/backend/modules/auth/auth.py
      via: HTTP requests to /api/v1/auth/*
      pattern: fetch.*auth
    - from: app/frontend/src/app/routing/ProtectedRoute.tsx
      to: app/frontend/src/contexts/AuthContext.tsx
      via: useAuth() hook
      pattern: useAuth
---

<objective>
Implement complete Identity & Access management: JWT auth with refresh tokens, RBAC, session management, and user management with admin approval workflow.
</objective>

<context>
@.planning/phases/01-identity-access/01-CONTEXT.md
@.planning/phases/01-identity-access/01-RESEARCH.md
@.planning/REQUIREMENTS.md
@app/backend/core/auth.py
@app/backend/models/utilisateurs.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement Backend Auth Endpoints</name>
  <files>app/backend/modules/auth/auth.py, app/backend/dependencies/auth.py</files>
  <action>
    Enhance auth module with:
    1. POST /register - Create user with is_active=False (pending approval)
    2. POST /login - Return access + refresh tokens in httpOnly cookies
    3. POST /refresh - Refresh access token using refresh token (with rotation)
    4. POST /logout - Invalidate refresh token
    5. GET /me - Return current user info
    
    Use access token (15 min) + refresh token (7 days) with rotation.
    Store refresh tokens in database or use signed JWT.
    Use httpOnly, Secure, SameSite=Strict cookies.
  </action>
  <verify>
    <automated>Test endpoints with curl: 
    curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"Test123!","name":"Test User","role":"TECHNICIEN"}'
    curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"Test123!"}'</automated>
  </verify>
  <done>All auth endpoints functional: register returns user with pending status, login returns tokens in cookies, refresh rotates token, logout invalidates</done>
</task>

<task type="auto">
  <name>Task 2: Implement RBAC Dependencies</name>
  <files>app/backend/dependencies/auth.py</files>
  <action>
    Create role-based access dependencies:
    1. require_auth - User must be authenticated
    2. require_role(roles: List[Role]) - User must have one of specified roles
    3. get_current_active_user - Returns user only if is_active=True
    
    Apply to all protected endpoints in routers.
  </action>
  <verify>
    <automated>Test role restriction:
    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/admin/users
    (Should return 403 for non-admin)</automated>
  </verify>
  <done>Protected endpoints enforce role validation, returns 403 for unauthorized</done>
</task>

<task type="auto">
  <name>Task 3: Implement Admin User Management</name>
  <files>app/backend/routers/admin_users.py</files>
  <action>
    Add admin user management endpoints:
    1. GET /users - List all users (admin only)
    2. GET /users/pending - List users awaiting approval
    3. PATCH /users/{id}/approve - Approve and activate user
    4. PATCH /users/{id}/deactivate - Deactivate user
    5. PUT /users/{id} - Update user details
  </action>
  <verify>
    <automated>Test admin endpoints with admin token:
    curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/api/v1/admin/users</automated>
  </verify>
  <done>Admin can view, approve, and manage all users</done>
</task>

<task type="auto">
  <name>Task 4: Update Frontend Auth Context</name>
  <files>app/frontend/src/contexts/AuthContext.tsx, app/frontend/src/lib/auth.ts</files>
  <action>
    Update frontend auth handling:
    1. AuthContext handles automatic token refresh
    2. Store tokens in memory (not localStorage for security)
    3. Add login/register API calls
    4. Handle 401 responses by attempting refresh
    5. Clear auth state on logout
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>Frontend auth state works with new backend: login, logout, token refresh all functional</done>
</task>

<task type="auto">
  <name>Task 5: Implement Frontend Route Guards</name>
  <files>app/frontend/src/app/routing/ProtectedRoute.tsx, app/frontend/src/app/routing/AppRoutes.tsx</files>
  <action>
    Implement route protection:
    1. ProtectedRoute component - checks auth and role
    2. Update AppRoutes to wrap protected routes
    3. Add role-based redirects (technician → dashboard, admin → admin page)
    4. Handle pending approval state (show "waiting approval" message)
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>Protected routes redirect unauthorized users, role-based access enforced</done>
</task>

</tasks>

<verification>
- All API endpoints functional and return correct status codes
- Role validation works on both backend and frontend
- User registration creates pending users
- Admin can approve pending users
- Login/logout flow works with token refresh
</verification>

<success_criteria>
- Users can register (pending until approval)
- Users can login with JWT tokens
- Protected endpoints validate authentication AND role
- Frontend routes protected with guards
- Admin can manage users (approve, deactivate)
</success_criteria>

<output>
After completion, create `.planning/phases/01-identity-access/01-01-SUMMARY.md`
</output>
