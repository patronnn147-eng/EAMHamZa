# Backend Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the top-level `routers/` package by moving its files into `modules/`, then split every backend file exceeding 350 lines into focused sub-files inside `routes/` sub-folders. `main.py` auto-discovery requires zero changes.

**Architecture:** `main.py` calls `include_routers_from_package(app, "modules")` which uses `pkgutil.walk_packages` to recursively auto-discover any `router = APIRouter(...)` object inside `modules/`. Any new file placed in a `modules/*/routes/` subfolder (with an `__init__.py`) will be picked up automatically. Shared Pydantic schemas for a module go in a `schemas.py` sibling file; dependency functions go in `dependencies.py`.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Pydantic v2. Working directory for all commands: `app/backend/`.

---

## Standard Split Pattern (read this once, applied to every task)

Every module split follows this pattern:

1. Create `modules/<module>/routes/__init__.py` (empty file, makes it a package)
2. Extract Pydantic models from the original file → `modules/<module>/schemas.py`
3. Extract dependency injection functions → `modules/<module>/dependencies.py` (if any)
4. Create route sub-files in `modules/<module>/routes/`; each file uses this header:
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   # ... other imports from original file (copy only what this file needs)
   from ..schemas import ModelA, ModelB          # local schemas
   from ..dependencies import verify_role         # local deps (if any)

   router = APIRouter(prefix="/api/v1/<module>", tags=["<module>"])
   ```
5. Delete the original oversized file
6. Remove its explicit import from `main.py` if one exists (see Task 1)
7. Verify: `python -c "from modules.<module>.routes.<file> import router; print('OK')"`
8. Commit

---

## Phase A — Routing Consolidation (eliminate `routers/` package)

### Task 1: Update `main.py` — remove broken explicit imports

The following explicit imports in `main.py` will break when their source files are deleted or reorganized. Remove them now, before any files change.

**Files:**
- Modify: `main.py:166-186`

- [ ] **Step 1: Open `main.py` and remove lines 170–186 (the explicit fallback imports block)**

  Remove these lines entirely:
  ```python
  # Explicitly register critical routers if auto-discovery fails
  from modules.chetop.chetop import router as chetop_router
  app.include_router(chetop_router)

  from modules.admin.admin_itv import router as admin_itv_router
  app.include_router(admin_itv_router)

  from modules.admin.admin_work_orders import router as admin_work_orders_router
  app.include_router(admin_work_orders_router)

  from modules.cheftech.cheftech_work_orders import router as cheftech_work_orders_router
  app.include_router(cheftech_work_orders_router)

  from modules.technicien.technicien_work_orders import router as technicien_work_orders_router
  app.include_router(technicien_work_orders_router, prefix="/api/v1/technicien", tags=["technicien_work_orders"])

  from modules.technicien.technicien import router as technicien_router
  app.include_router(technicien_router)
  ```

  Auto-discovery via `include_routers_from_package(app, "modules")` already handles all of these.

- [ ] **Step 2: Verify app still starts**

  ```bash
  python -c "from main import app; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Commit**

  ```bash
  git add main.py
  git commit -m "refactor: remove redundant explicit router imports from main.py"
  ```

---

### Task 2: Move `routers/admin_users.py` + `routers/admin_analytics.py` + `routers/user_approvals.py` → `modules/admin/routes/`

**Files:**
- Create: `modules/admin/routes/__init__.py`
- Create: `modules/admin/routes/users.py` (from `routers/admin_users.py`)
- Create: `modules/admin/routes/analytics.py` (from `routers/admin_analytics.py`)
- Create: `modules/admin/routes/approvals.py` (from `routers/user_approvals.py`)
- Delete: `routers/admin_users.py`, `routers/admin_analytics.py`, `routers/user_approvals.py`

- [ ] **Step 1: Create `modules/admin/routes/__init__.py`**

  ```python
  # modules/admin/routes/__init__.py
  ```

- [ ] **Step 2: Copy `routers/admin_users.py` → `modules/admin/routes/users.py`** (no content changes needed — the file is already under 350 lines)

- [ ] **Step 3: Copy `routers/admin_analytics.py` → `modules/admin/routes/analytics.py`**

- [ ] **Step 4: Copy `routers/user_approvals.py` → `modules/admin/routes/approvals.py`**

- [ ] **Step 5: Delete the original files**

  ```bash
  rm routers/admin_users.py routers/admin_analytics.py routers/user_approvals.py
  ```

