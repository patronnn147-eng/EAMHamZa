# Telemetry Time-Series ML Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale static telemetry columns on `machines` with real time-series data from `machine_telemetry_logs`, and wire the full history into every ML model that benefits from sequential input.

**Architecture:** Rename `machine_telemetry_logs` columns to match ML feature names, drop the redundant static columns from `machines`, query the full telemetry history per machine in the ML router, pass it as `_logs` to the ML microservice, and update CUSUM/Mahalanobis/Survival/Kalman to use the sequence instead of a single scalar.

**Tech Stack:** SQLAlchemy 2, Alembic, FastAPI, numpy, scikit-learn, lifelines (Cox PH), PyTorch (PINN — optional)

---

## File Map

| File | Role |
|---|---|
| `app/backend/alembic/versions/rename_telemetry_cols.py` | New migration: rename 4 cols, drop 5 cols |
| `app/backend/models/machine_telemetry.py` | SQLAlchemy model — rename column defs |
| `app/backend/models/machines.py` | SQLAlchemy model — drop 5 column defs |
| `app/backend/modules/technicien/schemas_telemetry.py` | Pydantic schemas — rename fields |
| `app/backend/modules/chetop/schemas.py` | Pydantic schema for chetop work order payload |
| `app/backend/modules/technicien/technicien_work_orders.py` | Insert col names update |
| `app/backend/modules/chetop/routes/work_orders.py` | Insert col names update + remove machines block |
| `app/backend/modules/ml/router.py` | Query telemetry list, pass to RUL calc + ML client |
| `app/backend/modules/ml/rul_calculator.py` | Accept list, latest scalars, degradation rate |
| `app/backend/core/ml_client.py` | Add `_logs` + `machine_id` to predict_all payload |
| `app/ml-microservice/src/router.py` | Add optional `_logs`/`machine_id` to TelemetryInput |
| `app/ml-microservice/src/anomaly_cusum.py` | Add `replay_history()` to AnomalyEnsemble |
| `app/ml-microservice/src/health_index.py` | Add `fit_and_score_history()` to MahalanobisHealthIndex |
| `app/ml-microservice/src/survival_model.py` | Wire `fit_from_logs()` into `predict_all` path |
| `app/ml-microservice/src/kalman_estimator.py` | Add `smooth_from_scores()` for history replay |
| `app/ml-microservice/src/predictions.py` | Use `_logs` in all 4 time-series model calls |

---

## Task 1: Alembic Migration

**Files:**
- Create: `app/backend/alembic/versions/rename_telemetry_cols.py`

- [ ] **Step 1: Create the migration file**

```python
"""Rename machine_telemetry_logs columns and drop machines telemetry columns

Revision ID: rename_telemetry_cols
Revises: add_machine_telemetry_columns
Create Date: 2026-04-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "rename_telemetry_cols"
down_revision: Union[str, Sequence[str], None] = "add_machine_telemetry_columns"
branch_labels = None
depends_on = None


def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    r = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    )
    return r.first() is not None


def upgrade() -> None:
    # --- machine_telemetry_logs: rename placeholder cols ---
    renames = [
        ("temperature", "air_temperature"),
        ("vibration",   "process_temperature"),
        ("rpm",         "rotational_speed"),
        ("power",       "tool_wear"),
    ]
    for old, new in renames:
        if _col_exists("machine_telemetry_logs", old):
            op.alter_column("machine_telemetry_logs", old, new_column_name=new)

    # --- machines: drop static telemetry columns ---
    for col in ["air_temperature", "process_temperature",
                "rotational_speed", "torque", "tool_wear"]:
        if _col_exists("machines", col):
            op.drop_column("machines", col)


def downgrade() -> None:
    # Restore machines columns
    op.add_column("machines", sa.Column("air_temperature",    sa.Float(),   nullable=True))
    op.add_column("machines", sa.Column("process_temperature",sa.Float(),   nullable=True))
    op.add_column("machines", sa.Column("rotational_speed",   sa.Integer(), nullable=True))
    op.add_column("machines", sa.Column("torque",             sa.Float(),   nullable=True))
    op.add_column("machines", sa.Column("tool_wear",          sa.Integer(), nullable=True))
    # Reverse renames on machine_telemetry_logs
    renames = [
        ("air_temperature",   "temperature"),
        ("process_temperature","vibration"),
        ("rotational_speed",  "rpm"),
        ("tool_wear",         "power"),
    ]
    for old, new in renames:
        if _col_exists("machine_telemetry_logs", old):
            op.alter_column("machine_telemetry_logs", old, new_column_name=new)
```

- [ ] **Step 2: Run migration**

```bash
cd app/backend
alembic upgrade head
```

Expected output: `Running upgrade add_machine_telemetry_columns -> rename_telemetry_cols`

- [ ] **Step 3: Verify in DB**

