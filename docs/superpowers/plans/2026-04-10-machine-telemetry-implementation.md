# Machine Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Machine Telemetry system to track real sensor data from technicians completing work orders, replacing mock data in IoT Dashboard.

**Architecture:** Create a new `machine_telemetry_logs` table linked to work orders via `work_order_id`. Technicians enter telemetry readings (temperature, vibration, rpm, torque, power) when completing work orders. IoT Dashboard fetches real data from this table instead of generating random values.

**Tech Stack:** SQLAlchemy (async), Pydantic v2, FastAPI, React (frontend), PostgreSQL

---

## Task 1: Create MachineTelemetry Database Model

**Files:**
- Create: `app/backend/models/machine_telemetry.py`
- Modify: `app/backend/models/__init__.py` (add export)

- [ ] **Step 1: Create the MachineTelemetry model file**

```python
# app/backend/models/machine_telemetry.py
from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class MachineTelemetry(Base):
    __tablename__ = "machine_telemetry_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id = Column(Integer, nullable=False, index=True)
    work_order_id = Column(Integer, nullable=True, index=True)
    technician_id = Column(Integer, nullable=False)
    
    # Sensor readings
    temperature = Column(Float(), nullable=False)  # °C
    vibration = Column(Float(), nullable=False)     # mm/s
    rpm = Column(Integer(), nullable=False)         # rotational speed
    torque = Column(Float(), nullable=False)        # Nm
    power = Column(Float(), nullable=False)         # kW
    
    # Metadata
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 2: Add export to models/__init__.py**

```python
# Add to app/backend/models/__init__.py
from models.machine_telemetry import MachineTelemetry
__all__ = ["MachineTelemetry", ...existing_exports...]
```

- [ ] **Step 3: Run database migration to create table**

Run: `cd app/backend && python -c "from models import MachineTelemetry; print('Model imported successfully')"`

- [ ] **Step 4: Commit**

```bash
git add app/backend/models/machine_telemetry.py app/backend/models/__init__.py
git commit -m "feat(telemetry): add MachineTelemetry database model"
```

---

## Task 2: Add Pydantic Schemas for Telemetry Data

**Files:**
- Create: `app/backend/modules/technicien/schemas_telemetry.py`
- Modify: `app/backend/modules/technicien/schemas.py` (add imports)

- [ ] **Step 1: Create telemetry schemas file**

```python
# app/backend/modules/technicien/schemas_telemetry.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MachineTelemetryBase(BaseModel):
    """Base telemetry fields shared across request/response"""
    temperature: float = Field(..., description="Temperature in Celsius", ge=-50, le=200)
    vibration: float = Field(..., description="Vibration in mm/s", ge=0, le=100)
    rpm: int = Field(..., description="Rotational speed in RPM", ge=0, le=10000)
    torque: float = Field(..., description="Torque in Nm", ge=0, le=1000)
    power: float = Field(..., description="Power in kW", ge=0, le=500)
    notes: Optional[str] = None


class MachineTelemetryCreate(MachineTelemetryBase):
    """Schema for creating telemetry entry via work order completion"""
    machine_id: int
    work_order_id: Optional[int] = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class MachineTelemetryResponse(MachineTelemetryBase):
    """Schema for telemetry response"""
    id: int
    machine_id: int
    work_order_id: Optional[int] = None
    technician_id: int
    recorded_at: datetime
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MachineTelemetryLatest(BaseModel):
    """Schema for latest telemetry per machine"""
    machine_id: int
    machine_nom: Optional[str] = None
    temperature: float
    vibration: float
    rpm: int
    torque: float
    power: float
    recorded_at: datetime
    recorded_by: Optional[str] = None
    work_order_id: Optional[int] = None


class MachineTelemetryListResponse(BaseModel):
    """Paginated list response for machine telemetry"""
    items: List[MachineTelemetryResponse]
    total: int
    page: int
    size: int
```

- [ ] **Step 2: Add import to existing schemas.py**

Add at the top of `app/backend/modules/technicien/schemas.py`:
```python
from schemas_telemetry import (
    MachineTelemetryCreate,
    MachineTelemetryResponse,
    MachineTelemetryLatest,
)
```

- [ ] **Step 3: Commit**

```bash
git add app/backend/modules/technicien/schemas_telemetry.py app/backend/modules/technicien/schemas.py
git commit -m "feat(telemetry): add Pydantic schemas for telemetry data"
```

---

## Task 3: Extend Work Order Completion to Save Telemetry

**Files:**
- Modify: `app/backend/modules/technicien/technicien_work_orders.py:172-244`

- [ ] **Step 1: Update WorkOrderCompletePayload to include telemetry fields**

In `technicien_work_orders.py`, add telemetry fields to `WorkOrderCompletePayload`:

```python
class WorkOrderCompletePayload(BaseModel):
    rapport: str
    
    # Enhanced Report fields
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    # ... existing fields ...
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None
    
    # NEW: Machine Telemetry fields (all optional, can be provided separately)
    telemetry_temperature: Optional[float] = Field(None, ge=-50, le=200)
    telemetry_vibration: Optional[float] = Field(None, ge=0, le=100)
    telemetry_rpm: Optional[int] = Field(None, ge=0, le=10000)
    telemetry_torque: Optional[float] = Field(None, ge=0, le=1000)
    telemetry_power: Optional[float] = Field(None, ge=0, le=500)
    telemetry_notes: Optional[str] = None
