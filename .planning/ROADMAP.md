### Phase 11: Planning Fix

**Goal:** Fix the Planning page UI/Backend bug where assigned technicians and selected machines are not displayed. Implement eager loading on backend, hydrate frontend forms, and add regression tests.

**Requirements:** [PF-01, PF-02, PF-03]

**Plans:** 3 plans in 3 waves (Incomplete ☐)

**Plan list:**
- [ ] 11-01-PLAN.md — Backend eager‑loading of assigned users and machines
- [ ] 11-02-PLAN.md — Frontend UI hydration for Planning Management
- [ ] 11-03-PLAN.md — Regression tests for backend and frontend fixes

### Phase 12: ChefTech Alert Response Workflow page

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 11
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 12 to break down)

### Phase 12.1: RAG Implementation — pgvector document ingestion, semantic retrieval, and chat context augmentation (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 12
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 12.1 to break down)

### Phase 13: Add hybrid search (BM25 + vector) phase — Phase 1 Postgres-native, Phase 2 Elasticsearch

**Goal:** Phase 13.1 — Add Postgres-native BM25-style keyword retrieval alongside the existing pgvector cosine path in `rag-service`. Fuse the two via Reciprocal Rank Fusion (k=60), feed the fused list to the existing cross-encoder reranker, and surface observability + a runtime toggle. Phase 13.2 (Elasticsearch) is deferred per CONTEXT.md.

**Requirements:** [HYB-01, HYB-02, HYB-03, HYB-04, HYB-05, HYB-06, HYB-07, HYB-08, HYB-09]

**Depends on:** Phase 12

**Plans:** 1/3 plans executed

**Plan list:**
- [ ] 13-01-migration-tsvector-gin-PLAN.md — Alembic migration adding 2 GENERATED tsvector cols (FR + EN) + 2 GIN indexes on `doc_chunks`
- [ ] 13-02-hybrid-module-and-retriever-PLAN.md — New `app/rag-service/hybrid.py` (RRF + keyword SQL + env toggle + stats) + retriever fan-out + `/cache-stats` + `/hybrid-info` + `HYBRID_ENABLED` env wiring
- [ ] 13-03-smoke-toggle-observability-PLAN.md — Smoke verification (exact-ID + NL queries), toggle-off A/B regression, fail-loud BM25, user checkpoint