```bash
cd app/backend
python -c "
from core.database import engine
import sqlalchemy as sa
with engine.connect() as conn:
    res = conn.execute(sa.text(\"SELECT column_name FROM information_schema.columns WHERE table_name='machine_telemetry_logs' ORDER BY ordinal_position\"))
    print('telemetry cols:', [r[0] for r in res])
    res2 = conn.execute(sa.text(\"SELECT column_name FROM information_schema.columns WHERE table_name='machines' ORDER BY ordinal_position\"))
    print('machines cols:', [r[0] for r in res2])
"
```

Expected: telemetry cols include `air_temperature`, `process_temperature`, `rotational_speed`, `tool_wear`. Machines cols do NOT include any of the 5 dropped columns.

- [ ] **Step 4: Commit**

```bash
git add app/backend/alembic/versions/rename_telemetry_cols.py
git commit -m "feat(db): rename telemetry cols and drop stale machine sensor columns"
```

---

## Task 2: Update SQLAlchemy Models

**Files:**
- Modify: `app/backend/models/machine_telemetry.py`
- Modify: `app/backend/models/machines.py`

- [ ] **Step 1: Update MachineTelemetry model**

Replace the sensor column block in `app/backend/models/machine_telemetry.py`:

```python
# Replace these 5 lines:
#   temperature = Column(Float(), nullable=False)
#   vibration   = Column(Float(), nullable=False)
#   rpm         = Column(Integer(), nullable=False)
#   torque      = Column(Float(), nullable=False)
#   power       = Column(Float(), nullable=False)

# With:
    air_temperature     = Column(Float(), nullable=False)
    process_temperature = Column(Float(), nullable=False)
    rotational_speed    = Column(Integer(), nullable=False)
    torque              = Column(Float(), nullable=False)
    tool_wear           = Column(Float(), nullable=False)
```

Full updated file `app/backend/models/machine_telemetry.py`:

```python
from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class MachineTelemetry(Base):
    __tablename__ = "machine_telemetry_logs"
    __table_args__ = {"extend_existing": True}

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id          = Column(Integer, nullable=False, index=True)
    work_order_id       = Column(Integer, nullable=True, index=True)
    technician_id       = Column(Integer, nullable=False)

    air_temperature     = Column(Float(), nullable=False)
    process_temperature = Column(Float(), nullable=False)
    rotational_speed    = Column(Integer(), nullable=False)
    torque              = Column(Float(), nullable=False)
    tool_wear           = Column(Float(), nullable=False)

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 2: Remove static telemetry columns from Machines model**

In `app/backend/models/machines.py`, delete the entire `# Sensor Telemetry for ML failure simulation` block (lines 27-34):

```python
# DELETE these lines:
#     # Sensor Telemetry for ML failure simulation
#     air_temperature     = Column(Float(), nullable=True)
#     process_temperature = Column(Float(), nullable=True)
#     rotational_speed    = Column(Integer(), nullable=True)
#     torque              = Column(Float(), nullable=True)
#     tool_wear           = Column(Integer(), nullable=True)
```

The resulting `machines.py` sensor section ends at `image_url` and `created_at`. No sensor columns remain.

- [ ] **Step 3: Verify Python imports cleanly**

```bash
cd app/backend
python -c "from models.machine_telemetry import MachineTelemetry; from models.machines import Machines; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/backend/models/machine_telemetry.py app/backend/models/machines.py
git commit -m "feat(models): rename MachineTelemetry columns, remove stale sensor cols from Machines"
```

---

## Task 3: Update Pydantic Schemas

**Files:**
- Modify: `app/backend/modules/technicien/schemas_telemetry.py`

- [ ] **Step 1: Rewrite schemas_telemetry.py with renamed fields**

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MachineTelemetryBase(BaseModel):
    air_temperature:     float = Field(..., description="Air temperature in Kelvin",       ge=250,  le=400)
    process_temperature: float = Field(..., description="Process temperature in Kelvin",   ge=250,  le=450)
    rotational_speed:    int   = Field(..., description="Rotational speed in RPM",         ge=0,    le=10000)
    torque:              float = Field(..., description="Torque in Nm",                    ge=0,    le=1000)
    tool_wear:           float = Field(..., description="Tool wear in minutes",            ge=0,    le=500)
    notes: Optional[str] = None


class MachineTelemetryCreate(MachineTelemetryBase):
    machine_id:    int
    work_order_id: Optional[int] = None
    recorded_at:   datetime = Field(default_factory=datetime.utcnow)


class MachineTelemetryResponse(MachineTelemetryBase):
    id:            int
    machine_id:    int
    work_order_id: Optional[int] = None
    technician_id: int
    recorded_at:   datetime
    notes:         Optional[str] = None
    created_at:    datetime

    class Config:
        from_attributes = True


class MachineTelemetryLatest(BaseModel):
    machine_id:          int
    machine_nom:         Optional[str] = None
    air_temperature:     float
    process_temperature: float
    rotational_speed:    int
    torque:              float
    tool_wear:           float
    recorded_at:         datetime
    recorded_by:         Optional[str] = None
    work_order_id:       Optional[int] = None