```

- [ ] **Step 2: Add import for MachineTelemetry model**

Add at top of file:
```python
from models.machine_telemetry import MachineTelemetry
```

- [ ] **Step 3: Update complete_work_order function to save telemetry**

In the `complete_work_order` function, after `await db.commit()`, add telemetry save logic:

```python
# After intervention update, save telemetry if provided
if any([
    payload.telemetry_temperature,
    payload.telemetry_vibration,
    payload.telemetry_rpm,
    payload.telemetry_torque,
    payload.telemetry_power,
]):
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
    db.add(telemetry)
    await db.commit()
```

- [ ] **Step 4: Test the endpoint**

Run: `curl -X PATCH http://localhost:8000/api/v1/technicien/work-orders/1/complete -H "Authorization: Bearer $TOKEN" -d '{"rapport": "Fixed", "telemetry_temperature": 65.5, "telemetry_vibration": 3.2, "telemetry_rpm": 3500, "telemetry_torque": 45.0, "telemetry_power": 12.5}'`

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/technicien/technicien_work_orders.py
git commit -m "feat(telemetry): save telemetry data when completing work order"
```

---

## Task 4: Create GET Endpoint for Machine Telemetry

**Files:**
- Modify: `app/backend/modules/technicien/routes/machines.py` (or create new endpoint file)

- [ ] **Step 1: Check existing machines routes**

Read `app/backend/modules/technicien/routes/machines.py` to see existing endpoints.

- [ ] **Step 2: Add GET /machines/{id}/telemetry endpoint**

```python
# Add to app/backend/modules/technicien/routes/machines.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional

from core.database import get_db
from core.security import verify_technicien
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from schemas_telemetry import MachineTelemetryResponse, MachineTelemetryLatest
from schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("/machines/{machine_id}/telemetry", response_model=PaginatedResponse[MachineTelemetryResponse])
async def get_machine_telemetry(
    machine_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Get telemetry logs for a specific machine"""
    # Verify machine exists
    machine_result = await db.execute(select(Machines).where(Machines.id == machine_id))
    if not machine_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Count total
    count_result = await db.execute(
        select(func.count(MachineTelemetry.id)).where(MachineTelemetry.machine_id == machine_id)
    )
    total = count_result.scalar() or 0
    
    # Get telemetry records
    skip = (page - 1) * size
    query = select(MachineTelemetry)\
        .where(MachineTelemetry.machine_id == machine_id)\
        .order_by(desc(MachineTelemetry.recorded_at))\
        .offset(skip).limit(size)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    items = [
        MachineTelemetryResponse(
            id=r.id,
            machine_id=r.machine_id,
            work_order_id=r.work_order_id,
            technician_id=r.technician_id,
            temperature=r.temperature,
            vibration=r.vibration,
            rpm=r.rpm,
            torque=r.torque,
            power=r.power,
            recorded_at=r.recorded_at,
            notes=r.notes,
            created_at=r.created_at,
        ) for r in records
    ]
    
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get("/machines/{machine_id}/telemetry/latest", response_model=MachineTelemetryLatest)
async def get_machine_latest_telemetry(
    machine_id: int,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Get latest telemetry reading for a machine"""
    # Verify machine exists
    machine_result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = machine_result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get latest telemetry
    query = select(MachineTelemetry)\
        .where(MachineTelemetry.machine_id == machine_id)\
        .order_by(desc(MachineTelemetry.recorded_at))\
        .limit(1)
    
    result = await db.execute(query)
    telemetry = result.scalar_one_or_none()
    
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry data found for this machine")
    
    return MachineTelemetryLatest(
        machine_id=machine_id,
        machine_nom=machine.nom,
        temperature=telemetry.temperature,
        vibration=telemetry.vibration,
        rpm=telemetry.rpm,
        torque=telemetry.torque,
        power=telemetry.power,
        recorded_at=telemetry.recorded_at,
        work_order_id=telemetry.work_order_id,
    )
```

- [ ] **Step 3: Add missing imports**

Add at top:
```python
from sqlalchemy import func, desc
```

- [ ] **Step 4: Register the new routes**

Ensure the router is included in the technician module's `__init__.py` or main router.

- [ ] **Step 5: Test the endpoint**

Run: `curl http://localhost:8000/api/v1/technicien/machines/1/telemetry/latest -H "Authorization: Bearer $TOKEN"`

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/technicien/routes/machines.py
git commit -m "feat(telemetry): add GET endpoints for machine telemetry"
```

---

## Task 5: Add Machine Metrics Form to Work Order Completion Screen

**Files:**
- Modify: `app/frontend/src/modules/technicien/WorkOrderDetail.tsx` (or completion modal)
- Create: `app/frontend/src/components/technicien/MachineMetricsForm.tsx`

- [ ] **Step 1: Create MachineMetricsForm component**

```tsx
// app/frontend/src/components/technicien/MachineMetricsForm.tsx
import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Thermometer, Activity, Gauge, Zap, FileText } from 'lucide-react';