- [ ] **Step 6: Verify all three routers import correctly**

  ```bash
  python -c "
  from modules.admin.routes.users import router
  from modules.admin.routes.analytics import router as r2
  from modules.admin.routes.approvals import router as r3
  print('OK')
  "
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add modules/admin/routes/ routers/
  git commit -m "refactor: move admin routers from routers/ into modules/admin/routes/"
  ```

---

### Task 3: Move `routers/notifications.py` → `modules/shared/routes/notifications.py`

**Files:**
- Create: `modules/shared/routes/__init__.py`
- Create: `modules/shared/routes/notifications.py`
- Delete: `routers/notifications.py`

- [ ] **Step 1: Create `modules/shared/routes/__init__.py`**

  ```python
  # modules/shared/routes/__init__.py
  ```

- [ ] **Step 2: Copy `routers/notifications.py` → `modules/shared/routes/notifications.py`** (no content changes needed — 330 lines, under limit)

- [ ] **Step 3: Delete original**

  ```bash
  rm routers/notifications.py
  ```

- [ ] **Step 4: Verify**

  ```bash
  python -c "from modules.shared.routes.notifications import router; print('OK')"
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add modules/shared/routes/ routers/
  git commit -m "refactor: move notifications router from routers/ into modules/shared/routes/"
  ```

---

### Task 4: Split `routers/plannings.py` (922 lines) → `modules/shared/routes/planning/`

**Files:**
- Create: `modules/shared/routes/planning/__init__.py`
- Create: `modules/shared/routes/planning/schemas.py` (Pydantic models from lines 53–131)
- Create: `modules/shared/routes/planning/helpers.py` (utility functions from lines 35–51, 133–318)
- Create: `modules/shared/routes/planning/read.py` (routes: list, get-by-id, get-machines)
- Create: `modules/shared/routes/planning/write.py` (routes: create, delete, resend-emails)
- Create: `modules/shared/routes/planning/update.py` (routes: update, get-users-by-role)
- Delete: `routers/plannings.py`

- [ ] **Step 1: Create `modules/shared/routes/planning/__init__.py`**

  ```python
  # modules/shared/routes/planning/__init__.py
  ```

- [ ] **Step 2: Create `modules/shared/routes/planning/schemas.py`**

  Copy lines 53–131 from `routers/plannings.py` (the Pydantic model classes: `PlanningCreateData`, `PlanningUpdateData`, `PlanningResponse`, `UserOption`, `PlanningMachineResponse`). Add the required imports at the top:

  ```python
  from datetime import datetime
  from typing import List, Optional
  from pydantic import BaseModel, Field
  ```

- [ ] **Step 3: Create `modules/shared/routes/planning/helpers.py`**

  Copy lines 35–51 (`_serialize_planning_for_email`) and lines 133–318 (the four async helper functions: `verify_admin`, `get_user_by_id`, `validate_planning_data`, `send_planning_notifications`, `get_planning_with_users`). Add required imports at the top:

  ```python
  import logging
  from datetime import datetime
  from typing import List, Optional
  from fastapi import HTTPException
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select, func, delete
  from sqlalchemy.orm import selectinload
  from core.auth import get_current_user
  from models.utilisateurs import Utilisateurs, UserRole
  from models.plannings import Plannings, PlanningType, ShiftType
  from models.planning_machines import Planning_machines
  # ... copy any other imports referenced in these functions
  from .schemas import PlanningCreateData, PlanningResponse
  ```

- [ ] **Step 4: Create `modules/shared/routes/planning/read.py`**

  Header:
  ```python
  import logging
  from typing import List, Optional
  from fastapi import APIRouter, Depends, HTTPException, Query
  from sqlalchemy.ext.asyncio import AsyncSession
  from schemas.pagination import PaginatedResponse
  from core.database import get_db
  from core.auth import get_current_user
  from models.utilisateurs import Utilisateurs, UserRole
  from models.plannings import Plannings, PlanningType, ShiftType
  from models.planning_machines import Planning_machines
  from .schemas import PlanningResponse, PlanningMachineResponse, UserOption
  from .helpers import verify_admin, get_planning_with_users

  router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
  logger = logging.getLogger(__name__)
  ```

  Routes to include:
  - `list_plannings` (GET `/`) — lines 353–450
  - `get_planning` (GET `/{planning_id}`) — lines 451–503
  - `get_planning_machines` (GET `/{planning_id}/machines`) — lines 504–562

