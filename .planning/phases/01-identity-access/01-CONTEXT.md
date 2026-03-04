# Phase 1: Identity & Access - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning
**Source:** User discussion

---

<domain>
## Phase Boundary

Implement complete identity and access management:
- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- Secure session management
- User management CRUD

**Existing codebase:** JWT auth exists in `app/backend/core/auth.py`, uses Argon2 hashing, 4 roles defined in `models/utilisateurs.py`

</domain>

<decisions>
## Implementation Decisions

### Authentication
- **JWT + Refresh Token:** Use access token (15 min) + refresh token (7 days) with rotation
- **Token Storage:** httpOnly cookies for security
- **Password Hashing:** Continue using Argon2 (already implemented)

### Registration
- **Self-registration:** Option A — users can register themselves, require admin approval before login
- **Approval workflow:** New users require admin approval before login

### Session Management
- **Multiple sessions:** Option A — allow multiple sessions on different devices
- **Session timeout:** Option C — 8 hours (work day)

### RBAC
- **Backend enforcement:** All protected endpoints validate role
- **Frontend guards:** Route-level protection based on user.role

### User Management
- **Admin capabilities:** Create, read, update, deactivate users
- **User fields:** email, name, role, zone_travail, is_active, created_at

</decisions>

<specifics>
## Specific Ideas

**From existing code:**
- `app/backend/core/auth.py` — JWT create/decode, password verify
- `app/backend/models/utilisateurs.py` — User model with roles: ADMIN, CHEFTECH, CHETOP, TECHNICIEN
- `app/frontend/src/lib/auth.ts` — Frontend auth utilities
- `app/frontend/src/contexts/AuthContext.tsx` — Auth state management

**API endpoints needed:**
- POST /api/v1/auth/login
- POST /api/v1/auth/register
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
- GET /api/v1/users (admin)
- POST /api/v1/users (admin)
- PUT /api/v1/users/{id} (admin)
- PATCH /api/v1/users/{id}/activate (admin)
- PATCH /api/v1/users/{id}/deactivate (admin)

</specifics>

<deferred>
## Deferred Ideas

- Email verification (future phase)
- Password reset flow (future phase)
- Two-factor authentication (future phase)
- OAuth/SSO integration (future phase)

</deferred>

---

*Phase: 01-identity-access*
*Context gathered: 2026-03-04*
