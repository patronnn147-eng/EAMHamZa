# Roadmap: Backend Optimization

## Project: Backend Optimization

**Goal:** Optimize FastAPI + SQLAlchemy backend performance by fixing N+1 queries, ML model singleton, in-memory cache, and adding database indexes

## Milestones

### Phase 01: Backend Optimization (Complete ✅)

**Goal:** Fix N+1 queries using eager loading and add performance indexes to PostgreSQL

**Requirements:** [OPT-01, OPT-02, OPT-03]

**Plans:** 3 plans in 2 waves (Complete ✅)

**Plan list:**
- [x] 01-01-PLAN.md — Apply eager loading to service layer
- [x] 01-02-PLAN.md — Create and apply database index migrations
- [x] 01-03-PLAN.md — Fix N+1 in ML router and maintenance scheduler

---

### Phase 02: ML Model Singleton (Complete ✅)

**Goal:** Load ML model .pkl file once at startup instead of on every request

**Requirements:** [OPT-04]

**Plans:** 1 plan in 1 wave (Complete ✅)

**Plan list:**
- [x] 02-01-PLAN.md — Verify singleton and add model_unavailable fallback

---

### Phase 03: In-Memory TTL Cache (Complete ✅)

**Goal:** Add lightweight in-memory TTL cache for ML predictions (5 minutes)

**Requirements:** [OPT-05]

**Plans:** 1 plan in 1 wave (Complete ✅)

**Plan list:**
- [x] 03-01-PLAN.md — Add TTL cache for ML predictions

---

### Phase 04: Connection Pooling (Complete ✅)

**Goal:** Configure SQLAlchemy async engine connection pooling for non-Lambda environments and NullPool for Lambda, ensuring stability under concurrent load.

**Requirements:** [DB-POOL-01]

**Plans:** 1 plan in 1 wave (Complete ✅)

**Plan list:**
- [x] 04-01-PLAN.md — Implement connection pooling and tests

---

*Generated: 2026-04-03*
*Updated: 2026-04-03*