- [ ] **Step 5: Create `modules/shared/routes/planning/write.py`**

  Header (same imports as read.py, plus email/task imports):
  ```python
  import logging
  from typing import List, Optional
  from fastapi import APIRouter, Depends, HTTPException, status
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select, delete
  from sqlalchemy.orm import selectinload
  from core.database import get_db
  from core.auth import get_current_user
  from models.utilisateurs import Utilisateurs, UserRole
  from models.plannings import Plannings, PlanningType, ShiftType
  from models.planning_machines import Planning_machines
  from .schemas import PlanningResponse, PlanningCreateData
  from .helpers import verify_admin, validate_planning_data, send_planning_notifications, get_planning_with_users

  router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
  logger = logging.getLogger(__name__)
  ```

  Routes to include:
  - `create_planning` (POST `/`) — lines 563–690
  - `resend_planning_emails` (POST `/{planning_id}/resend-emails`) — lines 838–881
  - `delete_planning` (DELETE `/{planning_id}`) — lines 882–922

- [ ] **Step 6: Create `modules/shared/routes/planning/update.py`**

  Same header as write.py, plus `PlanningUpdateData`. Routes to include:
  - `get_users_by_role` (GET `/users/by-role/{role}`) — lines 320–351
  - `update_planning` (PUT `/{planning_id}`) — lines 691–837

- [ ] **Step 7: Delete original**

  ```bash
  rm routers/plannings.py
  ```

- [ ] **Step 8: Verify**

  ```bash
  python -c "
  from modules.shared.routes.planning.read import router
  from modules.shared.routes.planning.write import router as r2
  from modules.shared.routes.planning.update import router as r3
  print('OK')
  "
  ```

- [ ] **Step 9: Delete `routers/` package if now empty, and remove its discovery call from main.py**

  ```bash
  ls routers/   # should only contain __init__.py
  rm -rf routers/
  ```

  In `main.py`, remove line 166: `include_routers_from_package(app, "routers")`

- [ ] **Step 10: Verify app starts**

  ```bash
  python -c "from main import app; print('OK')"
  ```

- [ ] **Step 11: Commit**

  ```bash
  git add modules/shared/routes/planning/ routers/ main.py
  git commit -m "refactor: split plannings router (922 lines) into modules/shared/routes/planning/"
  ```

---

## Phase B — Module File Splits

### Task 5: Split `modules/cheftech/cheftech.py` (945 lines)

**Files:**
- Create: `modules/cheftech/schemas.py`
- Create: `modules/cheftech/dependencies.py`
- Create: `modules/cheftech/routes/__init__.py`
- Create: `modules/cheftech/routes/interventions.py`
- Create: `modules/cheftech/routes/work_orders.py`
- Create: `modules/cheftech/routes/analytics.py`
- Delete: `modules/cheftech/cheftech.py`

- [ ] **Step 1: Create `modules/cheftech/schemas.py`**

  Copy all Pydantic `class` definitions from `cheftech.py` (lines ~32–145: `InterventionResponse`, `WorkOrderResponse`, `TechnicianResponse`, `MachineResponse`, `CompletedWorkOrderItem`, `DashboardStats`, and any other BaseModel subclasses). Add their imports.

- [ ] **Step 2: Create `modules/cheftech/dependencies.py`**

  ```python
  from fastapi import Depends, HTTPException
  from models.utilisateurs import Utilisateurs, UserRole
  from core.auth import get_current_user

  async def verify_management_access(current_user: Utilisateurs = Depends(get_current_user)):
      if current_user.role not in [UserRole.cheftech, UserRole.admin]:
          raise HTTPException(status_code=403, detail="Access denied")
      return current_user

  async def verify_cheftech(current_user: Utilisateurs = Depends(verify_management_access)):
      return current_user

  async def verify_cheftech_or_admin(current_user: Utilisateurs = Depends(verify_management_access)):
      return current_user
  ```

  (Copy the exact implementations from `cheftech.py` lines 146–155.)

- [ ] **Step 3: Create `modules/cheftech/routes/__init__.py`** (empty)

