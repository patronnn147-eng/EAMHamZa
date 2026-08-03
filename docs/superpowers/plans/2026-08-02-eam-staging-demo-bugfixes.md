# EAM Staging Demo Bugfixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this project's memory `feedback-no-subagents.md` forbids the Agent tool — do NOT use superpowers:subagent-driven-development here). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two confirmed, pre-existing bugs the user hit while reviewing seeded demo data — (1) work-order/intervention lists and detail views show raw user IDs instead of technician/cheftech names in several role views, and (2) the real "complete work order via PDCA form" endpoint never triggers the P4/P7 ML feedback hooks. This is Plan 1 of 2 for the eam-staging demo-video prep; Plan 2 (the new seed-data script) depends on these fixes being in place first so seeded data displays and feeds ML correctly.

**Architecture:** Backend-only for bug 6 in the two generic/entity-CRUD views (Admin) — add a name-lookup join to existing queries and a new `Optional[str]` field to the response schema; frontend for those two views is *already wired* to read the field (confirmed by reading the code), so no frontend change needed there. For the cheftech/technicien intervention views, both backend (name field + query) and a small frontend render fix are needed (frontend currently renders raw `Tech #{id}` instead of a name). Bug 7 is a single isolated addition mirroring an existing non-fatal try/except pattern already used elsewhere in the same codebase.

**Tech Stack:** FastAPI + SQLAlchemy async (Python), Pydantic v2, React + TypeScript (Vite), pytest (asyncio_mode=auto, `testpaths = tests` under `app/backend/`).

## Global Constraints

- Do not change the return type/shape of `OrdresTravailService.get_by_id`, `.update`, `.create`, `.delete` — other code (`app/backend/modules/shared/routes/ordres_travail/validation.py`) depends on getting a plain ORM `OrdresTravail` object back for mutation. Only `.get_list` may be enriched.
- Follow the existing outerjoin+`.label()` pattern already used in `app/backend/modules/chetop/routes/work_orders.py:59` and `app/backend/modules/cheftech/cheftech_work_orders.py:171-191` for any new query joins — this codebase already has a working precedent, don't invent a different style.
- `OrdresIntervention.statut` real vocabulary is `EN_ATTENTE / EN_COURS / TERMINÉ / BLOQUÉ / PENDING_APPROVAL / APPROVED / DECLINED` (constant `_STATUT_TERMINE = "TERMINÉ"` in `app/backend/modules/technicien/routes/interventions.py:35`). Never write `"TERMINEE"`.
- All new Pydantic response fields must be `Optional[str] = None` — every one of these rows can legitimately have no assigned user yet.
- No new test infrastructure: this repo's `app/backend/tests/unit/` contains only pure-Pydantic/pure-function tests, no async DB fixtures/conftest for route-level tests. Match that convention — write pure unit tests for schema shape and any extracted pure logic; verify the DB-query changes live via the browser against a running stack (this project already does this for AKS work, see project memory `aks-phase0-build.md`).

---

### Task 1: Generic `OrdresTravailResponse` — add `utilisateur_nom` / `validated_by_nom`

This feeds `AdminWorkOrdersList.tsx` (via `client.entities.ordres_travail.query`) and `ChetopValidationQueue.tsx`/`useAdminWorkOrderValidation.ts` (both already reference `wo.utilisateur_nom` in their TSX/TS — confirmed via grep, zero frontend changes needed for this task).

**Files:**
- Modify: `app/backend/modules/shared/routes/ordres_travail/schemas.py:43-71` (`OrdresTravailResponse`)
- Modify: `app/backend/services/ordres_travail.py:92-110` (`OrdresTravailService.get_list`)
- Test: `app/backend/tests/unit/test_ordres_travail_schemas.py` (new)

**Interfaces:**
- Produces: `OrdresTravailResponse.utilisateur_nom: Optional[str]`, `OrdresTravailResponse.validated_by_nom: Optional[str]` — read by frontend types `OrdreTravail.utilisateur_nom` (`app/frontend/src/lib/types.ts:39`) and `PendingAdminWorkOrder.utilisateur_nom` (`app/frontend/src/hooks/useAdminWorkOrderValidation.ts:16`).

- [ ] **Step 1: Write the failing test for the schema accepting the new fields**