class MachineTelemetryListResponse(BaseModel):
    items: List[MachineTelemetryResponse]
    total: int
    page:  int
    size:  int
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
cd app/backend
python -c "from modules.technicien.schemas_telemetry import MachineTelemetryResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/backend/modules/technicien/schemas_telemetry.py
git commit -m "feat(schemas): rename telemetry Pydantic fields to match ML feature names"
```

---

## Task 4: Update Work Order Completion Handlers

**Files:**
- Modify: `app/backend/modules/technicien/technicien_work_orders.py`
- Modify: `app/backend/modules/chetop/routes/work_orders.py`

- [ ] **Step 1: Update technicien handler insert**

In `technicien_work_orders.py`, find the `MachineTelemetry(` block (around line 257) and replace:

```python
# OLD:
            telemetry = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=wo.id,
                technician_id=current_user.id,
                temperature=payload.telemetry_temperature or 0,
                vibration=payload.telemetry_vibration or 0,
                rpm=payload.telemetry_rpm or 0,
                torque=payload.telemetry_torque or 0,
                power=payload.telemetry_power or 0,
                recorded_at=now,
                notes=payload.telemetry_notes,
            )

# NEW:
            telemetry = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=wo.id,
                technician_id=current_user.id,
                air_temperature=payload.telemetry_temperature or 0,
                process_temperature=payload.telemetry_vibration or 0,
                rotational_speed=payload.telemetry_rpm or 0,
                torque=payload.telemetry_torque or 0,
                tool_wear=payload.telemetry_power or 0,
                recorded_at=now,
                notes=payload.telemetry_notes,
            )
```

- [ ] **Step 2: Update chetop handler insert and remove machines update block**

In `chetop/routes/work_orders.py`, find the `MachineTelemetry(` block (around line 183) and replace:

```python
# OLD:
            telemetry_log = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=order_id,
                technician_id=current_user.id,
                temperature=payload.air_temperature or payload.process_temperature,
                vibration=None,
                rpm=payload.rotational_speed,
                torque=payload.torque,
                power=None,
                recorded_at=now,
                notes=f"Work order #{order_id} completion"
            )

# NEW:
            telemetry_log = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=order_id,
                technician_id=current_user.id,
                air_temperature=payload.air_temperature or 0,
                process_temperature=payload.process_temperature or 0,
                rotational_speed=payload.rotational_speed or 0,
                torque=payload.torque or 0,
                tool_wear=payload.tool_wear or 0,
                recorded_at=now,
                notes=f"Work order #{order_id} completion"
            )
```

Then delete the entire `# Task 5: Update machine's current state with latest telemetry` block in `chetop/routes/work_orders.py` (the `machine_result = await db.execute(...)` through `machine.tool_wear = payload.tool_wear` lines inclusive).

- [ ] **Step 3: Verify both files parse**

```bash
cd app/backend
python -c "
import ast, sys
for f in [
    'modules/technicien/technicien_work_orders.py',
    'modules/chetop/routes/work_orders.py',
]:
    ast.parse(open(f).read())
    print(f, 'OK')
"
```

Expected: both lines print `OK`

- [ ] **Step 4: Commit**

```bash
git add app/backend/modules/technicien/technicien_work_orders.py
git add app/backend/modules/chetop/routes/work_orders.py
git commit -m "feat(handlers): update telemetry insert column names, remove stale machines update"
```

---

## Task 5: Update ML Router to Query Telemetry History

**Files:**
- Modify: `app/backend/modules/ml/router.py`

- [ ] **Step 1: Add MachineTelemetry import to router.py**

At the top of `app/backend/modules/ml/router.py`, add:

```python
from models.machine_telemetry import MachineTelemetry
```

- [ ] **Step 2: Add helper function to build telemetry log dicts**

After the imports block in `router.py`, add:

```python
async def _get_telemetry_history(machine_id: int, db: AsyncSession):
    """
    Query all telemetry entries for a machine ordered oldest-first.
    Returns list of dicts compatible with FeatureStore.build_time_series_from_logs.
    """
    from sqlalchemy import asc
    result = await db.execute(
        select(MachineTelemetry)
        .where(MachineTelemetry.machine_id == machine_id)
        .order_by(asc(MachineTelemetry.recorded_at))
    )
    entries = result.scalars().all()
    return entries, [
        {
            "machine_id":           machine_id,
            "air_temperature":      e.air_temperature,
            "process_temperature":  e.process_temperature,
            "rotational_speed":     e.rotational_speed,
            "torque":               e.torque,
            "tool_wear":            e.tool_wear,
            "created_at":           e.recorded_at.isoformat() if e.recorded_at else "",
            "risk_level":           "LOW",
        }
        for e in entries
    ]
```

- [ ] **Step 3: Update get_unified_health to use telemetry history**