- [ ] **Step 4: Create `modules/cheftech/routes/interventions.py`**

  Header:
  ```python
  import logging
  from typing import List, Optional
  from fastapi import APIRouter, Depends, Query
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import and_, or_, select, func
  from sqlalchemy.orm import selectinload
  from schemas.pagination import PaginatedResponse
  from core.database import get_db
  from models.ordres_intervention import Ordres_intervention
  from models.machines import Machines
  from models.ordres_travail import Ordres_travail
  from models.utilisateurs import Utilisateurs
  from ..schemas import InterventionResponse, DashboardStats
  from ..dependencies import verify_cheftech

  router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])
  logger = logging.getLogger(__name__)
  ```

  Routes to include:
  - `get_dashboard_stats` (GET `/dashboard`) — lines 157–208
  - `get_interventions` (GET `/interventions`) — lines 209–294

- [ ] **Step 5: Create `modules/cheftech/routes/work_orders.py`**

  Same header but also import `WorkOrderResponse`, `CompletedWorkOrderItem`, RabbitMQ, tasks. Routes:
  - `get_work_orders` (GET `/ordres-travail`) — lines 295–351
  - `assign_work_order` (POST `/ordres-travail/{ordre_id}/assign`) — lines 443–624
  - `get_completed_work_orders` (GET `/completed-work-orders`) — lines 685–789
  - `add_cheftech_feedback` (PUT `/work-orders/{ordre_id}/feedback`) — lines 790–813

- [ ] **Step 6: Create `modules/cheftech/routes/analytics.py`**

  Routes:
  - `get_technicians` (GET `/techniciens`) — lines 352–390
  - `get_machines` (GET `/machines`) — lines 391–442
  - `update_machine_status` (PUT `/machines/{machine_id}/status`) — lines 625–684
  - `get_kpi_report` (GET `/reports/kpi`) — lines 814–858
  - `get_cheftech_analytics_dashboard` (GET `/analytics/dashboard`) — lines 859–945

- [ ] **Step 7: Verify each file is under 350 lines**

  ```bash
  wc -l modules/cheftech/routes/interventions.py modules/cheftech/routes/work_orders.py modules/cheftech/routes/analytics.py
  ```
  All must be ≤ 350. If `work_orders.py` exceeds 350, move `get_completed_work_orders` + `add_cheftech_feedback` to `analytics.py`.

- [ ] **Step 8: Delete original and verify**

  ```bash
  rm modules/cheftech/cheftech.py
  python -c "
  from modules.cheftech.routes.interventions import router
  from modules.cheftech.routes.work_orders import router as r2
  from modules.cheftech.routes.analytics import router as r3
  print('OK')
  "
  ```

- [ ] **Step 9: Commit**

  ```bash
  git add modules/cheftech/
  git commit -m "refactor: split cheftech.py (945 lines) into routes/ subfolder"
  ```

---

### Task 6: Split `modules/chetop/chetop.py` (534 lines)

**Files:**
- Create: `modules/chetop/schemas.py`
- Create: `modules/chetop/routes/__init__.py`
- Create: `modules/chetop/routes/dashboard.py`
- Create: `modules/chetop/routes/work_orders.py`
- Create: `modules/chetop/routes/interventions.py`
- Create: `modules/chetop/routes/machines.py`
- Delete: `modules/chetop/chetop.py`

- [ ] **Step 1: Create `modules/chetop/schemas.py`**

  Copy all Pydantic model classes from `chetop.py` (lines ~38–116: `InterventionRequestCreate`, `WorkOrderResponse`, `InterventionRequestResponse`, `MachineStatusUpdate`, `MachineResponse`, `DashboardStats`, `WorkOrderCompletePayload`).

- [ ] **Step 2: Create `modules/chetop/routes/__init__.py`** (empty)

