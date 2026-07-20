# Machine Status — Technician-Proposed, CHEFTECH-Gated Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a technician completes a work order and records the machine's resulting status, that becomes a proposal a CHEFTECH must approve before it changes the machine card's status badge — with ADMIN having read-only visibility via the existing audit log.

**Architecture:** New `machine_status_change_requests` table + service (mirrors the existing `parts_drafts.py` guarded-draft pattern) sits between WO completion and `Machines.statut`. Both WO-completion endpoints (technicien, chetop) create a PENDING request instead of writing `Machines.statut` directly. A new CHEFTECH-only router + frontend page lets CHEFTECH approve (writes `Machines.statut`, logs to `AuditLog`) or reject (logs only). A 5th machine status (`FONCTIONNEMENT_RESTREINT`) is added to the shared vocabulary used by both completion forms and the card.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), React + TypeScript + shadcn/ui (frontend), pytest (`tests/backend/*.test.py`, `python_files = *.test.py` per `pytest.ini`).

## Global Constraints

- Shared status vocabulary (5 values, exact spelling): `OPERATIONNELLE`, `FONCTIONNEMENT_RESTREINT`, `EN_MAINTENANCE`, `EN_PANNE`, `HORS_SERVICE`.
- Approve/reject is **CHEFTECH-only** — not `verify_cheftech` (that helper also allows ADMIN/CHETOP), a new strict guard.
- No new ADMIN-facing UI — approve/reject write to the existing `AuditLog` (`entity_type=MACHINE`), surfaced by the already-existing `AuditLogViewer.tsx` page.
- One PENDING request per machine — a new WO completion auto-supersedes (→ REJECTED, with a note) any existing PENDING request for that machine.
- `MachineStatusChangeRequest.status` column must use `SQLEnum(RequestStatus, native_enum=False, length=20)` — matching `OrdresTravail.statut`'s established pattern in this codebase (a native Postgres enum causes `varchar = enumtype` cast errors; see `models/ordres_travail.py`).
- This repo has no DB-backed automated test infrastructure (`tests/backend/conftest.py` only adds `app/backend` to `sys.path` — no DB fixture exists anywhere). Async DB-touching code (service functions, endpoints, WO-completion wiring) is verified manually via the running dev stack, not pytest — matching the existing `parts_drafts.py` precedent (only its pure helpers have `.test.py` coverage). Only pure/no-DB logic gets automated tests in this plan.
- Spec: `docs/superpowers/specs/2026-07-20-machine-status-gated-approval-design.md`.

---

### Task 1: Shared machine-status vocabulary

**Files:**
- Create: `app/backend/models/machine_status.py`
- Test: `tests/backend/machine_status.test.py`

**Interfaces:**
- Produces: `MACHINE_STATUSES: list[str]` (5 values), `is_valid_machine_status(value: str) -> bool` — consumed by Task 7 and Task 8's pydantic validators, and conceptually mirrored by Task 9's frontend `MACHINE_STATUS_OPTIONS`.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/machine_status.test.py`:

```python
"""Pure, no-DB tests for the shared machine-status vocabulary."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from models.machine_status import MACHINE_STATUSES, is_valid_machine_status


def test_machine_statuses_has_five_values():
    assert len(MACHINE_STATUSES) == 5


def test_fonctionnement_restreint_included():
    assert "FONCTIONNEMENT_RESTREINT" in MACHINE_STATUSES


def test_existing_four_statuses_preserved():
    for value in ("OPERATIONNELLE", "EN_MAINTENANCE", "EN_PANNE", "HORS_SERVICE"):
        assert value in MACHINE_STATUSES


def test_is_valid_machine_status_true_for_known_value():
    assert is_valid_machine_status("OPERATIONNELLE") is True


def test_is_valid_machine_status_false_for_unknown_value():
    assert is_valid_machine_status("ACTIF") is False


def test_is_valid_machine_status_false_for_none_semantics_not_applicable():
    # is_valid_machine_status expects a str; callers guard None themselves
    # (see Task 7/8 validators) — this just documents empty string is invalid.
    assert is_valid_machine_status("") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/machine_status.test.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models.machine_status'`

- [ ] **Step 3: Write minimal implementation**

Create `app/backend/models/machine_status.py`:

```python
"""Shared machine-status vocabulary.

Single source of truth for both Machines.statut (the card badge) and
OrdresIntervention.machine_status_after (what a technician selects when
completing a work order) — same 5 values everywhere, no mapping table.
Both columns stay plain unconstrained strings; validation lives here.
"""

MACHINE_STATUSES = [
    "OPERATIONNELLE",
    "FONCTIONNEMENT_RESTREINT",
    "EN_MAINTENANCE",
    "EN_PANNE",
    "HORS_SERVICE",
]


def is_valid_machine_status(value: str) -> bool:
    return value in MACHINE_STATUSES
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/machine_status.test.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/models/machine_status.py tests/backend/machine_status.test.py
git commit -m "feat: add shared machine-status vocabulary (5 values incl. FONCTIONNEMENT_RESTREINT)"
```

---

### Task 2: `MachineStatusChangeRequest` model

**Files:**
- Create: `app/backend/models/machine_status_change_request.py`
- Test: `tests/backend/machine_status_change_request.test.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `MachineStatusChangeRequest` (SQLAlchemy model, `__tablename__ = "machine_status_change_requests"`), `RequestStatus` (str-enum: `PENDING`/`APPROVED`/`REJECTED`) — consumed by Task 3 (migration must match these columns exactly), Task 5 (service), Task 6 (router).

- [ ] **Step 1: Write the failing test**

Create `tests/backend/machine_status_change_request.test.py`:

```python
"""Structural, no-DB tests — importing a SQLAlchemy model doesn't connect
to a database (core.database.Base only builds metadata at import time;
the engine is created lazily in DatabaseManager.init_db())."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from models.machine_status_change_request import MachineStatusChangeRequest, RequestStatus


def test_tablename():
    assert MachineStatusChangeRequest.__tablename__ == "machine_status_change_requests"


def test_columns_present():
    columns = set(MachineStatusChangeRequest.__table__.columns.keys())
    expected = {
        "id", "machine_id", "from_status", "to_status", "status",
        "source_intervention_id", "requested_by", "requested_at",
        "reviewed_by", "reviewed_at", "review_note",
    }
    assert expected.issubset(columns)


def test_request_status_values():
    assert {s.value for s in RequestStatus} == {"PENDING", "APPROVED", "REJECTED"}


def test_status_column_default_is_pending():
    assert MachineStatusChangeRequest.__table__.c.status.default.arg == RequestStatus.PENDING


