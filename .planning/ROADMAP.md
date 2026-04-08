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

### Phase 05: ML Model Training & Optimization (Complete ✅)

**Goal:** Retrain all 6 ML models (P1-P6) with optimized hyperparameters, feature engineering, and cross-validation. Update retraining service.

**Requirements:** [ML-TRAIN-01, ML-TRAIN-02, ML-TRAIN-03]

**Plans:** 1 plan in 1 wave (Complete ✅)

**Plan list:**
- [x] 05-01-PLAN.md — Retrain all 6 models with optimized hyperparameters + update retraining service

---

### Phase 06: ML Fleet Dashboard (Complete ✅)

**Goal:** Build a React frontend dashboard that visualizes all 6 ML model predictions (P1-P6) for the entire machine fleet, with fleet overview, machine detail panels, trend charts, SHAP explanations, and anomaly alerts.

**Requirements:** [ML-DASH-01, ML-DASH-02, ML-DASH-03]

**Plans:** 1 plan in 1 wave (Complete ✅)

**Plan list:**
- [x] 06-01-PLAN.md — Build ML Fleet Dashboard with fleet overview, machine detail, charts, SHAP, and manual verification

---

### Phase 07: ML Pipeline End-to-End: Model Training to Frontend Integration

**Goal:** Fix the full ML pipeline chain: consistent backend predictions across all endpoints, telemetry validation, accurate frontend display of all ML values, telemetry update UX, and a smart retraining workflow with admin feedback.

**Requirements:** [ML-PIPE-01, ML-PIPE-02, ML-PIPE-03, ML-PIPE-04, ML-PIPE-05, ML-PIPE-06, ML-PIPE-07, ML-PIPE-08, ML-PIPE-09, ML-PIPE-10, ML-PIPE-11]

**Depends on:** Phase 6

**Plans:** 4 plans in 2 waves

Plans:
- [ ] 07-01-PLAN.md — Backend: telemetry null guard, failure_types in response, N+1 batch-fetch fleet endpoints, pending_records in retrain stats
- [ ] 07-02-PLAN.md — Frontend types: fix MLPrediction and FleetMachineCard (failure_types, no_telemetry, is_new_machine, UNKNOWN risk)
- [ ] 07-03-PLAN.md — MachineDetailPanel: remove fake history, fix failure_types rendering, add telemetry edit form
- [ ] 07-04-PLAN.md — FleetOverview grey card, is_new_machine badge, useMLFleetData avg fix, MLDashboard inline retrain banner

---

*Generated: 2026-04-03*
*Updated: 2026-04-08*
