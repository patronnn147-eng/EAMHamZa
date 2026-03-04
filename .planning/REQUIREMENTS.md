# Requirements

**Project:** EAMSagemCom
**Updated:** 2026-03-04

---

## Phase 1: Identity & Access

### IA-01: User Authentication
**Type:** Security
**Description:** Implement secure JWT-based authentication with refresh tokens

**Acceptance Criteria:**
- [ ] Users can register with email/password
- [ ] Users can login and receive JWT access token
- [ ] Access tokens expire appropriately (15-30 min)
- [ ] Refresh token rotation implemented
- [ ] Passwords hashed with Argon2

---

### IA-02: Role-Based Access Control (RBAC)
**Type:** Security
**Description:** Enforce role-based permissions across all API endpoints

**Acceptance Criteria:**
- [ ] Four roles: ADMIN, CHEFTECH, CHETOP, TECHNICIEN
- [ ] Backend validates role on each protected endpoint
- [ ] Frontend route guards prevent unauthorized access
- [ ] Role permissions documented

---

### IA-03: Session Management
**Type:** Security
**Description:** Manage user sessions securely

**Acceptance Criteria:**
- [ ] Single session enforcement (optional - user preference)
- [ ] Session timeout handling
- [ ] Logout invalidates tokens
- [ ] Secure token storage (httpOnly cookies)

---

### IA-04: User Management
**Type:** Feature
**Description:** Admin user management capabilities

**Acceptance Criteria:**
- [ ] Admin can view all users
- [ ] Admin can create new users
- [ ] Admin can update user details
- [ ] Admin can deactivate/reactivate users
- [ ] User approval workflow (pending users)

---

## Phase 2: Core EAM Features

### EAM-01: Machine Management
**Type:** Feature
**Description:** CRUD operations for machines

**Acceptance Criteria:**
- [ ] Create, read, update, delete machines
- [ ] Machine status tracking
- [ ] Machine location/zones

---

### EAM-02: Work Orders
**Type:** Feature
**Description:** Work order creation and management

**Acceptance Criteria:**
- [ ] Create work orders
- [ ] Assign to technicians
- [ ] Track status (pending, in-progress, completed)
- [ ] Link to machines

---

### EAM-03: Planning & Scheduling
**Type:** Feature
**Description:** Schedule maintenance and interventions

**Acceptance Criteria:**
- [ ] Calendar view for plannings
- [ ] Assign technicians to time slots
- [ ] Link plannings to machines and work orders

---

## Phase 3: ML Integration

### ML-01: Predictive Maintenance
**Type:** Feature
**Description:** ML-powered failure prediction

**Acceptance Criteria:**
- [ ] Train model on AI4I 2020 dataset
- [ ] Predict failure probability
- [ ] Calculate Remaining Useful Life (RUL)
- [ ] Display predictions in UI

---

### ML-02: Anomaly Detection
**Type:** Feature
**Description:** Detect anomalous machine behavior

**Acceptance Criteria:**
- [ ] Analyze sensor data for anomalies
- [ ] Alert on abnormal patterns
- [ ] Historical anomaly log

---

## Phase 4: Reporting & Analytics

### RPT-01: Dashboards
**Type:** Feature
**Description:** Role-specific dashboards

**Acceptance Criteria:**
- [ ] Admin dashboard with overview
- [ ] Technician dashboard with assignments
- [ ] ChefTech dashboard with team metrics
- [ ] Real-time data updates

---

### RPT-02: Reports & Export
**Type:** Feature
**Description:** Generate and export reports

**Acceptance Criteria:**
- [ ] Export work order reports
- [ ] Machine reliability reports
- [ ] Intervention history

---

*Requirements defined: 2026-03-04*