def test_status_column_is_not_native_enum():
    # native_enum=False is required — see Global Constraints. A native PG enum
    # here would break inserts the same way it would on OrdresTravail.statut.
    col_type = MachineStatusChangeRequest.__table__.c.status.type
    assert col_type.native_enum is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/machine_status_change_request.test.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models.machine_status_change_request'`

- [ ] **Step 3: Write minimal implementation**

Create `app/backend/models/machine_status_change_request.py`:

```python
"""Gated-approval request for a technician-proposed machine status change.

Created by WO completion (technicien or chetop), reviewed by CHEFTECH.
Only APPROVED writes to Machines.statut — see
modules/shared/services/machine_status_requests.py.
"""
from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.sql import func
import enum


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MachineStatusChangeRequest(Base):
    __tablename__ = "machine_status_change_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    machine_id = Column(Integer, nullable=False, index=True)
    from_status = Column(String(30), nullable=False)
    to_status = Column(String(30), nullable=False)
    status = Column(
        SQLEnum(RequestStatus, native_enum=False, length=20),
        nullable=False,
        default=RequestStatus.PENDING,
        index=True,
    )
    # native_enum=False: DB column is character varying (not a PG enum type).
    # Without this, SQLAlchemy casts params to ::requeststatus →
    # "varchar = requeststatus" → UndefinedFunctionError. Mirrors
    # OrdresTravail.statut in models/ordres_travail.py.
    source_intervention_id = Column(Integer, nullable=True)
    requested_by = Column(Integer, nullable=True)
    requested_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/machine_status_change_request.test.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/models/machine_status_change_request.py tests/backend/machine_status_change_request.test.py
git commit -m "feat: add MachineStatusChangeRequest model"
```

---

### Task 3: Alembic migration

**Files:**
- Create: `app/backend/alembic/versions/machine_status_change_requests.py`

**Interfaces:**
- Consumes: column shape from Task 2's `MachineStatusChangeRequest`.
- Produces: the `machine_status_change_requests` table in the live DB — required before Task 5/6/7/8 can be exercised against a running stack.

No automated test — this repo has no migration test harness (confirmed: none of the ~15 existing migration files under `app/backend/alembic/versions/` have accompanying tests). Verified manually in Step 2 below.

- [ ] **Step 1: Write the migration**

Confirm current head first:

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\backend" && python -m alembic heads`
Expected output: `p4_wo_outcome_column (head)`

Create `app/backend/alembic/versions/machine_status_change_requests.py`:

```python
"""Create machine_status_change_requests table

Revision ID: machine_status_change_requests
Revises: p4_wo_outcome_column
Create Date: 2026-07-20

Idempotent guard via information_schema (mirrors quick_action_runs.py).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "machine_status_change_requests"
down_revision: Union[str, Sequence[str], None] = "p4_wo_outcome_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if _table_exists("machine_status_change_requests"):
        return
    op.create_table(
        "machine_status_change_requests",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="PENDING"
        ),
        sa.Column("source_intervention_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_machine_status_change_requests_machine_id",
        "machine_status_change_requests",
        ["machine_id"],
    )
    op.create_index(
        "ix_machine_status_change_requests_status",
        "machine_status_change_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_machine_status_change_requests_status",
        table_name="machine_status_change_requests",
    )
    op.drop_index(
        "ix_machine_status_change_requests_machine_id",
        table_name="machine_status_change_requests",
    )
    op.drop_table("machine_status_change_requests")
```

- [ ] **Step 2: Apply and verify manually**

With the dev stack running (`make up` from repo root if not already up):

Run: `docker compose exec backend alembic upgrade head`
Expected: log line ending in `Running upgrade p4_wo_outcome_column -> machine_status_change_requests, Create machine_status_change_requests table`, no errors.

Verify the table exists:

Run: `docker compose exec postgres psql -U postgres -d asset_management -c "\d machine_status_change_requests"`
Expected: column list matching Step 1's `create_table` call (`id`, `machine_id`, `from_status`, `to_status`, `status`, `source_intervention_id`, `requested_by`, `requested_at`, `reviewed_by`, `reviewed_at`, `review_note`) plus the two indexes.

(`asset_management` is `docker-compose.yml`'s default `POSTGRES_DB` — confirm against your `.env` if it's been overridden.)

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/alembic/versions/machine_status_change_requests.py
git commit -m "feat: migration for machine_status_change_requests table"
```

---

### Task 4: Strict CHEFTECH-only auth dependency

**Files:**
- Modify: `app/backend/modules/cheftech/dependencies.py`
- Test: `tests/backend/verify_cheftech_only.test.py`

**Interfaces:**
- Consumes: `UserRole` from `models.utilisateurs` (existing).
- Produces: `verify_cheftech_only(current_user: Utilisateurs = Depends(get_current_user)) -> Utilisateurs`, raises `HTTPException(403)` for any non-CHEFTECH role — consumed by Task 6's router.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/verify_cheftech_only.test.py`:

```python
"""Pure, no-DB tests — verify_cheftech_only is a plain sync function; calling
it directly with a stub object bypasses FastAPI's DI, which is fine since DI
just calls the function."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from fastapi import HTTPException
from modules.cheftech.dependencies import verify_cheftech_only
from models.utilisateurs import UserRole


class _FakeUser:
    def __init__(self, role):
        self.role = role


def test_verify_cheftech_only_allows_cheftech():
    user = _FakeUser(UserRole.CHEFTECH)
    assert verify_cheftech_only(user) is user


def test_verify_cheftech_only_rejects_admin():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.ADMIN))
    assert exc.value.status_code == 403


def test_verify_cheftech_only_rejects_chetop():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.CHETOP))
    assert exc.value.status_code == 403


def test_verify_cheftech_only_rejects_technicien():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.TECHNICIEN))
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/verify_cheftech_only.test.py -v`
Expected: FAIL with `ImportError: cannot import name 'verify_cheftech_only'`

- [ ] **Step 3: Write minimal implementation**

Read current file first (`app/backend/modules/cheftech/dependencies.py`) — it's:

```python
from fastapi import Depends, HTTPException
from models.utilisateurs import Utilisateurs, UserRole
from core.auth import get_current_user


def verify_management_access(
    current_user: Utilisateurs = Depends(get_current_user),
):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN, UserRole.CHETOP]:
        raise HTTPException(
            status_code=403, detail="Accès non autorisé. Rôle de gestion requis."
        )
    return current_user


def verify_cheftech(
    current_user: Utilisateurs = Depends(verify_management_access),
):
    return current_user


def verify_cheftech_or_admin(
    current_user: Utilisateurs = Depends(verify_management_access),
):
    return current_user
```

Append a new function at the end of the file (use Edit, anchoring on the existing `verify_cheftech_or_admin` block):