Replace the `fusion_result` block in `get_unified_health` (lines ~89-101):

```python
    # OLD:
    # fusion_result: Optional[Dict] = None
    # try:
    #     if await is_ml_service_available():
    #         fusion_result = await ml_client.predict_all(
    #             air_temperature=float(getattr(machine, "air_temperature", 300) or 300),
    #             ...
    #         )
    # except Exception:
    #     pass

    # NEW:
    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    # Derive scalar inputs: latest entry or defaults
    if telemetry_entries:
        latest = telemetry_entries[-1]
        _air   = float(latest.air_temperature)
        _proc  = float(latest.process_temperature)
        _rpm   = int(latest.rotational_speed)
        _torq  = float(latest.torque)
        _wear  = float(latest.tool_wear)
    else:
        _air, _proc, _rpm, _torq, _wear = 300.0, 310.0, 1500, 40.0, 0.0

    fusion_result: Optional[Dict] = None
    try:
        if await is_ml_service_available():
            fusion_result = await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
            )
    except Exception:
        pass
```

- [ ] **Step 4: Pass telemetry_entries to RULCalculator in get_unified_health**

Replace the `prediction = RULCalculator.calculate_rul(` call:

```python
    # OLD:
    prediction = RULCalculator.calculate_rul(
        machine,
        interventions,
        open_work_orders=open_wo_count,
        recent_interventions=recent_count,
        fusion_result=fusion_result,
    )

    # NEW:
    prediction = RULCalculator.calculate_rul(
        machine,
        interventions,
        telemetry_entries=telemetry_entries,
        open_work_orders=open_wo_count,
        recent_interventions=recent_count,
        fusion_result=fusion_result,
    )
```

- [ ] **Step 5: Apply same changes to get_machine_prediction**

In `get_machine_prediction` (line ~140), replace the fusion block similarly:

```python
    # After fetching interventions and open_wo_count, add:
    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    if telemetry_entries:
        latest = telemetry_entries[-1]
        _air   = float(latest.air_temperature)
        _proc  = float(latest.process_temperature)
        _rpm   = int(latest.rotational_speed)
        _torq  = float(latest.torque)
        _wear  = float(latest.tool_wear)
    else:
        _air, _proc, _rpm, _torq, _wear = 300.0, 310.0, 1500, 40.0, 0.0

    fusion_result: Optional[Dict] = None
    try:
        if await is_ml_service_available():
            fusion_result = await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
            )
    except Exception:
        pass

    prediction = RULCalculator.calculate_rul(
        machine,
        interventions,
        telemetry_entries=telemetry_entries,
        open_work_orders=open_wo_count,
        recent_interventions=recent_interventions_count,
        fusion_result=fusion_result,
    )
```

- [ ] **Step 6: Verify router parses**

```bash
cd app/backend
python -c "import ast; ast.parse(open('modules/ml/router.py').read()); print('OK')"
```

- [ ] **Step 7: Commit**

```bash
git add app/backend/modules/ml/router.py
git commit -m "feat(ml-router): query telemetry history and pass to RUL calculator and ML client"
```

---

## Task 6: Update ML Client and Microservice Input Schema

**Files:**
- Modify: `app/backend/core/ml_client.py`
- Modify: `app/ml-microservice/src/router.py`

- [ ] **Step 1: Update ml_client.py predict_all signature**

In `app/backend/core/ml_client.py`, update the `predict_all` method:

```python
    async def predict_all(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int,
        machine_id: int = -1,
        telemetry_logs: list = None,
    ) -> Dict:
        """Get all P1-P6 predictions plus DST fusion."""
        client = await self.get_client()
        payload = {
            "air_temperature":    air_temperature,
            "process_temperature": process_temperature,
            "rotational_speed":   rotational_speed,
            "torque":             torque,
            "tool_wear":          tool_wear,
            "machine_id":         machine_id,
        }
        if telemetry_logs:
            payload["_logs"] = telemetry_logs
        response = await client.post("/api/v1/ml/predict-all", json=payload)
        return response.json()
```

- [ ] **Step 2: Update TelemetryInput in ml-microservice router**

In `app/ml-microservice/src/router.py`, update the `TelemetryInput` model:

```python
class TelemetryInput(BaseModel):
    """Input telemetry data for predictions."""
    air_temperature:    float
    process_temperature: float
    rotational_speed:   int
    torque:             float
    tool_wear:          int
    machine_id:         Optional[int] = -1
    _logs:              Optional[List[Dict]] = None

    class Config:
        # Allow underscore-prefixed fields
        populate_by_name = True
```

Also add `from typing import List, Dict` to the import if not already present (it is in the existing file).

- [ ] **Step 3: Verify both files parse**

```bash
cd app/backend
python -c "import ast; ast.parse(open('core/ml_client.py').read()); print('ml_client OK')"
cd ../ml-microservice
python -c "import ast; ast.parse(open('src/router.py').read()); print('router OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/backend/core/ml_client.py app/ml-microservice/src/router.py
git commit -m "feat(ml-client): pass machine_id and telemetry history to ML microservice"
```