- [ ] **Step 3: Create `modules/chetop/routes/dashboard.py`**

  Header:
  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from core.database import get_db
  from core.auth import get_current_user
  from models.utilisateurs import Utilisateurs
  from ..schemas import DashboardStats

  router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
  ```

  Routes: `get_dashboard_stats` (GET `/dashboard`) — lines 117–177

- [ ] **Step 4: Create `modules/chetop/routes/interventions.py`**

  Routes:
  - `create_intervention_request` (POST `/intervention-requests`) — lines 178–237
  - `get_my_intervention_requests` (GET `/intervention-requests`) — lines 426–459

- [ ] **Step 5: Create `modules/chetop/routes/work_orders.py`**

  Routes:
  - `get_my_work_orders` (GET `/work-orders`) — lines 238–284
  - `start_work_order` (PATCH `/work-orders/{order_id}/start`) — lines 285–343
  - `complete_work_order` (PATCH `/work-orders/{order_id}/complete`) — lines 344–425

- [ ] **Step 6: Create `modules/chetop/routes/machines.py`**

  Routes:
  - `get_machines` (GET `/machines`) — lines 460–496
  - `update_machine_status` (PUT `/machines/{machine_id}/status`) — lines 497–534

- [ ] **Step 7: Delete original and verify**

  ```bash
  rm modules/chetop/chetop.py
  python -c "
  from modules.chetop.routes.dashboard import router
  from modules.chetop.routes.interventions import router as r2
  from modules.chetop.routes.work_orders import router as r3
  from modules.chetop.routes.machines import router as r4
  print('OK')
  "
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add modules/chetop/
  git commit -m "refactor: split chetop.py (534 lines) into routes/ subfolder"
  ```

---

### Task 7: Split `modules/technicien/technicien.py` (476 lines)

**Files:**
- Create: `modules/technicien/schemas.py`
- Create: `modules/technicien/routes/__init__.py`
- Create: `modules/technicien/routes/machines.py`
- Create: `modules/technicien/routes/interventions.py`
- Delete: `modules/technicien/technicien.py`

- [ ] **Step 1: Create `modules/technicien/schemas.py`**

  Copy Pydantic models from `technicien.py` (lines ~33–140: `InterventionResponse`, `InterventionStatusUpdate`, `InterventionRequestPayload`, `WorkOrderExecutionUpdate`, `MachineResponse`).

- [ ] **Step 2: Create `modules/technicien/routes/__init__.py`** (empty)

- [ ] **Step 3: Create `modules/technicien/routes/machines.py`**

  Header:
  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from core.database import get_db
  from core.auth import get_current_user
  from models.utilisateurs import Utilisateurs
  from models.machines import Machines
  from ..schemas import MachineResponse

  router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])
  ```

  Routes: `get_machines_list` (GET `/machines`) — lines 143–170

- [ ] **Step 4: Create `modules/technicien/routes/interventions.py`**

  Routes:
  - `list_my_interventions` (GET `/interventions`) — lines 171–232
  - `update_intervention_status` (PUT `/interventions/{intervention_id}/status`) — lines 233–370
  - `request_intervention` (POST `/interventions/request`) — lines 371–476

- [ ] **Step 5: Verify interventions.py is under 350 lines**

  ```bash
  wc -l modules/technicien/routes/interventions.py
  ```
  If > 350, move `request_intervention` to a new `modules/technicien/routes/intervention_requests.py`.

- [ ] **Step 6: Delete original and verify**

  ```bash
  rm modules/technicien/technicien.py
  python -c "
  from modules.technicien.routes.machines import router
  from modules.technicien.routes.interventions import router as r2
  print('OK')
  "
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add modules/technicien/
  git commit -m "refactor: split technicien.py (476 lines) into routes/ subfolder"
  ```

---

### Task 8: Split `modules/shared/machines.py` (589 lines)

**Files:**
- Create: `modules/shared/routes/machines/__init__.py`
- Create: `modules/shared/routes/machines/schemas.py`
- Create: `modules/shared/routes/machines/crud.py`
- Create: `modules/shared/routes/machines/import_.py`
- Delete: `modules/shared/machines.py`

Note: `modules/shared/routes/__init__.py` already exists (created in Task 3).

- [ ] **Step 1: Create `modules/shared/routes/machines/__init__.py`** (empty)

- [ ] **Step 2: Create `modules/shared/routes/machines/schemas.py`**

  Copy Pydantic models from `machines.py` (lines ~33–101: `MachinesData`, `MachinesUpdateData`, `MachinesResponse`, `MachinesListResponse`, `MachinesBatchCreateRequest`, `MachinesBatchUpdateItem`, `MachinesBatchUpdateRequest`, `MachinesBatchDeleteRequest`).

- [ ] **Step 3: Create `modules/shared/routes/machines/crud.py`**

  Header:
  ```python
  from typing import List
  from fastapi import APIRouter, Depends, HTTPException
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from core.database import get_db
  from core.auth import get_current_user
  from models.machines import Machines
  from models.utilisateurs import Utilisateurs
  from schemas.pagination import PaginatedResponse
  from .schemas import MachinesData, MachinesUpdateData, MachinesResponse, MachinesListResponse
  from .schemas import MachinesBatchCreateRequest, MachinesBatchUpdateRequest, MachinesBatchDeleteRequest

  router = APIRouter(prefix="/api/v1/machines", tags=["machines"])
  ```

  Routes:
  - `query_machiness` (GET ``) — lines 103–139
  - `query_machiness_all` (GET `/all`) — lines 140–176
  - `get_machines` (GET `/{id}`) — lines 177–200
  - `create_machines` (POST ``) — lines 201–224
  - `create_machiness_batch` (POST `/batch`) — lines 225–249
  - `update_machiness_batch` (PUT `/batch`) — lines 250–276
  - `update_machines` (PUT `/{id}`) — lines 277–306
  - `delete_machiness_batch` (DELETE `/batch`) — lines 307–331
  - `delete_machines` (DELETE `/{id}`) — lines 332–355