```python
def verify_cheftech_or_admin(
    current_user: Utilisateurs = Depends(verify_management_access),
):
    return current_user


def verify_cheftech_only(
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Strict CHEFTECH-only guard — unlike verify_cheftech above (which
    actually also allows ADMIN and CHETOP via verify_management_access),
    this rejects everyone except CHEFTECH. Used for the machine-status
    approval queue, where ADMIN deliberately has no action (read-only via
    the audit log)."""
    if current_user.role != UserRole.CHEFTECH:
        raise HTTPException(status_code=403, detail="Réservé au chef technicien.")
    return current_user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/verify_cheftech_only.test.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/modules/cheftech/dependencies.py tests/backend/verify_cheftech_only.test.py
git commit -m "feat: add strict CHEFTECH-only auth guard"
```

---

### Task 5: Service layer — create / approve / reject / list

**Files:**
- Create: `app/backend/modules/shared/services/machine_status_requests.py`

**Interfaces:**
- Consumes: `Machines` (`models.machines`), `MachineStatusChangeRequest`/`RequestStatus` (Task 2), `AuditService`/`AuditEntityType` (`services.audit`, existing).
- Produces:
  - `async def create_status_change_request(machine_id: int, to_status: str, requested_by: Optional[int], source_intervention_id: Optional[int], db: AsyncSession) -> Optional[int]`
  - `async def approve_status_change_request(request_id: int, approved_by: int, db: AsyncSession) -> Dict[str, Any]` — `{"success": True, "request_id", "status": "APPROVED", "statut"}` or `{"success": False, "error"}`
  - `async def reject_status_change_request(request_id: int, rejected_by: int, note: Optional[str], db: AsyncSession) -> Dict[str, Any]` — `{"success": True, "request_id", "status": "REJECTED"}` or `{"success": False, "error"}`
  - `async def list_pending_requests(db: AsyncSession) -> List[Dict[str, Any]]`
  All consumed by Task 6's router and Task 7/8's WO-completion wiring.

No automated test for this task — every function is DB-touching async code, and this repo has no DB fixture (see Global Constraints). Verified functionally in Task 14 (end-to-end).

- [ ] **Step 1: Write the service**

Create `app/backend/modules/shared/services/machine_status_requests.py`:

```python
"""
Gated approval for technician-proposed machine status changes.

Mirrors modules/ml/services/parts_drafts.py's guarded-draft pattern: a
technician's WO-completion input becomes a PENDING request; only a CHEFTECH
approval writes it to Machines.statut. ADMIN never acts here — approve/reject
write an AuditLog row, surfaced by the existing AuditLogViewer.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def create_status_change_request(
    machine_id: int,
    to_status: str,
    requested_by: Optional[int],
    source_intervention_id: Optional[int],
    db: AsyncSession,
) -> Optional[int]:
    """
    Create a PENDING machine status change request.

    Returns None (no-op) if:
    - the machine doesn't exist
    - to_status already equals the machine's current statut (nothing to propose)

    Supersedes (-> REJECTED, with a note) any existing PENDING request for
    this machine before creating the new one — "last technician's call" per
    request, but nothing is deleted. The new row is flushed (not committed);
    caller commits as part of its own transaction (WO completion).
    """
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )

    machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
    if not machine:
        return None

    from_status = machine.statut
    if from_status == to_status:
        return None

    existing_q = await db.execute(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.machine_id == machine_id,
            MachineStatusChangeRequest.status == RequestStatus.PENDING,
        )
    )
    for existing in existing_q.scalars().all():
        existing.status = RequestStatus.REJECTED
        existing.reviewed_at = datetime.now(timezone.utc)
        existing.review_note = "Superseded by newer request"

    request = MachineStatusChangeRequest(
        machine_id=machine_id,
        from_status=from_status,
        to_status=to_status,
        status=RequestStatus.PENDING,
        source_intervention_id=source_intervention_id,
        requested_by=requested_by,
    )
    db.add(request)
    await db.flush()  # get request.id without committing
    logger.info(
        f"Machine status change request #{request.id} created for machine "
        f"{machine_id}: {from_status} -> {to_status}"
    )
    return request.id


async def approve_status_change_request(
    request_id: int,
    approved_by: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """PENDING -> APPROVED. Sets Machines.statut = to_status, writes AuditLog."""
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from services.audit import AuditService, AuditEntityType

    request = await db.scalar(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.id == request_id
        )
    )
    if not request:
        return {"success": False, "error": "Request not found"}
    if request.status != RequestStatus.PENDING:
        return {
            "success": False,
            "error": f"Request is not pending (status: {request.status.value})",
        }

    machine = await db.scalar(select(Machines).where(Machines.id == request.machine_id))
    if not machine:
        return {"success": False, "error": "Machine not found"}

    machine.statut = request.to_status
    request.status = RequestStatus.APPROVED
    request.reviewed_by = approved_by
    request.reviewed_at = datetime.now(timezone.utc)

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.MACHINE,
            entity_id=request.machine_id,
            old_values={"statut": request.from_status},
            new_values={"statut": request.to_status},
            user_id=approved_by,
            entity_name=machine.nom,
        )
    except Exception:
        logger.warning(f"Audit log failed for status request #{request_id} approval")

    await db.commit()
    logger.info(
        f"Machine status change request #{request_id} approved by user {approved_by}"
    )
    return {
        "success": True,
        "request_id": request_id,
        "status": "APPROVED",
        "statut": machine.statut,
    }


async def reject_status_change_request(
    request_id: int,
    rejected_by: int,
    note: Optional[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """PENDING -> REJECTED. Machines.statut untouched, writes AuditLog.

    `statut` is deliberately NOT in the audit old/new values here — it
    doesn't change on reject, and AuditService.log_update() only records a
    diff for keys whose value differs between old_values/new_values;
    identical values on both sides would produce an empty, useless entry.
    """
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from services.audit import AuditService, AuditEntityType

    request = await db.scalar(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.id == request_id
        )
    )
    if not request:
        return {"success": False, "error": "Request not found"}
    if request.status != RequestStatus.PENDING:
        return {
            "success": False,
            "error": f"Request is not pending (status: {request.status.value})",
        }

    machine = await db.scalar(select(Machines).where(Machines.id == request.machine_id))

    request.status = RequestStatus.REJECTED
    request.reviewed_by = rejected_by
    request.reviewed_at = datetime.now(timezone.utc)
    request.review_note = note

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.MACHINE,
            entity_id=request.machine_id,
            old_values={
                "request_status": "PENDING",
                "proposed_statut": request.to_status,
            },
            new_values={
                "request_status": "REJECTED",
                "proposed_statut": request.to_status,
                "review_note": note or "",
            },
            user_id=rejected_by,
            entity_name=machine.nom if machine else None,
        )
    except Exception:
        logger.warning(f"Audit log failed for status request #{request_id} rejection")

    await db.commit()
    logger.info(
        f"Machine status change request #{request_id} rejected by user {rejected_by}"
    )
    return {"success": True, "request_id": request_id, "status": "REJECTED"}


async def list_pending_requests(db: AsyncSession) -> List[Dict[str, Any]]:
    """Joined view for the CHEFTECH queue page, oldest-first."""
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from models.utilisateurs import Utilisateurs

    result = await db.execute(
        select(MachineStatusChangeRequest, Machines, Utilisateurs)
        .join(Machines, MachineStatusChangeRequest.machine_id == Machines.id)
        .outerjoin(
            Utilisateurs, MachineStatusChangeRequest.requested_by == Utilisateurs.id
        )
        .where(MachineStatusChangeRequest.status == RequestStatus.PENDING)
        .order_by(MachineStatusChangeRequest.requested_at.asc())
    )
    rows = result.all()
    return [
        {
            "id": req.id,
            "machine_id": req.machine_id,
            "machine_name": machine.nom,
            "from_status": req.from_status,
            "to_status": req.to_status,
            "requested_by": req.requested_by,
            "requested_by_name": user.nom if user else None,
            "requested_at": req.requested_at.isoformat() if req.requested_at else None,
            "source_intervention_id": req.source_intervention_id,
        }
        for req, machine, user in rows
    ]
```

