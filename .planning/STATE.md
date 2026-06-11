---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: active
stopped_at: "Completed 13-03-smoke-toggle-observability-PLAN.md"
last_updated: "2026-06-11"
progress:
  total_phases: 19
  completed_phases: 6
  total_plans: 37
  completed_plans: 20
---

# Project State

**Project:** Backend Optimization

**Last Updated:** 2026-06-06

## Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 01-backend-optimization | ✅ Complete | Verified: 9/9 truths passed |
| 02-ml-singleton | ✅ Complete | 40% performance improvement verified |
| 03-cache | ✅ Complete | 94% faster on cached calls |
| 04-connection-pooling | ✅ Complete | Connection pooling configured and tested |
| 05-ml-training | ✅ Complete | All 6 models retrained, 100% TestSprite tests passed |
| 06-ml-dashboard | ✅ Complete | Dashboard implemented, API fixed, manual verification passed |
| 13-add-hybrid-search-bm25-vector | ✅ Complete | 3/3 plans complete — Phase 13.1 Postgres-native hybrid search fully signed off |

## Session Notes

- Phase 01: N+1 queries fixed via selectinload, 9 database indexes applied
- Phase 02: ML model singleton verified - 40% faster on second call
- Phase 03: In-memory TTL cache verified - 94% faster on cached calls
- Phase 04: Connection pooling implemented, Lambda handling, tests passed
- Phase 05: All 6 ML models retrained with XGBoost + GridSearchCV + feature engineering
  - P1: XGBClassifier, ROC-AUC 0.9655, PR-AUC 0.8043
  - P2: MultiOutput XGB, HDF F1=1.0, PWF F1=0.93
  - P3: XGBRegressor, R²=0.5851, MAE=15.04
  - P4: IsolationForest, F1=0.3383
  - P5: XGBClassifier, F1-macro=0.7726
  - P6: XGBRegressor, R²=0.6535, MAE=1.72 days
  - Retraining service updated to support all 6 models
  - TestSprite: 4/4 tests passed (100%)
  - API fixes: health endpoints, fleet/critical format, None→0.0

## Accumulated Context

### Roadmap Evolution
- Phase 7 added: ML Pipeline End-to-End: Model Training to Frontend Integration
- Phase 12 added: ChefTech Alert Response Workflow page
- Phase 12.1 inserted after Phase 12: RAG Implementation — pgvector document ingestion, semantic retrieval, and chat context augmentation (URGENT)
- Phase 13 added: Add hybrid search (BM25 + vector) phase — Phase 1 Postgres-native, Phase 2 Elasticsearch

### Phase 13 Decisions (13-01 executed 2026-06-06)
- GENERATED ALWAYS STORED tsvector columns chosen over application-level UPDATE: backfill + future syncs are automatic, ingestor.py stays untouched.
- Non-CONCURRENT CREATE INDEX accepted (Alembic transaction wrapping) — ~1s blocking at current scale tolerable.
- `SET lock_timeout = '30s'` guard added to ALTER TABLE DDL so future runs fail loud rather than block writers.
- Per CONTEXT.md, two language configs (french + english) as separate tsvector columns + separate GIN indexes; query side will use `GREATEST(rank_fr, rank_en)`.

### Phase 13 Decisions (13-02 executed 2026-06-06)
- Vector branch SQL kept verbatim except additive `dc.id AS chunk_id` projection so `rrf_fuse()` can dedupe by stable PK.
- Retrieval cache key widened atomically to 5-tuple `(query, machine_id, top_k, threshold, hybrid_enabled)` so toggling does not return stale results.
- BM25 errors re-raised (fail-loud per CONTEXT.md); embedding failure in hybrid mode still lets keyword branch contribute; in vector-only mode preserves pre-13 `[]` return.
- `tests/` removed from rag-service `.dockerignore` so verify command `docker compose run --rm rag-service pytest tests/...` works as written (Rule 3 blocking-issue auto-fix).
- `pytest` + `pytest-asyncio` added to rag-service `requirements.txt` (image lacked them).
- 37 unit tests (25 RRF + 12 retriever toggle) all green inside the rag-service container.

### Phase 13 Decisions (13-03 completed 2026-06-11)
- Corpus sync prerequisite confirmed: sync_db_to_rag.py --tables ordres_travail ingested 130 WOs (0 failures) before smoke queries.
- Fail-loud DDL test substituted with unit test (auto-mode safety classifier blocked ALTER TABLE DROP COLUMN); test_bm25_error_propagates_fail_loud PASSED.
- NL-FR query FTS=0 is expected: French corpus lacks sufficient keyword co-occurrence; vector branch retrieves CMS zone docs correctly.
- Task 4 qualitative chat verification: user approved — exact-ID queries hit reliably, natural-language quality preserved.
- Phase 13.1 (Postgres-native hybrid search) fully signed off.

## Blocker / Issues

- Backend container has no source volume mount — new alembic revisions must be `docker cp`'d into the container OR the image rebuilt before `alembic upgrade head`. Flag for Plan 13-03 preflight.
- rag-service container also has no source volume mount — any new source change requires a full `docker compose build rag-service` + restart before curl-based verifications. Flag for Plan 13-03.
- Git Bash on Windows host path-mangles `/app/...` in `docker compose exec` — prefix shell-outs with `MSYS_NO_PATHCONV=1`. Flag for Plan 13-03.

## Session Continuity

- **Last session:** 2026-06-11 — finalized 13-03 (Task 4 user approval recorded). Phase 13.1 Postgres-native hybrid search fully complete.
- **Stopped at:** Completed 13-03-smoke-toggle-observability-PLAN.md
- **Resume with:** Phase 13.2 Elasticsearch (next plan per ROADMAP)

---

*State recorded: 2026-06-06 after phase 13 plan 02 execution*