---

## Task 7: Update RUL Calculator

**Files:**
- Modify: `app/backend/modules/ml/rul_calculator.py`

- [ ] **Step 1: Update calculate_rul signature and Step 1 telemetry extraction**

Replace the entire `# --- Step 1: Telemetry Data Extraction ---` block and the method signature:

```python
    @staticmethod
    def calculate_rul(
        machine: Machines,
        interventions: List[Ordres_intervention],
        telemetry_entries=None,          # List[MachineTelemetry] — optional
        open_work_orders: int = 0,
        recent_interventions: int = 0,
        fusion_result: Optional[Dict] = None,
    ) -> Dict:
```

Replace Step 1 body:

```python
        # --- Step 1: Telemetry Data Extraction ---
        # Use latest entry from history; fall back to hardcoded defaults for new machines
        entries = telemetry_entries or []

        if entries:
            latest = entries[-1]
            air_temp     = float(latest.air_temperature)
            process_temp = float(latest.process_temperature)
            rpm          = int(latest.rotational_speed)
            torque       = float(latest.torque)
            tool_wear    = float(latest.tool_wear)
        else:
            air_temp, process_temp, rpm, torque, tool_wear = 300.0, 310.0, 1500, 40.0, 0.0

        temp_delta = process_temp - air_temp
        rpm_torque = (float(rpm) * float(torque)) / 1000.0

        # --- Step 1b: Degradation Rate ---
        # (latest - first) / (n - 1) per sensor; 0 if single or no entry
        def _deg_rate(attr: str) -> float:
            if len(entries) < 2:
                return 0.0
            first = float(getattr(entries[0], attr))
            last  = float(getattr(entries[-1], attr))
            return (last - first) / (len(entries) - 1)

        deg_air   = _deg_rate("air_temperature")
        deg_proc  = _deg_rate("process_temperature")
        deg_rpm   = _deg_rate("rotational_speed")
        deg_torque= _deg_rate("torque")
        deg_wear  = _deg_rate("tool_wear")

        # Composite degradation magnitude (0 = stable, higher = faster degradation)
        deg_magnitude = (
            abs(deg_air) / 10.0 +
            abs(deg_proc) / 10.0 +
            abs(deg_wear) / 5.0
        )
```

- [ ] **Step 2: Apply degradation rate to rul_days**

After the existing `rul_days` calculation (around line 59), add:

```python
        # Apply degradation rate: reduce RUL proportionally (cap at 50% reduction)
        if deg_magnitude > 0:
            degradation_factor = max(0.5, 1.0 - min(0.5, deg_magnitude * 0.1))
            rul_days = rul_days * degradation_factor
```

- [ ] **Step 3: Update data_points in response**

In the response dict, update:

```python
            "data_points": len(entries),
```

Also add degradation info to `health_breakdown`:

```python
                "degradation_rate_air":   round(float(deg_air),    4),
                "degradation_rate_wear":  round(float(deg_wear),   4),
                "degradation_magnitude":  round(float(deg_magnitude), 4),
```

- [ ] **Step 4: Remove old static field echoes from response**

Delete these lines from the response dict (they referenced the now-deleted machine columns):

```python
            # DELETE:
            "air_temperature": float(air_temp),
            "process_temperature": float(process_temp),
            "rotational_speed": int(rpm),
            "torque": float(torque),
            "tool_wear": int(tool_wear)
```

Replace with:
```python
            "air_temperature":    round(float(air_temp), 2),
            "process_temperature":round(float(process_temp), 2),
            "rotational_speed":   int(rpm),
            "torque":             round(float(torque), 2),
            "tool_wear":          round(float(tool_wear), 2),
            "telemetry_data_points": len(entries),
```

- [ ] **Step 5: Verify**

```bash
cd app/backend
python -c "import ast; ast.parse(open('modules/ml/rul_calculator.py').read()); print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/ml/rul_calculator.py
git commit -m "feat(rul-calc): accept telemetry history list, compute degradation rate, apply to RUL"
```

---

## Task 8: Update CUSUM — Replay History

**Files:**
- Modify: `app/ml-microservice/src/anomaly_cusum.py`

- [ ] **Step 1: Add replay_history method to AnomalyEnsemble**

After the existing `predict()` method in `AnomalyEnsemble`, add:

```python
    def replay_history(
        self,
        history: List[np.ndarray],
        feature_names: List[str] = None,
    ) -> None:
        """
        Warm-start CUSUM state by replaying historical observations (excluding latest).

        Resets CUSUM statistics to zero first, then sequentially updates each
        detector with all entries except the last (the latest will be scored
        via predict()). This initializes cumulative sums to reflect real
        accumulated drift rather than cold-starting at zero.

        Args:
            history: List of 1-D arrays, each of shape (n_features,), oldest first.
                     Should be all entries EXCEPT the last one.
            feature_names: Column names matching the order of each array.
                           Defaults to self._baselines keys in insertion order.
        """
        if not self._fitted or len(history) == 0:
            return

        names = feature_names or list(self._baselines.keys())
        # Reset CUSUM stats before replay
        for det in self._cusums.values():
            det.reset()

        for obs in history:
            obs_arr = np.asarray(obs, dtype=float)
            for i, name in enumerate(names):
                if name not in self._cusums or i >= len(obs_arr):
                    continue
                mu, _ = self._baselines[name]
                self._cusums[name].update(float(obs_arr[i]), mu)
```

- [ ] **Step 2: Update predictions.py to call replay_history before predict**

In `app/ml-microservice/src/predictions.py`, in the `predict_all` method, replace the `model_e_out` block:

```python
            # --- Model E: Anomaly Ensemble ---
            model_e_out: Optional[Dict] = None
            anomaly_model = get_anomaly_ensemble()
            feature_names = ["air_temperature", "process_temperature",
                             "rotational_speed", "torque", "tool_wear"]
            if anomaly_model is not None and anomaly_model._fitted:
                # Warm-start CUSUM with history (all entries except latest)
                if len(logs) > 1:
                    history_arrays = [
                        np.array([
                            float(lg.get("air_temperature", 298)),
                            float(lg.get("process_temperature", 308)),
                            float(lg.get("rotational_speed", 1500)),
                            float(lg.get("torque", 40)),
                            float(lg.get("tool_wear", 0)),
                        ])
                        for lg in logs[:-1]  # exclude latest — that's what predict() scores
                    ]
                    anomaly_model.replay_history(history_arrays, feature_names)
                model_e_out = anomaly_model.predict(np.array(features_5), feature_names)
```

- [ ] **Step 3: Verify**

```bash
cd app/ml-microservice
python -c "import ast; ast.parse(open('src/anomaly_cusum.py').read()); print('cusum OK')"
python -c "import ast; ast.parse(open('src/predictions.py').read()); print('predictions OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/ml-microservice/src/anomaly_cusum.py app/ml-microservice/src/predictions.py
git commit -m "feat(cusum): replay telemetry history to warm-start CUSUM state before scoring"
```

---

## Task 9: Update Mahalanobis — Machine-Specific Baseline

**Files:**
- Modify: `app/ml-microservice/src/health_index.py`

- [ ] **Step 1: Add fit_and_score_history method to MahalanobisHealthIndex**

After the existing `score()` method in `MahalanobisHealthIndex`, add:

```python
    def fit_and_score_history(
        self,
        history: np.ndarray,
    ) -> Dict:
        """
        Fit a machine-specific GMM baseline on all historical readings
        except the last, then score the last entry against that baseline.

        Falls back to the global model's score if history is too small (<10).

        Args:
            history: np.ndarray of shape (n_entries, 5), oldest first.
                     Columns: [air_temperature, process_temperature,
                               rotational_speed, torque, tool_wear]

        Returns:
            Same dict as score(): health_index, mahal_distance, is_anomaly,
            percentile, n_components_used.
            Extra key: score_source ("machine_baseline" | "global_baseline")
        """
        if len(history) < 10:
            # Not enough history — fall back to global fitted model
            if self._fitted:
                result = self.score(history[-1])
                result["score_source"] = "global_baseline"
                return result
            return {
                "health_index": 100.0,
                "mahal_distance": 0.0,
                "is_anomaly": False,
                "percentile": 100.0,
                "n_components_used": 0,
                "score_source": "no_model",
            }

        X = np.asarray(history, dtype=float)
        latest = X[-1]
        train  = X[:-1]  # all but latest are the baseline

        # Fit a temporary machine-specific model
        tmp = MahalanobisHealthIndex(
            n_components=min(self.n_components, max(1, len(train) // 5)),
            reg_covar=self.reg_covar,
        )
        try:
            tmp.fit(train)
            result = tmp.score(latest)
            result["score_source"] = "machine_baseline"
            return result
        except Exception as e:
            logger.warning(f"Machine-specific Mahal fit failed: {e} — using global")
            if self._fitted:
                result = self.score(latest)
                result["score_source"] = "global_baseline"
                return result
            return {
                "health_index": 100.0,
                "mahal_distance": 0.0,
                "is_anomaly": False,
                "percentile": 100.0,
                "n_components_used": 0,
                "score_source": "fallback",
            }
```

- [ ] **Step 2: Update predictions.py to use fit_and_score_history when logs available**

In `predictions.py`, replace the `model_c_out` block:

```python
            # --- Model C: Mahalanobis Health Index ---
            model_c_out: Optional[Dict] = None
            hi_model = get_health_index_model()
            if hi_model is not None:
                if len(logs) >= 2:
                    history_matrix = np.array([
                        [
                            float(lg.get("air_temperature", 298)),
                            float(lg.get("process_temperature", 308)),
                            float(lg.get("rotational_speed", 1500)),
                            float(lg.get("torque", 40)),
                            float(lg.get("tool_wear", 0)),
                        ]
                        for lg in logs
                    ])
                    model_c_out = hi_model.fit_and_score_history(history_matrix)
                elif hi_model._fitted:
                    model_c_out = hi_model.score(np.array(features_5))
```

- [ ] **Step 3: Verify**

```bash
cd app/ml-microservice
python -c "import ast; ast.parse(open('src/health_index.py').read()); print('health_index OK')"
python -c "import ast; ast.parse(open('src/predictions.py').read()); print('predictions OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/ml-microservice/src/health_index.py app/ml-microservice/src/predictions.py
git commit -m "feat(mahalanobis): add fit_and_score_history for machine-specific health baseline"
```

---

## Task 10: Update Survival Model — Wire fit_from_logs into Prediction Path

**Files:**
- Modify: `app/ml-microservice/src/predictions.py`

- [ ] **Step 1: Update model_b_out block to use telemetry logs**

In `predictions.py`, replace the `model_b_out` block:

```python
            # --- Model B: Survival Analysis ---
            model_b_out: Optional[Dict] = None
            surv_model = get_survival_model()
            if surv_model is not None:
                if len(logs) >= 10:
                    # Enough history to fit a machine-specific survival model
                    try:
                        surv_model.fit_from_logs(logs)
                    except Exception as _e:
                        logger.warning(f"Survival fit_from_logs failed: {_e}")
                if surv_model._fitted:
                    model_b_out = surv_model.predict(snapshot)
```

- [ ] **Step 2: Verify**

```bash
cd app/ml-microservice
python -c "import ast; ast.parse(open('src/predictions.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/ml-microservice/src/predictions.py
git commit -m "feat(survival): fit Cox PH from telemetry history when >=10 data points available"
```

---

## Task 11: Update Kalman Filter — Smooth Over Full History

**Files:**
- Modify: `app/ml-microservice/src/kalman_estimator.py`
- Modify: `app/ml-microservice/src/predictions.py`

- [ ] **Step 1: Add smooth_from_scores method to KalmanStateEstimator**

Read the end of `kalman_estimator.py` to find the last method, then add after it:

```python
    def smooth_from_scores(
        self,
        score_history: List[Dict],
        initial_hi: float = 80.0,
        initial_rul: float = 30.0,
    ) -> Dict:
        """
        Reset filter and run through a sequence of historical health observations.

        Each entry in score_history is an obs dict with zero or more of:
            rule_score, ml_score, survival_hi, mahal_hi

        Returns the smoothed state after the final observation — same format
        as update().

        Args:
            score_history: List of obs dicts, oldest first.
            initial_hi: Initial health index assumption (default 80).
            initial_rul: Initial RUL assumption in days (default 30).
        """
        self.reset(initial_hi=initial_hi, initial_rul=initial_rul)
        result = {
            "hi_kalman":              initial_hi,
            "rul_kalman":             initial_rul,
            "degradation_rate":       0.5,
            "sensor_fault_flag":      False,
            "innovation_norm":        0.0,
            "state_covariance_trace": float(np.trace(self.P)),
        }
        for obs in score_history:
            result = self.update(obs)
        return result
```

- [ ] **Step 2: Update predictions.py Kalman block to use history**

In `predictions.py`, replace the `kalman_state` block:

```python
            # --- Kalman state update ---
            DEFAULT_HI = 75.0
            rule_score = max(0.0, 100.0 - failure_prob)

            if len(logs) >= 2:
                # Build simplified observation sequence from history
                # Each historical entry contributes rule_score only (P1 inversion)
                # Full model scores are too expensive to recompute per step
                kalman_history = []
                for lg in logs[:-1]:
                    air_h = float(lg.get("air_temperature", 298))
                    # Cheap rule-based estimate: higher temp → lower health
                    hi_est = max(0.0, min(100.0, 100.0 - (air_h - 298) * 2.0))
                    kalman_history.append({"rule_score": hi_est})

                # Final observation uses all available model scores
                final_obs = {
                    "rule_score":  rule_score,
                    "ml_score":    rule_score,
                    "survival_hi": model_b_out["health_index"] if model_b_out and not np.isnan(model_b_out.get("health_index", np.nan)) else DEFAULT_HI,
                    "mahal_hi":    model_c_out["health_index"] if model_c_out and not np.isnan(model_c_out.get("health_index", np.nan)) else DEFAULT_HI,
                }
                kalman_history.append(final_obs)
                kalman_state = get_kalman_estimator().smooth_from_scores(kalman_history)
            else:
                kalman_obs = {
                    "rule_score":  rule_score,
                    "ml_score":    rule_score,
                    "survival_hi": model_b_out["health_index"] if model_b_out and not np.isnan(model_b_out.get("health_index", np.nan)) else DEFAULT_HI,
                    "mahal_hi":    model_c_out["health_index"] if model_c_out and not np.isnan(model_c_out.get("health_index", np.nan)) else DEFAULT_HI,
                }
                kalman_state = get_kalman_estimator().update(kalman_obs)
```