- [ ] **Step 2: Verify it imports cleanly (no DB needed for this)**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\backend" && python -c "import sys; sys.path.insert(0, '.'); from modules.shared.services.machine_status_requests import create_status_change_request, approve_status_change_request, reject_status_change_request, list_pending_requests; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/modules/shared/services/machine_status_requests.py
git commit -m "feat: add machine status change request service (create/approve/reject/list)"
```

---

### Task 6: CHEFTECH-only router

**Files:**
- Create: `app/backend/modules/cheftech/routes/machine_status_requests.py`

**Interfaces:**
- Consumes: `verify_cheftech_only` (Task 4), `approve_status_change_request`/`reject_status_change_request`/`list_pending_requests` (Task 5).
- Produces: `GET /api/v1/cheftech/machine-status-requests`, `PATCH /api/v1/cheftech/machine-status-requests/{id}/approve`, `PATCH /api/v1/cheftech/machine-status-requests/{id}/reject` — consumed by Task 13's frontend page. Auto-discovered by `include_routers_from_package(app, "modules")` in `main.py` (no manual registration needed — confirmed this is how every other `modules/cheftech/routes/*.py` router already gets wired up).

- [ ] **Step 1: Write the router**

Create `app/backend/modules/cheftech/routes/machine_status_requests.py`:

```python
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs
from modules.cheftech.dependencies import verify_cheftech_only
from modules.shared.services.machine_status_requests import (
    approve_status_change_request,
    list_pending_requests,
    reject_status_change_request,
)

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


class RejectPayload(BaseModel):
    note: Optional[str] = None


@router.get("/machine-status-requests")
async def get_pending_machine_status_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: list technician-proposed machine status changes awaiting review."""
    items = await list_pending_requests(db)
    return {"pending_count": len(items), "items": items}


@router.patch(
    "/machine-status-requests/{request_id}/approve",
    responses={404: {"description": "Request not found"}, 400: {"description": "Request is not pending"}},
)
async def approve_machine_status_request(
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: approve a proposed status change. Sets Machines.statut."""
    result = await approve_status_change_request(request_id, current_user.id, db)
    if not result["success"]:
        status_code = 404 if result["error"] == "Request not found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return result


@router.patch(
    "/machine-status-requests/{request_id}/reject",
    responses={404: {"description": "Request not found"}, 400: {"description": "Request is not pending"}},
)
async def reject_machine_status_request(
    request_id: int,
    payload: RejectPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: reject a proposed status change. Machines.statut unchanged."""
    result = await reject_status_change_request(
        request_id, current_user.id, payload.note, db
    )
    if not result["success"]:
        status_code = 404 if result["error"] == "Request not found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return result
```

- [ ] **Step 2: Verify route registration (no DB needed)**

Run:
```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\backend" && python -c "
import sys
sys.path.insert(0, '.')
from modules.cheftech.routes.machine_status_requests import router
for r in router.routes:
    print(r.methods, r.path)
"
```
Expected output (3 lines, order may vary):
```
{'GET'} /api/v1/cheftech/machine-status-requests
{'PATCH'} /api/v1/cheftech/machine-status-requests/{request_id}/approve
{'PATCH'} /api/v1/cheftech/machine-status-requests/{request_id}/reject
```

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/modules/cheftech/routes/machine_status_requests.py
git commit -m "feat: add CHEFTECH machine-status-requests router"
```

---

### Task 7: Wire into technicien WO completion

**Files:**
- Modify: `app/backend/modules/technicien/technicien_work_orders.py`
- Test: `tests/backend/technicien_machine_status_validator.test.py`

**Interfaces:**
- Consumes: `MACHINE_STATUSES` (Task 1), `create_status_change_request` (Task 5).
- Produces: `WorkOrderCompletePayload.machine_status_after` now rejects unknown values at the pydantic layer (400 via FastAPI's automatic validation error handling); `complete_work_order` now creates a status change request as a side effect.

- [ ] **Step 1: Write the failing test (validator only — pure, no DB)**

Create `tests/backend/technicien_machine_status_validator.test.py`:

```python
"""Pure test: pydantic validation only. Importing technicien_work_orders.py
pulls in its full dependency chain (routers, services) but does not touch
the DB at import time — same as importing modules.ml.router does elsewhere
in this codebase."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from pydantic import ValidationError
from modules.technicien.technicien_work_orders import WorkOrderCompletePayload


def test_valid_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(
        rapport="ok", machine_status_after="FONCTIONNEMENT_RESTREINT"
    )
    assert payload.machine_status_after == "FONCTIONNEMENT_RESTREINT"


def test_invalid_machine_status_after_rejected():
    with pytest.raises(ValidationError):
        WorkOrderCompletePayload(rapport="ok", machine_status_after="BOGUS")


def test_none_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(rapport="ok")
    assert payload.machine_status_after is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/technicien_machine_status_validator.test.py -v`
Expected: FAIL on `test_invalid_machine_status_after_rejected` (no validator yet, so `"BOGUS"` is silently accepted — the other two pass already).

- [ ] **Step 3: Add the validator and the request-creation wiring**

Edit `app/backend/modules/technicien/technicien_work_orders.py`.

Change the pydantic import (currently `from pydantic import BaseModel`):

```python
from pydantic import BaseModel, field_validator
```

Add two new imports alongside the existing ones (after `from services.ml.recovery import PostMaintenanceRecoveryService`):

```python
from services.ml.recovery import PostMaintenanceRecoveryService
from models.machine_status import MACHINE_STATUSES
from modules.shared.services.machine_status_requests import create_status_change_request
```

In the `WorkOrderCompletePayload` class, replace:

```python
    machine_status_after: Optional[str] = None

    # PDCA Specific
```

with:

```python
    machine_status_after: Optional[str] = None

    @field_validator("machine_status_after")
    @classmethod
    def _validate_machine_status_after(cls, v):
        if v is not None and v not in MACHINE_STATUSES:
            raise ValueError(f"machine_status_after must be one of {MACHINE_STATUSES}")
        return v

    # PDCA Specific
```

In `complete_work_order`, replace:

```python
        intervention = (await db.execute(
            select(OrdresIntervention).where(OrdresIntervention.ordre_travail_id == order_id)
        )).scalar_one_or_none()
        if intervention:
            await _update_intervention_fields(db, intervention, payload, wo.date_debut, now)
```

with:

```python
        intervention = (await db.execute(
            select(OrdresIntervention).where(OrdresIntervention.ordre_travail_id == order_id)
        )).scalar_one_or_none()
        if intervention:
            await _update_intervention_fields(db, intervention, payload, wo.date_debut, now)
            if payload.machine_status_after:
                try:
                    await create_status_change_request(
                        machine_id=wo.machine_id,
                        to_status=payload.machine_status_after,
                        requested_by=current_user.id,
                        source_intervention_id=intervention.id,
                        db=db,
                    )
                except Exception:
                    logger.warning(
                        f"Machine status change request failed for WO {order_id}"
                    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/technicien_machine_status_validator.test.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/modules/technicien/technicien_work_orders.py tests/backend/technicien_machine_status_validator.test.py
git commit -m "feat: validate machine_status_after and create status change request on technicien WO completion"
```

---

### Task 8: Wire into chetop WO completion

**Files:**
- Modify: `app/backend/modules/chetop/schemas.py`
- Modify: `app/backend/modules/chetop/routes/work_orders.py`
- Test: `tests/backend/chetop_machine_status_validator.test.py`

**Interfaces:**
- Consumes: `MACHINE_STATUSES` (Task 1), `create_status_change_request` (Task 5).
- Produces: same validation + request-creation behavior as Task 7, on the chetop completion path.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/chetop_machine_status_validator.test.py`:

```python
"""Pure test: pydantic validation only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from pydantic import ValidationError
from modules.chetop.schemas import WorkOrderCompletePayload


def test_valid_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(
        rapport="ok", machine_status_after="EN_PANNE"
    )
    assert payload.machine_status_after == "EN_PANNE"


def test_invalid_machine_status_after_rejected():
    with pytest.raises(ValidationError):
        WorkOrderCompletePayload(rapport="ok", machine_status_after="EN_MARCHE")


def test_none_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(rapport="ok")
    assert payload.machine_status_after is None
```

Note: `test_invalid_machine_status_after_rejected` deliberately uses `"EN_MARCHE"` — the modal's *old* value, now invalid under the unified vocabulary. This is the regression the unification is meant to catch.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/chetop_machine_status_validator.test.py -v`
Expected: FAIL on `test_invalid_machine_status_after_rejected` (no validator yet).

- [ ] **Step 3: Add the validator to the schema**

Edit `app/backend/modules/chetop/schemas.py`. Change the top import:

```python
from pydantic import BaseModel
```

to:

```python
from pydantic import BaseModel, field_validator

from models.machine_status import MACHINE_STATUSES
```

In the `WorkOrderCompletePayload` class, replace:

```python
    machine_status_after: Optional[str] = None

    # PDCA Specific
```

with:

```python
    machine_status_after: Optional[str] = None

    @field_validator("machine_status_after")
    @classmethod
    def _validate_machine_status_after(cls, v):
        if v is not None and v not in MACHINE_STATUSES:
            raise ValueError(f"machine_status_after must be one of {MACHINE_STATUSES}")
        return v

    # PDCA Specific
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom" && python -m pytest tests/backend/chetop_machine_status_validator.test.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Wire request-creation into the completion endpoint**

Edit `app/backend/modules/chetop/routes/work_orders.py`. Add an import alongside the existing ones (after `from services.ml.recovery import PostMaintenanceRecoveryService`):

```python
from services.ml.recovery import PostMaintenanceRecoveryService
from modules.shared.services.machine_status_requests import create_status_change_request
```

In `complete_work_order`, replace:

```python
        _apply_intervention_completion_fields(intervention, payload, wo, now)
        _add_telemetry_if_present(db, payload, wo, order_id, now, current_user.id)
        await _apply_parts_consumption(db, intervention, payload, order_id)
```

with:

```python
        _apply_intervention_completion_fields(intervention, payload, wo, now)
        if payload.machine_status_after:
            try:
                await create_status_change_request(
                    machine_id=wo.machine_id,
                    to_status=payload.machine_status_after,
                    requested_by=current_user.id,
                    source_intervention_id=intervention.id,
                    db=db,
                )
            except Exception:
                logger.warning(
                    f"Machine status change request failed for WO {order_id}"
                )
        _add_telemetry_if_present(db, payload, wo, order_id, now, current_user.id)
        await _apply_parts_consumption(db, intervention, payload, order_id)
```

- [ ] **Step 6: Verify the endpoint file still imports cleanly**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\backend" && python -c "import sys; sys.path.insert(0, '.'); from modules.chetop.routes.work_orders import router; print(len(router.routes))"`
Expected: prints an integer (route count), no traceback.

- [ ] **Step 7: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/backend/modules/chetop/schemas.py app/backend/modules/chetop/routes/work_orders.py tests/backend/chetop_machine_status_validator.test.py
git commit -m "feat: validate machine_status_after and create status change request on chetop WO completion"
```

---

### Task 9: Frontend shared status vocabulary

**Files:**
- Modify: `app/frontend/src/lib/constants.ts`

**Interfaces:**
- Produces: `MACHINE_STATUS_OPTIONS` now has 5 entries — consumed by Task 10, 11, 12, 13.

- [ ] **Step 1: Add the 5th option**

Edit `app/frontend/src/lib/constants.ts`. Replace:

```ts
export const MACHINE_STATUS_OPTIONS = [
    { value: 'OPERATIONNELLE', label: 'Opérationnelle' },
    { value: 'EN_MAINTENANCE', label: 'En Maintenance' },
    { value: 'EN_PANNE', label: 'En Panne' },
    { value: 'HORS_SERVICE', label: 'Hors Service' },
];
```

with:

```ts
export const MACHINE_STATUS_OPTIONS = [
    { value: 'OPERATIONNELLE', label: 'Opérationnelle' },
    { value: 'FONCTIONNEMENT_RESTREINT', label: 'Fonctionnement restreint' },
    { value: 'EN_MAINTENANCE', label: 'En Maintenance' },
    { value: 'EN_PANNE', label: 'En Panne' },
    { value: 'HORS_SERVICE', label: 'Hors Service' },
];
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\frontend" && npx tsc --noEmit`
Expected: no new errors referencing `constants.ts`.

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/frontend/src/lib/constants.ts
git commit -m "feat: add FONCTIONNEMENT_RESTREINT to shared machine status options"
```

---

### Task 10: Unify `WorkOrderCompleteDialog.tsx` (technicien)

**Files:**
- Modify: `app/frontend/src/modules/technicien/components/WorkOrderCompleteDialog.tsx`

**Interfaces:**
- Consumes: `MACHINE_STATUS_OPTIONS` from `@/lib/constants` (Task 9).

- [ ] **Step 1: Import the shared options and remove the local ones**

Edit the file. Add an import (after the existing `DirectConsumeSelector` import):

```ts
import { DirectConsumeSelector, DirectConsumeRow, PendingDraftRow, directHasErrors, serializeDirect, serializePendingDirect } from '@/components/inventory/DirectConsumeSelector';
import { MACHINE_STATUS_OPTIONS } from '@/lib/constants';
```

Delete the local constant:

```ts
const MACHINE_STATUS_OPTIONS = [
    { value: 'OPERATIONAL', label: 'Opérationnel' },
    { value: 'DEGRADED', label: 'Dégradé (fonctionne partiellement)' },
    { value: 'STOPPED', label: 'Arrêté (en attente)' },
    { value: 'SCRAP', label: 'Mettre au rebut' },
];

```

(the trailing blank line goes too — the block sits between the ROOT_CAUSE options above it and `const STEPS = [` below it).

- [ ] **Step 2: Update the default state value**

Find and replace:

```ts
const [machineStatusAfter, setMachineStatusAfter] = useState<string>('OPERATIONAL');
```

with:

```ts
const [machineStatusAfter, setMachineStatusAfter] = useState<string>('OPERATIONNELLE');
```

- [ ] **Step 3: Verify no TypeScript errors**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\frontend" && npx tsc --noEmit`
Expected: no new errors referencing `WorkOrderCompleteDialog.tsx`.

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/frontend/src/modules/technicien/components/WorkOrderCompleteDialog.tsx
git commit -m "refactor: unify WorkOrderCompleteDialog machine status options with shared vocabulary"
```

---

### Task 11: Unify `CompleteWorkOrderModal.tsx` (chetop)

**Files:**
- Modify: `app/frontend/src/modules/shared/CompleteWorkOrderModal.tsx`

**Interfaces:**
- Consumes: `MACHINE_STATUS_OPTIONS` from `@/lib/constants` (Task 9).

- [ ] **Step 1: Import the shared options**

Edit the file. Add an import (after the existing `MachineMetricsForm` import):

```ts
import { MachineMetricsForm, TelemetryFormData } from '@/components/technicien/MachineMetricsForm';
import { MACHINE_STATUS_OPTIONS } from '@/lib/constants';
```

- [ ] **Step 2: Replace the inline SelectItems with a map over the shared options**

Find:

```tsx
                    <Select
                      value={formData.machine_status_after}
                      onValueChange={(val) => setFormData({ ...formData, machine_status_after: val })}
                    >
                      <SelectTrigger id="m_status"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="EN_MARCHE">En marche (Fonctionnel)</SelectItem>
                        <SelectItem value="ARRETEE">Arrêtée (En attente/HS)</SelectItem>
                        <SelectItem value="FONCTIONNEMENT_RESTREINT">Fonctionnement restreint</SelectItem>
                      </SelectContent>
                    </Select>
```

Replace with:

```tsx
                    <Select
                      value={formData.machine_status_after}
                      onValueChange={(val) => setFormData({ ...formData, machine_status_after: val })}
                    >
                      <SelectTrigger id="m_status"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {MACHINE_STATUS_OPTIONS.map((status) => (
                          <SelectItem key={status.value} value={status.value}>
                            {status.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
```

- [ ] **Step 3: Update the two default values**

There are two identical occurrences of `machine_status_after: 'EN_MARCHE',` in this file — one in the initial `useState` (around line 105), one in the reset-on-close effect (around line 134). Replace **both** with `machine_status_after: 'OPERATIONNELLE',`.

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\frontend" && npx tsc --noEmit`
Expected: no new errors referencing `CompleteWorkOrderModal.tsx`.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/frontend/src/modules/shared/CompleteWorkOrderModal.tsx
git commit -m "refactor: unify CompleteWorkOrderModal machine status options with shared vocabulary"
```

---

### Task 12: Add FONCTIONNEMENT_RESTREINT to all status badge displays

**Files:**
- Modify: `app/frontend/src/modules/admin/machines/components/AdminMachinesGrid.tsx`
- Modify: `app/frontend/src/modules/technicien/TechnicianMachines.tsx`
- Modify: `app/frontend/src/modules/chetop/ChetopMachines.tsx`
- Modify: `app/frontend/src/modules/cheftech/machines/components/ChefTechMachinesGrid.tsx`
- Modify: `app/frontend/src/modules/shared/MachineDetailPage.tsx`

**Interfaces:**
- No new interfaces — purely visual, each file's `getMachineStatusConfig` map gets one new entry.

- [ ] **Step 1: `AdminMachinesGrid.tsx`**

Find:

```tsx
function getMachineStatusConfig(statut = '') {
  const map: Record<string, { label: string; dot: string }> = {
    OPERATIONNELLE: { label: 'Opérationnelle', dot: 'bg-emerald-500' },
    EN_MAINTENANCE: { label: 'En Maintenance', dot: 'bg-amber-500' },
    EN_PANNE: { label: 'En Panne', dot: 'bg-red-500 animate-pulse' },
    HORS_SERVICE: { label: 'Hors Service', dot: 'bg-gray-400' },
  };
  return map[statut] ?? { label: statut || 'Inconnu', dot: 'bg-gray-300' };
}
```

Replace with:

```tsx
function getMachineStatusConfig(statut = '') {
  const map: Record<string, { label: string; dot: string }> = {
    OPERATIONNELLE: { label: 'Opérationnelle', dot: 'bg-emerald-500' },
    FONCTIONNEMENT_RESTREINT: { label: 'Fonctionnement restreint', dot: 'bg-amber-600' },
    EN_MAINTENANCE: { label: 'En Maintenance', dot: 'bg-amber-500' },
    EN_PANNE: { label: 'En Panne', dot: 'bg-red-500 animate-pulse' },
    HORS_SERVICE: { label: 'Hors Service', dot: 'bg-gray-400' },
  };
  return map[statut] ?? { label: statut || 'Inconnu', dot: 'bg-gray-300' };
}
```

(`bg-amber-600` vs. `EN_MAINTENANCE`'s `bg-amber-500` — distinct enough to tell the two amber states apart at a glance.)

- [ ] **Step 2: `TechnicianMachines.tsx`**

Same find/replace as Step 1 (identical function body in this file).

- [ ] **Step 3: `ChetopMachines.tsx`**

Same find/replace as Step 1 (identical function body in this file).

- [ ] **Step 4: `ChefTechMachinesGrid.tsx`**

Same find/replace as Step 1 (identical function body in this file).

- [ ] **Step 5: `MachineDetailPage.tsx` — badge map**

Find:

```tsx
function getMachineStatusConfig(statut: string) {
    const map: Record<string, { label: string; className: string }> = {
        OPERATIONNELLE: { label: '● Opérationnelle', className: 'bg-emerald-100 text-emerald-800 border border-emerald-200' },
        EN_MAINTENANCE: { label: '● En Maintenance', className: 'bg-amber-100 text-amber-800 border border-amber-200' },
        EN_PANNE: { label: '● En Panne', className: 'bg-red-100 text-red-800 border border-red-200 animate-pulse' },
        HORS_SERVICE: { label: '● Hors Service', className: 'bg-gray-100 text-blue-100 border border-blue-700/50' },
    };
    return map[statut] ?? { label: statut, className: 'bg-gray-100 text-blue-200' };
}
```

Replace with:

```tsx
function getMachineStatusConfig(statut: string) {
    const map: Record<string, { label: string; className: string }> = {
        OPERATIONNELLE: { label: '● Opérationnelle', className: 'bg-emerald-100 text-emerald-800 border border-emerald-200' },
        FONCTIONNEMENT_RESTREINT: { label: '● Fonctionnement restreint', className: 'bg-orange-100 text-orange-800 border border-orange-200' },
        EN_MAINTENANCE: { label: '● En Maintenance', className: 'bg-amber-100 text-amber-800 border border-amber-200' },
        EN_PANNE: { label: '● En Panne', className: 'bg-red-100 text-red-800 border border-red-200 animate-pulse' },
        HORS_SERVICE: { label: '● Hors Service', className: 'bg-gray-100 text-blue-100 border border-blue-700/50' },
    };
    return map[statut] ?? { label: statut, className: 'bg-gray-100 text-blue-200' };
}
```

- [ ] **Step 6: `MachineDetailPage.tsx` — manual-edit dropdown**

Find:

```tsx
                                <SelectContent>
                                    <SelectItem value="OPERATIONNELLE">Opérationnelle</SelectItem>
                                    <SelectItem value="EN_MAINTENANCE">En Maintenance</SelectItem>
                                    <SelectItem value="EN_PANNE">En Panne</SelectItem>
                                    <SelectItem value="HORS_SERVICE">Hors Service</SelectItem>
                                </SelectContent>
```

Replace with:

```tsx
                                <SelectContent>
                                    <SelectItem value="OPERATIONNELLE">Opérationnelle</SelectItem>
                                    <SelectItem value="FONCTIONNEMENT_RESTREINT">Fonctionnement restreint</SelectItem>
                                    <SelectItem value="EN_MAINTENANCE">En Maintenance</SelectItem>
                                    <SelectItem value="EN_PANNE">En Panne</SelectItem>
                                    <SelectItem value="HORS_SERVICE">Hors Service</SelectItem>
                                </SelectContent>
```

- [ ] **Step 7: Verify no TypeScript errors**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\frontend" && npx tsc --noEmit`
Expected: no new errors in any of the 5 modified files.

- [ ] **Step 8: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/frontend/src/modules/admin/machines/components/AdminMachinesGrid.tsx app/frontend/src/modules/technicien/TechnicianMachines.tsx app/frontend/src/modules/chetop/ChetopMachines.tsx app/frontend/src/modules/cheftech/machines/components/ChefTechMachinesGrid.tsx app/frontend/src/modules/shared/MachineDetailPage.tsx
git commit -m "feat: display FONCTIONNEMENT_RESTREINT status badge across machine views"
```

---

### Task 13: CHEFTECH review queue page

**Files:**
- Create: `app/frontend/src/modules/cheftech/MachineStatusRequestsPage.tsx`
- Modify: `app/frontend/src/app/routing/AppRoutes.tsx`
- Modify: `app/frontend/src/components/layout/Sidebar.tsx`

**Interfaces:**
- Consumes: `GET/PATCH /api/v1/cheftech/machine-status-requests*` (Task 6), `MACHINE_STATUS_OPTIONS` (Task 9).

- [ ] **Step 1: Create the page component**

Create `app/frontend/src/modules/cheftech/MachineStatusRequestsPage.tsx`:

```tsx
import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { MACHINE_STATUS_OPTIONS } from '@/lib/constants';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface PendingRequest {
  id: number;
  machine_id: number;
  machine_name: string;
  from_status: string;
  to_status: string;
  requested_by: number | null;
  requested_by_name: string | null;
  requested_at: string | null;
  source_intervention_id: number | null;
}

function statusLabel(value: string): string {
  return MACHINE_STATUS_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

export default function MachineStatusRequestsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<PendingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [rejectNoteId, setRejectNoteId] = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState('');

  const loadData = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/cheftech/machine-status-requests`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch (err) {
      console.error('Failed to load machine status requests:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const approve = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetch(
        `${API}/api/v1/cheftech/machine-status-requests/${id}/approve`,
        { method: 'PATCH', headers: { Authorization: `Bearer ${getToken()}` } }
      );
      if (!res.ok) throw new Error('API error');
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast({
        title: 'Statut approuvé',
        description: 'Le statut de la machine a été mis à jour.',
      });
    } catch {
      toast({
        title: 'Erreur',
        description: "Impossible d'approuver la demande",
        variant: 'destructive',
      });
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetch(
        `${API}/api/v1/cheftech/machine-status-requests/${id}/reject`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ note: rejectNote || undefined }),
        }
      );
      if (!res.ok) throw new Error('API error');
      setItems((prev) => prev.filter((i) => i.id !== id));
      setRejectNoteId(null);
      setRejectNote('');
      toast({ title: 'Demande rejetée' });
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de rejeter la demande',
        variant: 'destructive',
      });
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-6 w-6 text-white/70" />
          <h1 className="text-2xl font-bold text-white">Changements de statut</h1>
          <Badge variant="outline" className="border-white/10 text-white/50 text-xs">
            {items.length} en attente
          </Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadData}
          className="border-white/10 bg-white/5 text-white/60 hover:bg-white/10 text-xs"
        >
          Actualiser
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="font-medium text-sm">Aucune demande en attente</span>
        </div>
      ) : (
        <div className="rounded-xl border border-white/[0.06] bg-[#0f1623] overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-white/[0.06] hover:bg-transparent">
                <TableHead className="text-white/50">Machine</TableHead>
                <TableHead className="text-white/50">Technicien</TableHead>
                <TableHead className="text-white/50">Statut actuel</TableHead>
                <TableHead className="text-white/50">Statut proposé</TableHead>
                <TableHead className="text-white/50 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <React.Fragment key={item.id}>
                  <TableRow className="border-white/[0.06]">
                    <TableCell className="text-white font-medium">
                      {item.machine_name} (#{item.machine_id})
                    </TableCell>
                    <TableCell className="text-white/60">
                      {item.requested_by_name ?? `Utilisateur #${item.requested_by}`}
                    </TableCell>
                    <TableCell className="text-white/60">
                      {statusLabel(item.from_status)}
                    </TableCell>
                    <TableCell className="text-white font-semibold">
                      {statusLabel(item.to_status)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-500 text-white"
                          disabled={busyId === item.id}
                          onClick={() => approve(item.id)}
                        >
                          <CheckCircle2 className="h-4 w-4 mr-1" />
                          Approuver
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                          disabled={busyId === item.id}
                          onClick={() =>
                            setRejectNoteId(rejectNoteId === item.id ? null : item.id)
                          }
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Rejeter
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  {rejectNoteId === item.id && (
                    <TableRow className="border-white/[0.06]">
                      <TableCell colSpan={5} className="bg-[#131c2e]">
                        <div className="flex items-center gap-2 py-2">
                          <Textarea
                            value={rejectNote}
                            onChange={(e) => setRejectNote(e.target.value)}
                            placeholder="Motif du rejet (optionnel)"
                            className="bg-[#0f1623] border-white/[0.08] text-white text-sm min-h-[40px]"
                          />
                          <Button
                            size="sm"
                            className="bg-red-600 hover:bg-red-500 text-white shrink-0"
                            disabled={busyId === item.id}
                            onClick={() => reject(item.id)}
                          >
                            Confirmer
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Register the route**

Edit `app/frontend/src/app/routing/AppRoutes.tsx`. Add an import (after `import ChefTechAlertWorkflow from '@/modules/cheftech/ChefTechAlertWorkflow';`):

```tsx
import ChefTechAlertWorkflow from '@/modules/cheftech/ChefTechAlertWorkflow';
import MachineStatusRequestsPage from '@/modules/cheftech/MachineStatusRequestsPage';
```

Add a route (after the `/cheftech/alerts` route block, i.e. after its closing `/>`  and before the `/chat` route):

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
      <Route
        path="/cheftech/machine-status-requests"
        element={
          <ProtectedRoute allowedRoles={['CHEFTECH']}>
            <Layout>
              <MachineStatusRequestsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
```

- [ ] **Step 3: Add the sidebar entry**

Edit `app/frontend/src/components/layout/Sidebar.tsx`. Add `RefreshCw` to the lucide-react import list:

```tsx
import {
  LayoutDashboard,
  Settings,
  Wrench,
  ClipboardList,
  Calendar,
  FileText,
  Archive,
  UserCheck,
  Users,
  Columns,
  Package,
  BrainCircuit,
  LucideIcon,
  Bell,
  MessageSquare,
  Activity,
  History,
  ChevronLeft,
  ListChecks,
  Database,
  PackageSearch,
  RefreshCw,
} from 'lucide-react';
```

In the `CHEFTECH` navigation array, add a new entry after `'Centre des alertes'`:

```tsx
      { name: 'Centre des alertes', href: '/cheftech/alerts', icon: Bell },
      { name: 'Changements de statut', href: '/cheftech/machine-status-requests', icon: RefreshCw },
      { name: 'Assistant IA', href: '/chat', icon: MessageSquare },
```

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom\app\frontend" && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
git add app/frontend/src/modules/cheftech/MachineStatusRequestsPage.tsx app/frontend/src/app/routing/AppRoutes.tsx app/frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add CHEFTECH machine status requests review queue page"
```

---

### Task 14: End-to-end verification (browser)

No new files — this task exercises everything built in Tasks 1–13 together against the running dev stack.

- [ ] **Step 1: Rebuild and start the stack**

```bash
cd "C:\Users\Admin\Downloads\EAM\EAMSagemCom"
docker compose build backend frontend
docker compose up -d
docker compose exec backend alembic upgrade head
```

Expected: all containers healthy; migration output shows `machine_status_change_requests` already applied (or applies cleanly if Task 3 wasn't run against this stack yet).

- [ ] **Step 2: Complete a WO as TECHNICIEN with a status proposal**

In the browser (`http://localhost:3000`), log in as a TECHNICIEN, open an `IN_PROGRESS` work order, complete it, and in "État de la machine après" pick **Fonctionnement restreint**. Submit.

Expected: completion succeeds (existing behavior unchanged). The machine's card status badge does **not** change yet (still shows its prior status) — this is the gate working as intended.

- [ ] **Step 3: Confirm the request landed as PENDING**

Log in as CHEFTECH, navigate to **Changements de statut** in the sidebar (`/cheftech/machine-status-requests`).

Expected: one row — the machine from Step 2, "Statut proposé" = "Fonctionnement restreint", technician's name shown.

- [ ] **Step 4: Approve and confirm the card updates**

Click **Approuver** on that row.

Expected: row disappears from the queue; navigating to that machine's card (Admin/CHEFTECH machines grid, or the machine detail page) now shows **Fonctionnement restreint** with its amber badge.

- [ ] **Step 5: Confirm ADMIN sees it via audit log, with no action available**

Log in as ADMIN. Confirm `/cheftech/machine-status-requests` is not reachable (redirect/blocked by `ProtectedRoute`). Navigate to **Historique (Audit)** (`/audit-log`).

Expected: an entry for the machine with `entity_type = MACHINE`, showing the `statut` change from the prior value to "FONCTIONNEMENT_RESTREINT", attributed to the CHEFTECH who approved it.

- [ ] **Step 6: Confirm reject leaves the card unchanged**

Repeat Steps 2–3 with a different proposed status (e.g. **En panne**). As CHEFTECH, click **Rejeter**, optionally type a note, click **Confirmer**.

Expected: row disappears from the queue; the machine's card status is unchanged from before Step 2's completion. In `/audit-log` as ADMIN, an entry shows the rejection (`request_status: PENDING -> REJECTED`) with the note.

- [ ] **Step 7: Confirm supersede-on-new-completion**

Complete another WO for the *same* machine as TECHNICIEN with a new proposed status, before the previous request (if any is still PENDING) is reviewed.

Expected: the CHEFTECH queue shows only the newest request for that machine — the older PENDING one is gone from the queue (superseded → REJECTED, visible in the audit log with note "Superseded by newer request" only if it had already been approved/rejected... actually confirm via direct check: query `GET /api/v1/cheftech/machine-status-requests` before and after to see only one PENDING row per machine).
