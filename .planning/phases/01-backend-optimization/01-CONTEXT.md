# Phase 01: Backend Optimization - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix N+1 query patterns in FastAPI/SQLAlchemy backend and add database indexes for performance optimization.
</domain>

<decisions>
## Implementation Decisions

### Approach
- Use SQLAlchemy `selectinload` for eager loading (not `joinedload` - better for collections)
- Docker-based workflow (backend in container, Python 3.11)
- No breaking changes to API contracts

### Services to Update
- `ordres_travail.py` - add selectinload for machine, utilisateur, interventions
- `ordres_intervention.py` - add selectinload for machine, technician, work_order
- `planning_utilisateurs.py` - add selectinload for utilisateur
- `planning_ordres_travail.py` - add selectinload for ordre_travail

### Database Indexes
- FK columns: machine_id, utilisateur_id, technician_id
- Filter columns: statut, created_at, lu (notification read status)

### Claude's Discretion
- Index naming convention: `idx_{table}_{column}` - standard approach
- Migration file organization - use Alembic standard structure
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- SQLAlchemy relationships already defined on child models (Ordres_travail, Ordres_intervention → Machines)
- Reverse relationships needed on parent (Machines → Ordres_travail, Ordres_intervention)

### Established Patterns
- Services use sync SQLAlchemy session
- Response schemas define what gets returned
- FastAPI dependency injection for database session

### Integration Points
- ML router endpoints (`/fleet/critical`, `/fleet/dashboard`)
- Maintenance scheduler task
- Service layer list endpoints
</code_context>

<specifics>
## Specific Ideas

- Add reverse relationships to Machines model for orders and interventions
- Apply eager loading in service layer before returning to routers
- Create Alembic migrations for indexes (not raw SQL - use Alembic best practices)

</specifics>

<deferred>
## Deferred Ideas

(None - stayed within optimization scope)

</deferred>

---

*Phase: 01-backend-optimization*
*Context gathered: 2026-04-03*