- [ ] **Step 4: Create `modules/shared/routes/machines/import_.py`**

  Same header imports. Routes:
  - `download_import_template` (GET `/import/template`) — lines 356–424
  - `preview_machine_import` (POST `/import/preview`) — lines 425–end

- [ ] **Step 5: Delete original and verify**

  ```bash
  rm modules/shared/machines.py
  python -c "
  from modules.shared.routes.machines.crud import router
  from modules.shared.routes.machines.import_ import router as r2
  print('OK')
  "
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add modules/shared/routes/machines/ modules/shared/machines.py
  git commit -m "refactor: split shared/machines.py (589 lines) into routes/machines/"
  ```

---

### Task 9: Split `modules/shared/ordres_intervention.py` (441 lines)

**Files:**
- Create: `modules/shared/routes/ordres_intervention_read.py`
- Create: `modules/shared/routes/ordres_intervention_write.py`
- Delete: `modules/shared/ordres_intervention.py`

- [ ] **Step 1: Create `modules/shared/routes/ordres_intervention_read.py`**

  Copy imports + Pydantic models + router declaration from original. Routes to include:
  - `query_ordres_interventions` (GET ``) — lines 131–167
  - `query_ordres_interventions_all` (GET `/all`) — lines 168–204
  - `get_ordres_intervention` (GET `/{id}`) — lines 205–228

  Header (copy from original, keep `router = APIRouter(...)` with same prefix/tags).

- [ ] **Step 2: Create `modules/shared/routes/ordres_intervention_write.py`**

  Same header. Routes:
  - `create_ordres_intervention` (POST ``) — lines 229–256
  - `create_ordres_interventions_batch` (POST `/batch`) — lines 257–281
  - `update_ordres_interventions_batch` (PUT `/batch`) — lines 282–308
  - `update_ordres_intervention` (PUT `/{id}`) — lines 309–337
  - `validate_ordres_intervention` (POST `/{id}/validate`) — lines 338–395
  - `delete_ordres_interventions_batch` (DELETE `/batch`) — lines 396–420
  - `delete_ordres_intervention` (DELETE `/{id}`) — lines 421–441

- [ ] **Step 3: Delete original and verify**

  ```bash
  rm modules/shared/ordres_intervention.py
  python -c "
  from modules.shared.routes.ordres_intervention_read import router
  from modules.shared.routes.ordres_intervention_write import router as r2
  print('OK')
  "
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add modules/shared/routes/ modules/shared/ordres_intervention.py
  git commit -m "refactor: split shared/ordres_intervention.py (441 lines) into read/write"
  ```

---

### Task 10: Split `modules/shared/ordres_travail.py` (397 lines)

Same pattern as Task 9.

**Files:**
- Create: `modules/shared/routes/ordres_travail_read.py` (GET endpoints: lines 112–209)
- Create: `modules/shared/routes/ordres_travail_write.py` (POST/PUT/DELETE endpoints: lines 210–397)
- Delete: `modules/shared/ordres_travail.py`

- [ ] **Step 1: Create `modules/shared/routes/ordres_travail_read.py`**

  Copy imports + Pydantic models + router. Routes:
  - `query_ordres_travails` (GET ``) — lines 112–148
  - `query_ordres_travails_all` (GET `/all`) — lines 149–185
  - `get_ordres_travail` (GET `/{id}`) — lines 186–209

- [ ] **Step 2: Create `modules/shared/routes/ordres_travail_write.py`**

  Routes: all POST/PUT/DELETE handlers from lines 210–397.

- [ ] **Step 3: Delete original and verify**

  ```bash
  rm modules/shared/ordres_travail.py
  python -c "
  from modules.shared.routes.ordres_travail_read import router
  from modules.shared.routes.ordres_travail_write import router as r2
  print('OK')
  "
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add modules/shared/routes/ modules/shared/ordres_travail.py
  git commit -m "refactor: split shared/ordres_travail.py (397 lines) into read/write"
  ```