interface MachineMetricsFormProps {
  formData: TelemetryFormData;
  onChange: (data: TelemetryFormData) => void;
}

interface TelemetryFormData {
  temperature?: number;
  vibration?: number;
  rpm?: number;
  torque?: number;
  power?: number;
  notes?: string;
}

export const MachineMetricsForm: React.FC<MachineMetricsFormProps> = ({ formData, onChange }) => {
  const handleChange = (field: keyof TelemetryFormData, value: string | number) => {
    onChange({ ...formData, [field]: value });
  };

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Machine Metrics (Optional)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="space-y-2">
            <Label htmlFor="temperature" className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              Temp (°C)
            </Label>
            <Input
              id="temperature"
              type="number"
              step="0.1"
              min="-50"
              max="200"
              placeholder="65.0"
              value={formData.temperature ?? ''}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="vibration" className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Vib (mm/s)
            </Label>
            <Input
              id="vibration"
              type="number"
              step="0.1"
              min="0"
              max="100"
              placeholder="3.5"
              value={formData.vibration ?? ''}
              onChange={(e) => handleChange('vibration', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="rpm" className="flex items-center gap-1">
              <Gauge className="h-3 w-3" />
              RPM
            </Label>
            <Input
              id="rpm"
              type="number"
              step="1"
              min="0"
              max="10000"
              placeholder="3500"
              value={formData.rpm ?? ''}
              onChange={(e) => handleChange('rpm', parseInt(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="torque" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Torque (Nm)
            </Label>
            <Input
              id="torque"
              type="number"
              step="0.1"
              min="0"
              max="1000"
              placeholder="45.0"
              value={formData.torque ?? ''}
              onChange={(e) => handleChange('torque', parseFloat(e.target.value) || undefined)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="power" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Power (kW)
            </Label>
            <Input
              id="power"
              type="number"
              step="0.1"
              min="0"
              max="500"
              placeholder="12.5"
              value={formData.power ?? ''}
              onChange={(e) => handleChange('power', parseFloat(e.target.value) || undefined)}
            />
          </div>
        </div>
        
        <div className="mt-4 space-y-2">
          <Label htmlFor="notes" className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            Notes (Optional)
          </Label>
          <Textarea
            id="notes"
            placeholder="Any observations about machine state..."
            value={formData.notes ?? ''}
            onChange={(e) => handleChange('notes', e.target.value)}
            rows={2}
          />
        </div>
      </CardContent>
    </Card>
  );
};

export type { TelemetryFormData };
```

- [ ] **Step 2: Find and modify work order completion component**

Locate the technician work order completion form (likely in `app/frontend/src/modules/technicien/`). Add the MachineMetricsForm to the completion form.

```tsx
// In WorkOrderCompletionForm.tsx - add state and import
import { MachineMetricsForm, TelemetryFormData } from '@/components/technicien/MachineMetricsForm';

// Add state
const [telemetryData, setTelemetryData] = useState<TelemetryFormData>({});

// Add form field in submit payload
const submitPayload = {
  rapport: formData.rapport,
  // ... existing fields ...
  telemetry_temperature: telemetryData.temperature,
  telemetry_vibration: telemetryData.vibration,
  telemetry_rpm: telemetryData.rpm,
  telemetry_torque: telemetryData.torque,
  telemetry_power: telemetryData.power,
  telemetry_notes: telemetryData.notes,
};

// Add form component in JSX - after existing form fields
<MachineMetricsForm formData={telemetryData} onChange={setTelemetryData} />
```

- [ ] **Step 3: Test the UI**

1. Run the frontend: `npm run dev`
2. Navigate to technician work order completion
3. Verify the Machine Metrics form appears
4. Fill in values and submit
5. Check API response includes telemetry data

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/technicien/MachineMetricsForm.tsx app/frontend/src/modules/technicien/
git commit -m "feat(telemetry): add Machine Metrics form to work order completion"
```

---

## Task 6: Update IoT Dashboard to Use Real Telemetry Data

**Files:**
- Modify: `app/frontend/src/modules/shared/IoTDashboard.tsx`

- [ ] **Step 1: Update fetchMachines to get real telemetry data**

Replace the `fetchMachines` function in IoTDashboard.tsx:

```tsx
const fetchMachines = async () => {
  setLoading(true);
  try {
    // Get machines
    const res = await fetch(`${API}/api/v1/machines?limit=50`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    
    if (res.ok) {
      const data = await res.json();
      const machinesData = data.items || data || [];
      
      // For each machine, fetch latest telemetry
      const machinesWithTelemetry = await Promise.all(
        machinesData.map(async (m: any) => {
          let telemetry = null;
          try {
            const telRes = await fetch(
              `${API}/api/v1/technicien/machines/${m.id}/telemetry/latest`,
              { headers: { Authorization: `Bearer ${getToken()}` } }
            );
            if (telRes.ok) {
              telemetry = await telRes.json();
            }
          } catch (e) {
            // No telemetry for this machine
          }
          
          return {
            id: m.id,
            name: m.nom || `Machine ${m.id}`,
            zone: m.zone || 'Zone A',
            status: m.statut || 'OPERATIONAL',
            temperature: telemetry?.temperature ?? null,
            vibration: telemetry?.vibration ?? null,
            rpm: telemetry?.rpm ?? null,
            torque: telemetry?.torque ?? null,
            power: telemetry?.power ?? null,
            online: telemetry !== null,
            lastUpdate: telemetry?.recorded_at || null,
            hasTelemetry: telemetry !== null,
          };
        })
      );
      
      setMachines(machinesWithTelemetry);
    } else {
      setMachines(generateMockMachines());
    }
  } catch (err) {
    console.error('Failed to load machines', err);
    setMachines(generateMockMachines());
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 2: Update MachineTelemetry interface**

Replace the interface to handle null values:

```tsx
interface MachineTelemetry {
  id: number;
  name: string;
  zone: string;
  status: string;
  temperature: number | null;
  vibration: number | null;
  rpm: number | null;
  torque: number | null;
  power: number | null;
  online: boolean;
  lastUpdate: string | null;
  hasTelemetry: boolean;
}
```

- [ ] **Step 3: Update getHealthStatus to handle missing data**

```tsx
const getHealthStatus = (machine: MachineTelemetry) => {
  // If no telemetry data, show as unknown/warning
  if (!machine.hasTelemetry || machine.temperature === null) {
    return 'unknown';
  }
  if (machine.temperature > 95 || machine.vibration > 10) return 'critical';
  if (machine.temperature > 80 || machine.vibration > 7) return 'warning';
  return 'normal';
};
```

- [ ] **Step 4: Add health color for unknown state**

Add to `getHealthColor`:

```tsx
const getHealthColor = (status: string) => {
  switch (status) {
    case 'critical': return 'border-l-red-500';
    case 'warning': return 'border-l-yellow-500';
    case 'unknown': return 'border-l-gray-400';
    default: return 'border-l-green-500';
  }
};
```

- [ ] **Step 5: Update card display to show "No Data" when telemetry missing**

In the card content display, add conditional rendering:

```tsx
{machine.hasTelemetry ? (
  <div className="grid grid-cols-2 gap-2 text-sm">
    <div className="flex items-center gap-2">
      <Thermometer className="h-3 w-3 text-muted-foreground" />
      <span>{machine.temperature?.toFixed(1)}°C</span>
    </div>
    {/* ... rest of metrics ... */}
  </div>
) : (
  <div className="text-sm text-muted-foreground italic">
    No telemetry data
  </div>
)}
```

- [ ] **Step 6: Test the updated dashboard**

1. Complete a work order with telemetry data
2. Navigate to IoT Dashboard
3. Verify the machine shows real data instead of random values
4. Verify machines without telemetry show "No telemetry data"

- [ ] **Step 7: Commit**

```bash
git add app/frontend/src/modules/shared/IoTDashboard.tsx
git commit -m "feat(telemetry): update IoT Dashboard to show real telemetry data"
```

---

## Verification Checklist

After completing all tasks:

- [ ] Database table `machine_telemetry_logs` exists with correct columns
- [ ] POST /api/v1/technicien/work-orders/{id}/complete accepts telemetry fields
- [ ] GET /api/v1/technicien/machines/{id}/telemetry returns paginated telemetry
- [ ] GET /api/v1/technicien/machines/{id}/telemetry/latest returns latest reading
- [ ] Technician frontend shows Machine Metrics form on work order completion
- [ ] IoT Dashboard fetches real telemetry data instead of generating random values
- [ ] Machines without telemetry show appropriate "No data" state

---

## Plan Complete

**Next Steps:**
- Test the full flow: complete a work order with telemetry → verify appears in IoT Dashboard
- Add validation: ensure telemetry values are within reasonable ranges
- Consider adding historical chart view for individual machine telemetry