- [ ] **Step 3: Verify**

```bash
cd app/ml-microservice
python -c "import ast; ast.parse(open('src/kalman_estimator.py').read()); print('kalman OK')"
python -c "import ast; ast.parse(open('src/predictions.py').read()); print('predictions OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/ml-microservice/src/kalman_estimator.py app/ml-microservice/src/predictions.py
git commit -m "feat(kalman): smooth over full telemetry history to eliminate single-reading score swings"
```

---

## Task 12: Wire PINN Time Series from Telemetry Logs

**Files:**
- Modify: `app/ml-microservice/src/predictions.py`

- [ ] **Step 1: Update PINN time_series construction to use telemetry _logs**

In `predictions.py`, the existing line:

```python
time_series = FeatureStore.build_time_series_from_logs(machine_id, logs) if logs else []
```

Already works correctly once `_logs` is populated with `machine_telemetry_logs` data (which Task 6 sets up). The `build_time_series_from_logs` function expects the same keys we now provide: `air_temperature`, `process_temperature`, `rotational_speed`, `torque`, `tool_wear`, `created_at`, `machine_id`.

Verify the key name match by checking `FeatureStore.build_time_series_from_logs`:

```bash
cd app/ml-microservice
python -c "
from src.feature_store import FeatureStore
test_log = [{
    'machine_id': 1,
    'air_temperature': 300.0,
    'process_temperature': 310.0,
    'rotational_speed': 1500,
    'torque': 40.0,
    'tool_wear': 0.0,
    'created_at': '2026-01-01T00:00:00',
    'risk_level': 'LOW',
}, {
    'machine_id': 1,
    'air_temperature': 305.0,
    'process_temperature': 315.0,
    'rotational_speed': 1510,
    'torque': 42.0,
    'tool_wear': 10.0,
    'created_at': '2026-02-01T00:00:00',
    'risk_level': 'LOW',
}, {
    'machine_id': 1,
    'air_temperature': 312.0,
    'process_temperature': 322.0,
    'rotational_speed': 1520,
    'torque': 45.0,
    'tool_wear': 20.0,
    'created_at': '2026-03-01T00:00:00',
    'risk_level': 'LOW',
}]
ts = FeatureStore.build_time_series_from_logs(1, test_log)
print('time_series length:', len(ts))
print('first snapshot keys:', list(ts[0].keys()) if ts else 'empty')
"
```

Expected: `time_series length: 3` and snapshot keys include `air_temperature`, `process_temperature`, etc.

- [ ] **Step 2: If PINN requires minimum 3 entries, add guard comment**

In `predictions.py`, the existing guard `if _PINN_AVAILABLE and len(time_series) >= 3:` already handles this. No code change needed — just confirm it is still there after Task 8 and 9 edits.

- [ ] **Step 3: Commit**

```bash
git add app/ml-microservice/src/predictions.py
git commit -m "feat(pinn): confirm telemetry history flows correctly into PINN time-series pathway"
```

---

## Task 13: End-to-End Smoke Test

- [ ] **Step 1: Start backend and verify /unified-health returns telemetry data points**

```bash
cd app/backend
uvicorn start:app --reload --port 8000 &
sleep 3
curl -s http://localhost:8000/api/v1/ml/machines/1/unified-health | python -m json.tool | grep -E "telemetry_data_points|health_score|risk_level|degradation"
```

Expected output includes `"telemetry_data_points"` key and `"health_score"` is a number (not null).

- [ ] **Step 2: Complete a work order with telemetry and re-check**

```bash
# Complete a work order via API (adjust order_id as needed)
curl -s -X PATCH http://localhost:8000/api/v1/technicien/work-orders/1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "act_description": "test",
    "telemetry_temperature": 302.5,
    "telemetry_vibration": 311.0,
    "telemetry_rpm": 1495,
    "telemetry_torque": 41.2,
    "telemetry_power": 15.0
  }'

# Check telemetry was stored with new column names
cd app/backend
python -c "
import asyncio
from core.database import async_session
from models.machine_telemetry import MachineTelemetry
from sqlalchemy import select

async def check():
    async with async_session() as db:
        r = await db.execute(select(MachineTelemetry).order_by(MachineTelemetry.id.desc()).limit(1))
        t = r.scalar_one_or_none()
        if t:
            print('air_temperature:', t.air_temperature)
            print('process_temperature:', t.process_temperature)
            print('rotational_speed:', t.rotational_speed)
            print('tool_wear:', t.tool_wear)
        else:
            print('no telemetry found')

asyncio.run(check())
"
```

Expected: all 4 fields print their values (not AttributeError).

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test(smoke): verify end-to-end telemetry history flow through ML pipeline"
```