---

### Task 11: Split `modules/shared/planning_ordres_travail.py` (367 lines)

**Files:**
- Create: `modules/shared/routes/planning_ordres_read.py` (GET endpoints: lines 81–179)
- Create: `modules/shared/routes/planning_ordres_write.py` (POST/PUT/DELETE endpoints: lines 180–367)
- Delete: `modules/shared/planning_ordres_travail.py`

- [ ] **Step 1: Create `modules/shared/routes/planning_ordres_read.py`**

  Routes:
  - `query_planning_ordres_travails` (GET ``) — lines 81–117
  - `query_planning_ordres_travails_all` (GET `/all`) — lines 118–155
  - `get_planning_ordres_travail` (GET `/{id}`) — lines 156–179

- [ ] **Step 2: Create `modules/shared/routes/planning_ordres_write.py`**

  Routes: all POST/PUT/DELETE handlers from lines 180–367.

- [ ] **Step 3: Delete original and verify**

  ```bash
  rm modules/shared/planning_ordres_travail.py
  python -c "
  from modules.shared.routes.planning_ordres_read import router
  from modules.shared.routes.planning_ordres_write import router as r2
  print('OK')
  "
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add modules/shared/routes/ modules/shared/planning_ordres_travail.py
  git commit -m "refactor: split planning_ordres_travail.py (367 lines) into read/write"
  ```

---

### Task 12: Split `modules/ml/ml_predictive.py` (428 lines)

**Files:**
- Create: `modules/ml/services/prediction_engine.py`
- Create: `modules/ml/services/prediction_features.py`
- Delete: `modules/ml/ml_predictive.py`

`modules/ml/services/` already exists.

- [ ] **Step 1: Inspect the split boundary**

  ```bash
  grep -n "^def \|^class \|^async def " modules/ml/ml_predictive.py
  ```

  Identify: the `MachineLearningService` class starts at line 82. Lines before it (1–81) contain `get_model()` + model loading logic. Split:
  - `prediction_features.py`: lines 1–81 (feature extraction, model loading `get_model()`)
  - `prediction_engine.py`: lines 82–428 (`MachineLearningService` class and methods)

- [ ] **Step 2: Create `modules/ml/services/prediction_features.py`**

  Copy lines 1–81 from `ml_predictive.py` exactly.

- [ ] **Step 3: Create `modules/ml/services/prediction_engine.py`**

  Copy lines 82–428 (`MachineLearningService` class). Add at top:
  ```python
  from .prediction_features import get_model
  ```

- [ ] **Step 4: Update `modules/ml/router.py` and `modules/ml/services/ml_retraining.py`**

  Find all imports of `ml_predictive`:
  ```bash
  grep -rn "from.*ml_predictive\|import.*ml_predictive" modules/ml/
  ```

  Change `from modules.ml.ml_predictive import MachineLearningService` →
  `from modules.ml.services.prediction_engine import MachineLearningService`

  Change `from modules.ml.ml_predictive import get_model` →
  `from modules.ml.services.prediction_features import get_model`

- [ ] **Step 5: Delete original and verify**

  ```bash
  rm modules/ml/ml_predictive.py
  python -c "
  from modules.ml.services.prediction_features import get_model
  from modules.ml.services.prediction_engine import MachineLearningService
  print('OK')
  "
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add modules/ml/
  git commit -m "refactor: split ml_predictive.py (428 lines) into prediction_engine + prediction_features"
  ```

---

### Task 13: Delete `modules/shared/cheftech_old.py`

This file (423 lines) has zero imports from other files — confirmed by grep.

- [ ] **Step 1: Final safety check**

  ```bash
  grep -rn "cheftech_old" . --include="*.py" | grep -v __pycache__
  ```
  Expected: no results other than the file itself.

- [ ] **Step 2: Delete**

  ```bash
  rm modules/shared/cheftech_old.py
  ```

- [ ] **Step 3: Verify app still starts**

  ```bash
  python -c "from main import app; print('OK')"
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add modules/shared/cheftech_old.py
  git commit -m "chore: delete unused cheftech_old.py (legacy file, no importers)"
  ```

---

## Phase C — Services Splits

### Task 14: Split `services/payment.py` (419 lines) → `services/payment/`

`services/payment.py` contains: Pydantic models (lines 12–93), helper `_classify_stripe_error` (94–143), `initialize_stripe()` (144–203), `PaymentService` class (204–380), `CheckoutError` exception (381–419).

