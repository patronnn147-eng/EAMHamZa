# Phase 5: Inventory Management - Plan

**Project:** EAMSagemCom
**Phase:** 05
**Status:** Ready to Execute

---

## Implementation Tasks

### Task 1: Database Models

Create 4 new SQLAlchemy models:

| Model | Purpose |
|:------|:--------|
| `Piece` | Spare part master data |
| `PieceMachine` | Link parts to machines (M:N) |
| `Stock` | Current quantity per piece |
| `MouvementStock` | Stock movements history |

**Files to create:**
- `app/backend/models/pieces.py` - Piece model
- `app/backend/models/piece_machine.py` - Association table
- `app/backend/models/stock.py` - Stock level model
- `app/backend/models/mouvement_stock.py` - Movement model

---

### Task 2: Pydantic Schemas

Create request/response schemas:

- `app/backend/schemas/piece.py` - PieceCreate, PieceUpdate, PieceResponse
- `app/backend/schemas/stock.py` - StockCreate, StockResponse, MouvementStockCreate

---

### Task 3: API Endpoints

Create inventory router:

- `app/backend/modules/inventory/pieces.py` - CRUD for pieces
- `app/backend/modules/inventory/stock.py` - Stock operations
- `app/backend/modules/inventory/rapprovis.py` - Reorder alerts

**Endpoints:**

```
GET    /api/inventory/pieces          - List all parts
POST   /api/inventory/pieces         - Create part
GET    /api/inventory/pieces/{id}    - Get part details
PUT    /api/inventory/pieces/{id}    - Update part
DELETE /api/inventory/pieces/{id}    - Delete part

GET    /api/inventory/pieces/{id}/machines - Get compatible machines
POST   /api/inventory/pieces/{id}/machines - Link to machine

GET    /api/inventory/stock          - List stock levels
POST   /api/inventory/stock          - Add stock
POST   /api/inventory/stock/consume  - Consume for intervention
GET    /api/inventory/stock/alertes   - Low stock alerts
```

---

### Task 4: Link to Interventions

Modify existing intervention model to optionally link to consumed pieces.

- Update `ordres_intervention.py` to add `pieces_utilisees` relationship
- Add API to consume stock when completing intervention

---

### Task 5: Frontend Pages

Create React components:

| Component | Purpose |
|:----------|:--------|
| `Inventory.tsx` | Main inventory page |
| `PieceDetails.tsx` | Part detail/edit form |
| `StockManagement.tsx` | Stock levels view |
| `AlertesStock.tsx` | Low stock alerts widget |

Add navigation entry in sidebar.

---

### Task 6: RBAC

Configure permissions:

| Role | Inventory Access |
|:-----|:-----------------|
| ADMIN | Full CRUD |
| CHEFTECH | Full CRUD |
| CHETOP | View + Consume |
| TECHNICIEN | View only |

---

## Implementation Order

1. Create database models
2. Create Pydantic schemas
3. Create API router with endpoints
4. Add router to main.py
5. Create frontend components
6. Add navigation
7. Test end-to-end

---

## Notes

- Minimum stock threshold will be configurable per piece (default: 5)
- Stock movements track: date, quantity, type (in/out), reference
- Alerts generated on GET /api/inventory/stock/alertes

---

*Plan created: 2026-03-04*
