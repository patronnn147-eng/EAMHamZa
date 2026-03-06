# Phase 5: Inventory Management - Context

**Project:** EAMSagemCom
**Phase:** 05
**Goal:** Add Inventory/Spare Parts Management

---

## Background

The EAM system currently tracks machines, work orders, and interventions, but has **no inventory management**. Technicians record "pieces_remplacees" as free text in interventions, with no way to:

- Track what spare parts exist
- Know current stock levels
- Get alerts when parts are low

---

## Business Need

- **Stock Visibility:** Know what parts are available
- **Cost Control:** Track parts consumption
- **Prevent Downtime:** Ensure critical parts are in stock
- **Link to Maintenance:** Automatically consume parts when interventions are completed

---

## Current State

- **Existing:** Interventions have `pieces_remplacees` text field
- **Existing:** Machines are tracked with status
- **Missing:** Parts catalog, stock levels, reorder logic

---

## Requirements (from ROADMAP)

| ID | Requirement |
|:---|:------------|
| INV-01 | Spare Parts Catalog |
| INV-02 | Stock Management |
| INV-03 | Reorder Alerts |

---

## Technical Approach

### Database Models (new)

1. **Piece (SparePart)** - Master list of parts
2. **Stock** - Current inventory levels
3. **MouvementStock** - Stock movements (in/out)
4. **PieceMachine** - Many-to-many linking parts to machines

### API Endpoints (new)

- `GET/POST/PUT/DELETE /api/pieces` - CRUD for parts
- `GET/POST /api/stock` - Stock operations
- `GET /api/stock/alertes` - Low stock alerts
- `POST /api/stock/consume` - Consume for intervention

### Frontend (new)

- Inventory page with parts list
- Stock management view
- Alerts dashboard widget
- Link parts to intervention form

---

## Constraints

- Use existing database (PostgreSQL)
- Follow existing code patterns (SQLAlchemy, FastAPI)
- Reuse existing auth/RBAC
- Integrate with existing interventions

---

## Success Criteria

1. Full CRUD for spare parts
2. Stock levels visible and trackable
3. Low stock triggers alerts
4. Parts can be linked to machines
5. Interventions can consume parts

---

*Context created: 2026-03-04*
