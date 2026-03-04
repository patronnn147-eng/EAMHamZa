# Phase 1: Identity & Access - Research

**Researched:** 2026-03-04
**Phase:** 01 - Identity & Access

---

## What We Need to Know

### Current State
- JWT authentication exists in `app/backend/core/auth.py`
- Uses Argon2 for password hashing
- Four roles: ADMIN, CHEFTECH, CHETOP, TECHNICIEN
- User model in `models/utilisateurs.py`

### Implementation Questions

#### 1. Refresh Token Flow
- Need to implement refresh token rotation
- Store refresh tokens in database or use JWT with rotation
- httpOnly cookie storage

#### 2. Self-Registration
- Create registration endpoint
- Set `is_active=False` by default (pending approval)
- Admin approval workflow needed

#### 3. Session Management
- Track active sessions per user
- 8-hour access token expiry
- Allow multiple sessions (no single-session enforcement)

#### 4. Backend RBAC
- Current: `get_current_user` dependency
- Need: Role validation on each endpoint
- Create dependency for role checking: `require_role([ADMIN, CHEFTECH])`

#### 5. Frontend Route Guards
- Current: `AuthContext` with user info
- Need: Protected routes, role-based redirects

---

## Common Pitfalls

1. **Token storage in localStorage** — Use httpOnly cookies instead
2. **No refresh token rotation** — Security risk if token stolen
3. **Role checks on frontend only** — Always validate on backend
4. **No session invalidation on logout** — Must invalidate tokens

---

## Implementation Approach

1. **Auth Module (`app/backend/modules/auth/`)**
   - Enhance existing auth.py with refresh token logic
   - Add registration endpoint
   - Add logout that invalidates refresh token

2. **User Management (`app/backend/routers/admin_users.py`)**
   - Add approval endpoints
   - Add activate/deactivate endpoints

3. **Dependencies (`app/backend/dependencies/auth.py`)**
   - Add role-based dependencies
   - Add refresh token validation

4. **Frontend (`app/frontend/src/`)**
   - Update AuthContext for new auth flow
   - Add ProtectedRoute component
   - Update login/register forms

---

*Research complete: 2026-03-04*