```python
# app/backend/tests/unit/test_ordres_travail_schemas.py
"""Unit tests — OrdresTravailResponse name-enrichment fields (no DB, no async)."""
from datetime import datetime, timezone

from modules.shared.routes.ordres_travail.schemas import OrdresTravailResponse


def _base_row(**overrides) -> dict:
    base = {
        "id": 1,
        "titre": "OT-TEST",
        "description": "desc",
        "priorite": "MOYENNE",
        "machine_id": 1,
        "statut": "CLOSED",
        "created_at": datetime.now(timezone.utc),
    }
    return {**base, **overrides}


def test_ordres_travail_response_defaults_names_to_none():
    resp = OrdresTravailResponse(**_base_row())
    assert resp.utilisateur_nom is None
    assert resp.validated_by_nom is None


def test_ordres_travail_response_accepts_resolved_names():
    resp = OrdresTravailResponse(
        **_base_row(utilisateur_nom="Karim Ben Ali", validated_by_nom="Sami Trabelsi")
    )
    assert resp.utilisateur_nom == "Karim Ben Ali"
    assert resp.validated_by_nom == "Sami Trabelsi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/backend && python -m pytest tests/unit/test_ordres_travail_schemas.py -v`
Expected: FAIL — `TypeError: OrdresTravailResponse() got unexpected keyword arguments: 'utilisateur_nom', 'validated_by_nom'` (Pydantic v2 raises on unknown kwargs passed positionally to `__init__` in strict construction, or the assertions fail with `AttributeError` if extra="ignore" — either way, not passing).

- [ ] **Step 3: Add the two fields to the response schema**

In `app/backend/modules/shared/routes/ordres_travail/schemas.py`, inside `class OrdresTravailResponse(BaseModel):` (currently lines 43-71), add after the existing `validated_by: Optional[int] = None` line:

```python
    validated_by_nom: Optional[str] = None
    utilisateur_nom: Optional[str] = None
```

