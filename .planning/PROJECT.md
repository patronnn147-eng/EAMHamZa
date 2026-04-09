# Backend Optimization

## What This Is

FastAPI + SQLAlchemy backend for EAM (Enterprise Asset Management) system. Optimizing for performance: fixing N+1 queries, ML model singleton, in-memory cache, and database indexes.

## Core Value

Deliver a fast, responsive backend API by eliminating N+1 queries, optimizing ML model loading, caching predictions, and ensuring proper database indexing.

## Requirements

### Active

- [x] OPT-01: Fix N+1 queries using SQLAlchemy eager loading (selectinload)
- [x] OPT-02: Add database indexes on frequently filtered FK columns
- [x] OPT-03: Verify performance improvements
- [x] OPT-04: ML model singleton - load .pkl once at startup
- [ ] OPT-05: In-memory TTL cache for ML predictions (5 minutes)

### Out of Scope

- [Refactoring services architecture] — keep existing structure
- [Adding new features] — only optimization work
- [External caching services] — Redis not allowed, pure in-memory only

## Context

- FastAPI backend with SQLAlchemy ORM
- PostgreSQL database running in Docker
- ML model at app/backend/modules/ml/basic_machine_model.pkl
- Existing services: ordres_travail, ordres_intervention, plannings, planning_utilisateurs
- N+1 patterns found in: ml/router.py, maintenance_scheduler.py, and service layers

## Constraints

- **Docker**: All operations must use docker containers
- **Python**: 3.11 runs in Docker container, local is 3.13
- **No breaking changes**: Must not change API contracts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use selectinload for eager loading | Most efficient for related collections | ✓ Good |
| Index FK + filtered columns | Supports common query patterns | ✓ Good |
| Docker-based workflow | Ensures consistent environment | ✓ Good |
| ML model singleton | Load .pkl once at startup for performance | ✓ Good |
| In-memory TTL cache | Cache predictions for 5 minutes, no Redis | ✓ Good |

---

*Last updated: 2026-04-03*