**Files:**
- Create: `services/payment/__init__.py` (re-export public API)
- Create: `services/payment/models.py` (Pydantic models + exception)
- Create: `services/payment/stripe_service.py` (`initialize_stripe` + `_classify_stripe_error`)
- Create: `services/payment/service.py` (`PaymentService` class)
- Delete: `services/payment.py`

- [ ] **Step 1: Create `services/payment/models.py`**

  Copy lines 12–93 (Pydantic classes: `CheckoutSessionRequest`, `CheckoutSessionResponse`, `CheckoutStatusResponse`) and lines 381–419 (`CheckoutError`). Add imports.

- [ ] **Step 2: Create `services/payment/stripe_service.py`**

  Copy lines 94–203 (`_classify_stripe_error` + `initialize_stripe`). Add:
  ```python
  import stripe
  from .models import CheckoutError
  # ... other imports referenced in these functions
  ```

- [ ] **Step 3: Create `services/payment/service.py`**

  Copy lines 204–380 (`PaymentService` class). Add:
  ```python
  from .models import CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutError
  from .stripe_service import _classify_stripe_error
  ```

- [ ] **Step 4: Create `services/payment/__init__.py`**

  ```python
  from .service import PaymentService
  from .models import CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutError
  from .stripe_service import initialize_stripe

  __all__ = ["PaymentService", "CheckoutSessionRequest", "CheckoutSessionResponse",
             "CheckoutStatusResponse", "CheckoutError", "initialize_stripe"]
  ```

- [ ] **Step 5: Find and check consumers of `services/payment`**

  ```bash
  grep -rn "from services.payment\|import services.payment" . --include="*.py" | grep -v __pycache__
  ```
  Existing imports like `from services.payment import PaymentService` will continue to work via `__init__.py`.

- [ ] **Step 6: Delete original and verify**

  ```bash
  rm services/payment.py
  python -c "from services.payment import PaymentService; print('OK')"
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add services/payment/ services/payment.py
  git commit -m "refactor: split services/payment.py (419 lines) into payment/ package"
  ```

---

### Task 15: Split `services/inventory.py` (350 lines) → `services/inventory/`

`services/inventory.py` contains: `PieceService` class (lines 15–153) and `StockService` class (lines 154–350).

**Consumers:** `modules/inventory/pieces.py` imports `PieceService`; `modules/inventory/stock.py` imports `StockService`.

**Files:**
- Create: `services/inventory/__init__.py`
- Create: `services/inventory/piece_service.py`
- Create: `services/inventory/stock_service.py`
- Delete: `services/inventory.py`

- [ ] **Step 1: Create `services/inventory/piece_service.py`**

  Copy lines 15–153 (`PieceService` class) with all required imports.

- [ ] **Step 2: Create `services/inventory/stock_service.py`**

  Copy lines 154–350 (`StockService` class) with all required imports.

- [ ] **Step 3: Create `services/inventory/__init__.py`**

  ```python
  from .piece_service import PieceService
  from .stock_service import StockService

  __all__ = ["PieceService", "StockService"]
  ```

- [ ] **Step 4: Delete original and verify**

  ```bash
  rm services/inventory.py
  python -c "from services.inventory import PieceService, StockService; print('OK')"
  ```

- [ ] **Step 5: Verify consumers still import correctly**

  ```bash
  python -c "
  from modules.inventory.pieces import router
  from modules.inventory.stock import router as r2
  print('OK')
  "
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add services/inventory/ services/inventory.py
  git commit -m "refactor: split services/inventory.py (350 lines) into inventory/ package"
  ```

---

## Final Verification

- [ ] **Run full import check**

  ```bash
  python -c "
  from main import app
  routes = [r.path for r in app.routes]
  print(f'Total routes registered: {len(routes)}')
  print('Backend reorganization: OK')
  "
  ```

- [ ] **Run existing tests**

  ```bash
  cd ../..  # repo root
  python -m pytest tests/backend/ -v
  ```

- [ ] **Verify no file over 350 lines remains**

  ```bash
  find app/backend -name "*.py" ! -path "*__pycache__*" ! -path "*alembic*" ! -path "*venv*" \
    -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 350 ] && echo "$lines $1"' _ {} \;
  ```
  Expected: no output.

- [ ] **Final commit**

  ```bash
  git add -A
  git commit -m "refactor: complete backend reorganization — all files ≤ 350 lines"
  ```