(Keep them adjacent to the existing `utilisateur_id`/`validated_by` int fields for readability — exact insertion point doesn't matter to Pydantic.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/backend && python -m pytest tests/unit/test_ordres_travail_schemas.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Enrich `get_list` with resolved names**

In `app/backend/services/ordres_travail.py`, add the import at the top:

```python
from models.utilisateurs import Utilisateurs
```

Replace the body of `get_list` (currently lines 92-110) with:

```python
    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of OrdresTravails, enriched with resolved
        utilisateur_nom / validated_by_nom (batch-fetched, no per-row query)."""
        try:
            query, count_query = self._apply_filters(
                select(OrdresTravail), select(func.count(OrdresTravail.id)), query_dict
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort)
            items = (await self.db.execute(query.offset(skip).limit(limit))).scalars().all()

            user_ids = {i.utilisateur_id for i in items if i.utilisateur_id is not None}
            user_ids |= {i.validated_by for i in items if i.validated_by is not None}
            id_to_nom: Dict[int, str] = {}
            if user_ids:
                rows = await self.db.execute(
                    select(Utilisateurs.id, Utilisateurs.nom).where(Utilisateurs.id.in_(user_ids))
                )
                id_to_nom = {row.id: row.nom for row in rows.all()}

            for item in items:
                item.utilisateur_nom = id_to_nom.get(item.utilisateur_id) if item.utilisateur_id else None
                item.validated_by_nom = id_to_nom.get(item.validated_by) if item.validated_by else None

            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching OrdresTravail list: {str(e)}")
            raise
```

(`item.utilisateur_nom = ...` sets a plain instance attribute on the SQLAlchemy ORM object — not a mapped column, never persisted, never flushed. `OrdresTravailResponse.model_validate(item)` with `from_attributes=True` — used implicitly by FastAPI's `response_model` — reads it via `getattr` same as any other attribute.)

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/shared/routes/ordres_travail/schemas.py app/backend/services/ordres_travail.py app/backend/tests/unit/test_ordres_travail_schemas.py
git commit -m "fix(backend): resolve utilisateur/validated_by names on OrdresTravail list"
```

---

### Task 2: CHETOP's `WorkOrderResponse` — add `utilisateur_nom`

Feeds `chetop/dashboard/components/WorkOrdersTab.tsx:53` (`{order.utilisateur_nom && <span>Assigné à: {order.utilisateur_nom}</span>}` — already wired, confirmed via grep).

**Files:**
- Modify: `app/backend/modules/chetop/schemas.py:32-45` (`WorkOrderResponse`)
- Modify: `app/backend/modules/chetop/routes/work_orders.py:1-56` (`get_work_orders`)
- Test: `app/backend/tests/unit/test_chetop_schemas.py` (new)

**Interfaces:**
- Produces: `WorkOrderResponse.utilisateur_nom: Optional[str]`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/unit/test_chetop_schemas.py
"""Unit tests — chetop WorkOrderResponse name-enrichment field (no DB, no async)."""
from datetime import datetime, timezone

from modules.chetop.schemas import WorkOrderResponse


def test_chetop_work_order_response_accepts_utilisateur_nom():
    resp = WorkOrderResponse(
        id=1, titre="OT", priorite="MOYENNE", statut="DRAFT", machine_id=1,
        created_at=datetime.now(timezone.utc), utilisateur_nom="Karim Ben Ali",
    )
    assert resp.utilisateur_nom == "Karim Ben Ali"


def test_chetop_work_order_response_defaults_utilisateur_nom_to_none():
    resp = WorkOrderResponse(
        id=1, titre="OT", priorite="MOYENNE", statut="DRAFT", machine_id=1,
        created_at=datetime.now(timezone.utc),
    )
    assert resp.utilisateur_nom is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/backend && python -m pytest tests/unit/test_chetop_schemas.py -v`
Expected: FAIL — `utilisateur_nom` not a recognized field on `WorkOrderResponse`.

- [ ] **Step 3: Add the field**

In `app/backend/modules/chetop/schemas.py`, inside `class WorkOrderResponse(BaseModel):` (lines 32-42), add after `machine_nom: Optional[str] = None`:

```python
    utilisateur_nom: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/backend && python -m pytest tests/unit/test_chetop_schemas.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Join Utilisateurs in the query**

In `app/backend/modules/chetop/routes/work_orders.py`, add the import:

```python
from models.utilisateurs import Utilisateurs
```

Replace the query construction (currently around lines 59-91) — change:

```python
            select(OrdresTravail, Machines.nom.label("machine_nom"))
```

to:

```python
            select(
                OrdresTravail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("utilisateur_nom"),
            )
```

and add, alongside whatever existing `.outerjoin(Machines, ...)` clause is already there:

```python
            .outerjoin(Utilisateurs, OrdresTravail.utilisateur_id == Utilisateurs.id)
```

Then update the row-unpacking loop (`for wo, machine_nom in rows` around line 91) to `for wo, machine_nom, utilisateur_nom in rows`, and add `utilisateur_nom=utilisateur_nom` to the dict/response construction alongside the existing `machine_nom=machine_nom` (around line 86).

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/chetop/schemas.py app/backend/modules/chetop/routes/work_orders.py app/backend/tests/unit/test_chetop_schemas.py
git commit -m "fix(backend): resolve utilisateur_nom on chetop work-order list"
```

---

### Task 3: CHEFTECH's `InterventionResponse` — fix `technicien_id` mismatch, add `technicien_nom` + `approved_by_nom`

**Root cause confirmed:** `app/backend/modules/cheftech/schemas.py`'s `InterventionResponse.technicien_id` never matches the real ORM attribute `OrdresIntervention.technician_id` (English spelling) — so with `from_attributes=True` it always serializes as `None`, even though `app/backend/modules/cheftech/routes/interventions.py:73` already eager-loads `selectinload(OrdresIntervention.technician)`. Frontend already renders the broken result: `app/frontend/src/modules/cheftech/dashboard/components/InterventionsTab.tsx:181` shows `Par: Tech #{intervention.technicien_id}` which is always `Par: ChefOp` (falsy branch) today.

**Files:**
- Modify: `app/backend/modules/cheftech/schemas.py:6-27` (`InterventionResponse`)
- Modify: `app/backend/modules/cheftech/routes/interventions.py:100-114` (`get_interventions` enrichment loop)
- Modify: `app/frontend/src/modules/cheftech/dashboard/components/InterventionsTab.tsx:180-182`
- Modify: `app/frontend/src/lib/types.ts:81-107` (`Intervention` interface)
- Test: `app/backend/tests/unit/test_cheftech_intervention_schemas.py` (new)

**Interfaces:**
- Produces: `InterventionResponse.technician_id: Optional[int]` (renamed from `technicien_id`), `InterventionResponse.technicien_nom: Optional[str]`, `InterventionResponse.approved_by_nom: Optional[str]`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/unit/test_cheftech_intervention_schemas.py
"""Unit tests — cheftech InterventionResponse technician-name fields (no DB, no async)."""
from datetime import datetime, timezone

from modules.cheftech.schemas import InterventionResponse


def _base(**overrides) -> dict:
    base = {"id": 1, "date_intervention": datetime.now(timezone.utc)}
    return {**base, **overrides}


def test_intervention_response_uses_technician_id_matching_orm_attribute():
    """Field must be named technician_id (matches OrdresIntervention.technician_id),
    not technicien_id — the old name never matched the ORM attribute and always
    serialized as None."""
    resp = InterventionResponse(**_base(technician_id=7))
    assert resp.technician_id == 7


def test_intervention_response_accepts_resolved_names():
    resp = InterventionResponse(
        **_base(technician_id=7, technicien_nom="Karim Ben Ali", approved_by=3, approved_by_nom="Sami Trabelsi")
    )
    assert resp.technicien_nom == "Karim Ben Ali"
    assert resp.approved_by_nom == "Sami Trabelsi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/backend && python -m pytest tests/unit/test_cheftech_intervention_schemas.py -v`
Expected: FAIL — `technician_id`/`technicien_nom`/`approved_by_nom` not recognized fields.

- [ ] **Step 3: Fix the field name and add name fields**

In `app/backend/modules/cheftech/schemas.py`, inside `class InterventionResponse(BaseModel):` (lines 6-27), change:

```python
    technicien_id: Optional[int] = None
```

to:

```python
    technician_id: Optional[int] = None
    technicien_nom: Optional[str] = None
```

and change:

```python
    approved_by: Optional[int] = None
```

to:

```python
    approved_by: Optional[int] = None
    approved_by_nom: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/backend && python -m pytest tests/unit/test_cheftech_intervention_schemas.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Populate the new fields in the route's enrichment loop**

In `app/backend/modules/cheftech/routes/interventions.py`, add the import:

```python
from models.utilisateurs import Utilisateurs
```

Before the `enriched: List[dict] = []` loop (currently starting at line 100), batch-fetch approver names:

```python
        approver_ids = {i.approved_by for i in interventions if i.approved_by is not None}
        approver_id_to_nom: dict = {}
        if approver_ids:
            approver_rows = await db.execute(
                select(Utilisateurs.id, Utilisateurs.nom).where(Utilisateurs.id.in_(approver_ids))
            )
            approver_id_to_nom = {row.id: row.nom for row in approver_rows.all()}
```

Then change the `enriched.append(...)` block (currently lines 108-114) from:

```python
            enriched.append(
                {
                    **InterventionResponse.model_validate(i).model_dump(),
                    "work_order_due_date": due,
                    "is_overdue": overdue,
                }
            )
```

to:

```python
            enriched.append(
                {
                    **InterventionResponse.model_validate(i).model_dump(),
                    "work_order_due_date": due,
                    "is_overdue": overdue,
                    "technicien_nom": i.technician.nom if i.technician else None,
                    "approved_by_nom": approver_id_to_nom.get(i.approved_by) if i.approved_by else None,
                }
            )
```

(`i.technician` is already loaded via the existing `selectinload(OrdresIntervention.technician)` at line 73 — no new query needed for that part.)

- [ ] **Step 6: Update the frontend type**

In `app/frontend/src/lib/types.ts`, inside `export interface Intervention {` (lines 81-107), change:

```typescript
  technicien_id?: number;
```

to:

```typescript
  technicien_id?: number;
  technicien_nom?: string;
  approved_by_nom?: string;
```

(Keep `technicien_id` in the TS interface as-is — the frontend's own field name doesn't need to match the backend's Python attribute name, only the JSON key, and the backend now correctly serializes `technician_id` under Pydantic's field name... **wait**: renaming the Pydantic field to `technician_id` changes the JSON key from `technicien_id` to `technician_id`. Update the frontend to match:)

Change `app/frontend/src/lib/types.ts` line 85 instead to:

```typescript
  technician_id?: number;
  technicien_nom?: string;
  approved_by_nom?: string;
```

- [ ] **Step 7: Fix the render in InterventionsTab.tsx**

In `app/frontend/src/modules/cheftech/dashboard/components/InterventionsTab.tsx`, change line 181 from:

```tsx
                          Par: {intervention.technicien_id ? `Tech #${intervention.technicien_id}` : 'ChefOp'}
```

to:

```tsx
                          Par: {intervention.technicien_nom || (intervention.technician_id ? `Tech #${intervention.technician_id}` : 'ChefOp')}
```

- [ ] **Step 8: Search for other frontend readers of the renamed field**

Run: `grep -rn "technicien_id" app/frontend/src/modules/cheftech/` (or use the Grep tool) to confirm no other cheftech component reads the old `technicien_id` JSON key from this specific endpoint's response. Fix any found the same way as Step 7.

- [ ] **Step 9: Commit**

```bash
git add app/backend/modules/cheftech/schemas.py app/backend/modules/cheftech/routes/interventions.py app/frontend/src/lib/types.ts app/frontend/src/modules/cheftech/dashboard/components/InterventionsTab.tsx app/backend/tests/unit/test_cheftech_intervention_schemas.py
git commit -m "fix(backend,frontend): resolve technician/approver names on cheftech intervention list"
```

---

### Task 4: Technicien's `InterventionResponse` — add `approved_by_nom`

Technicien's own intervention list (`GET /api/v1/technicien/interventions`) always shows the current technician's own interventions (no need to display their own name), but `approved_by` (the CHEFTECH who approved) is currently a bare int with no name anywhere in the response or frontend.

**Files:**
- Modify: `app/backend/modules/technicien/schemas.py:6-54` (`InterventionResponse`)
- Modify: `app/backend/modules/technicien/routes/interventions.py:39-112` (`list_my_interventions`)
- Test: `app/backend/tests/unit/test_technicien_intervention_schemas.py` (new)

**Interfaces:**
- Produces: `InterventionResponse.approved_by_nom: Optional[str]`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/unit/test_technicien_intervention_schemas.py
"""Unit tests — technicien InterventionResponse approved_by_nom field (no DB, no async)."""
from datetime import datetime, timezone

from modules.technicien.schemas import InterventionResponse


def test_intervention_response_accepts_approved_by_nom():
    resp = InterventionResponse(
        id=1, date_intervention=datetime.now(timezone.utc), approved_by=3, approved_by_nom="Sami Trabelsi",
    )
    assert resp.approved_by_nom == "Sami Trabelsi"


def test_intervention_response_defaults_approved_by_nom_to_none():
    resp = InterventionResponse(id=1, date_intervention=datetime.now(timezone.utc))
    assert resp.approved_by_nom is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/backend && python -m pytest tests/unit/test_technicien_intervention_schemas.py -v`
Expected: FAIL — `approved_by_nom` not a recognized field.

- [ ] **Step 3: Add the field**

In `app/backend/modules/technicien/schemas.py`, inside `class InterventionResponse(BaseModel):` (lines 6-54), add directly after the existing `approved_by: Optional[int] = None` (line 17):

```python
    approved_by_nom: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/backend && python -m pytest tests/unit/test_technicien_intervention_schemas.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Populate it in `list_my_interventions`**

In `app/backend/modules/technicien/routes/interventions.py`, add the import:

```python
from models.utilisateurs import Utilisateurs
```

Before the `enriched: List[dict] = []` loop (currently starting at line 96), batch-fetch approver names:

```python
    approver_ids = {i.approved_by for i in interventions if i.approved_by is not None}
    approver_id_to_nom: dict = {}
    if approver_ids:
        approver_rows = await db.execute(
            select(Utilisateurs.id, Utilisateurs.nom).where(Utilisateurs.id.in_(approver_ids))
        )
        approver_id_to_nom = {row.id: row.nom for row in approver_rows.all()}
```

Then change the `enriched.append(...)` block (currently lines 104-110) from:

```python
        enriched.append(
            {
                **InterventionResponse.model_validate(i).model_dump(),
                "work_order_due_date": due,
                "is_overdue": overdue,
            }
        )
```

to:

```python
        enriched.append(
            {
                **InterventionResponse.model_validate(i).model_dump(),
                "work_order_due_date": due,
                "is_overdue": overdue,
                "approved_by_nom": approver_id_to_nom.get(i.approved_by) if i.approved_by else None,
            }
        )
```

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/technicien/schemas.py app/backend/modules/technicien/routes/interventions.py app/backend/tests/unit/test_technicien_intervention_schemas.py
git commit -m "fix(backend): resolve approved_by_nom on technicien intervention list"
```

---

### Task 5: Wire P4/P7 ML feedback into the real PDCA work-order-completion endpoint

**Root cause confirmed:** `record_p4_feedback`/`record_p7_feedback` currently only fire from `PUT /api/v1/technicien/interventions/{id}/status` (`app/backend/modules/technicien/routes/interventions.py:234-247`). The endpoint technicians actually use to close out real work — `PATCH /api/v1/technicien/work-orders/{id}/complete` (`complete_work_order` in `app/backend/modules/technicien/technicien_work_orders.py:417-471`, which calls `_update_intervention_fields` to set `intervention.statut = _STATUT_TERMINE` and fill PDCA fields) — never calls either feedback function. So work orders completed through the real PDCA flow never produce P4/P7 feedback metrics.

**Files:**
- Modify: `app/backend/modules/technicien/technicien_work_orders.py:417-471` (`complete_work_order`)
- Test: `app/backend/tests/unit/test_technicien_work_orders_feedback_wiring.py` (new)

**Interfaces:**
- Consumes: `record_p7_feedback(intervention_id: int, db: AsyncSession) -> Optional[Dict]` from `app/backend/modules/ml/services/p7_feedback.py`; `record_p4_feedback(intervention_id: int, db: AsyncSession, window_days: int = 14) -> Optional[Dict]` from `app/backend/modules/ml/services/p4_feedback.py` — both already exist, both already non-fatal by design (catch their own exceptions internally per their docstrings, but the *call site* must still not let an unexpected error break the completion response, mirroring the try/except pattern in `interventions.py:234-247`).

- [ ] **Step 1: Write a test confirming the call site exists and is non-fatal, via source inspection**

Since there is no async-DB test harness in this repo's `tests/unit/` (confirmed — all existing tests here are pure-Python/Pydantic), write a lightweight static check instead of an integration test:

```python
# app/backend/tests/unit/test_technicien_work_orders_feedback_wiring.py
"""Confirms complete_work_order() calls both ML feedback hooks — a source-level
check because this repo's tests/unit/ has no async DB fixture to exercise the
route directly (see pytest.ini: testpaths = tests, no conftest under tests/unit/)."""
import ast
from pathlib import Path


def _get_function_source(file_path: Path, function_name: str) -> str:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            return ast.get_source_segment(file_path.read_text(encoding="utf-8"), node)
    raise AssertionError(f"{function_name} not found in {file_path}")


def test_complete_work_order_calls_p7_and_p4_feedback():
    file_path = Path(__file__).parent.parent.parent / "modules" / "technicien" / "technicien_work_orders.py"
    source = _get_function_source(file_path, "complete_work_order")
    assert "record_p7_feedback(" in source, "complete_work_order must call record_p7_feedback"
    assert "record_p4_feedback(" in source, "complete_work_order must call record_p4_feedback"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/backend && python -m pytest tests/unit/test_technicien_work_orders_feedback_wiring.py -v`
Expected: FAIL — neither call present yet in `complete_work_order`.

- [ ] **Step 3: Add the feedback calls**

In `app/backend/modules/technicien/technicien_work_orders.py`, inside `complete_work_order` (currently lines 417-471), immediately after the line:

```python
            await _update_intervention_fields(db, intervention, payload, wo.date_debut, now)
```

add:

```python
            # P7.6 + P4.3 feedback — non-fatal, mirrors the pattern already
            # used in modules/technicien/routes/interventions.py's status endpoint.
            if intervention.legacy_parts_text:
                try:
                    from modules.ml.services.p7_feedback import record_p7_feedback
                    await record_p7_feedback(intervention.id, db)
                except Exception as _fb_err:
                    logger.debug(f"[P7-feedback] non-fatal error: {_fb_err}")
            try:
                from modules.ml.services.p4_feedback import record_p4_feedback
                await record_p4_feedback(intervention.id, db)
            except Exception as _fb_err:
                logger.debug(f"[P4-feedback] non-fatal error: {_fb_err}")
```

(Placed after `_update_intervention_fields` so `intervention.legacy_parts_text` and `intervention.date_intervention` — which both feedback functions read — are already set to their final values from this completion call. `payload.parts_replaced` is written into `legacy_parts_text` inside `_update_intervention_fields`, confirmed at line 288.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/backend && python -m pytest tests/unit/test_technicien_work_orders_feedback_wiring.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full unit test suite to check for regressions**

Run: `cd app/backend && python -m pytest tests/unit/ -v`
Expected: all tests pass (previous count + 7 new tests from Tasks 1-5)

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/technicien/technicien_work_orders.py app/backend/tests/unit/test_technicien_work_orders_feedback_wiring.py
git commit -m "fix(backend): wire P4/P7 ML feedback into the real PDCA work-order-complete endpoint"
```

---

### Task 6: Rebuild and redeploy backend + frontend images to eam-staging, verify live

**Files:** none (deployment only)

- [ ] **Step 1: Rebuild backend and frontend Docker images**

```bash
docker build -t eamdemoacr24102.azurecr.io/backend:aks-staging -f app/backend/Dockerfile app/backend
docker build -t eamdemoacr24102.azurecr.io/frontend:aks-staging -f app/frontend/Dockerfile app/frontend
```

Expected: both images build successfully with no errors.

- [ ] **Step 2: Push images to ACR**

```bash
docker push eamdemoacr24102.azurecr.io/backend:aks-staging
docker push eamdemoacr24102.azurecr.io/frontend:aks-staging
```

Expected: push completes, both tags visible in ACR.

- [ ] **Step 3: Force pod restart in eam-staging (imagePullPolicy is already `Always` per project memory `aks-phase0-build.md`)**

```bash
kubectl rollout restart deployment/backend -n eam-staging
kubectl rollout restart deployment/frontend -n eam-staging
kubectl rollout status deployment/backend -n eam-staging
kubectl rollout status deployment/frontend -n eam-staging
```

Expected: both deployments report `successfully rolled out`.

- [ ] **Step 4: Verify live via browser (port-forward, same method used earlier this session)**

```bash
kubectl port-forward svc/frontend 3000:80 -n eam-staging
```

Then in the Browser pane: log in as `staging-verify-2026@gmail.com` / `StagingTest123!`, open the Admin work-orders list and confirm assigned/validated-by names render instead of blanks (there will be few/no real names yet since eam-staging has no seed data — full visual confirmation happens after Plan 2's seed script runs, but this step confirms no 500 errors / schema mismatches from the changes in Tasks 1-5).

---

## Self-Review Notes

- **Spec coverage:** Bug 6 (names) — Tasks 1-4 cover the 4 confirmed-broken views (Admin generic, CHETOP, CHEFTECH, Technicien). Bug 7 (feedback wiring) — Task 5. Deployment/verification — Task 6.
- **Explicitly out of scope for this plan** (flagged separately, not silently dropped):
  - `GET /api/v1/admin/work-orders/pending-admin-validation` and its two sibling endpoints don't exist at all (404, frontend gracefully degrades to an empty list) — this is a missing feature, not a missing name field. Flagged via a separate background task (`task_da302ff6`).
  - `GET /api/v1/entities/utilisateurs/all` has no authentication and leaks every user's id/nom/email/role/password-hash — a real, unrelated security bug found while investigating this plan. Flagged via a separate background task (`task_b989f125`).
  - `app/backend/modules/cheftech/cheftech_work_orders.py`'s `/api/v1/cheftech/work-orders-table` endpoint (feeds `ChefTechWorkOrdersTable.tsx`) was checked and is **already correct** — it already joins `Utilisateurs` via the intervention's `technician_id` and returns `technicien_nom`/`technicien_email` for real. No change needed there.
  - Generic `OrdresInterventionResponse` (`/api/v1/entities/ordres_intervention`) was not enriched — no frontend consumer of it was found in this session's investigation (Admin's UI uses the generic *work-order* entity endpoint, not the generic intervention one, for its lists). If a future session finds a consumer, apply the same pattern as Task 1.
