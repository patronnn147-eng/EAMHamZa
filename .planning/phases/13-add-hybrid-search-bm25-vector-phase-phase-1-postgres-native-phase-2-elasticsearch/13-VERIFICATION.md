---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
verified: 2026-06-11T00:00:00Z
status: passed
score: 19/19 must-haves verified
---

# Phase 13: Hybrid Search (BM25 + Vector) Verification Report

**Phase Goal:** Phase 13.1 — Add Postgres-native BM25-style keyword retrieval alongside the existing pgvector cosine path in `rag-service`. Fuse the two via Reciprocal Rank Fusion (k=60), feed the fused list to the existing cross-encoder reranker, and surface observability + a runtime toggle. Phase 13.2 (Elasticsearch) is deferred per CONTEXT.md.

**Verified:** 2026-06-11
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | doc_chunks has a content_tsv_fr generated tsvector column populated for every existing row | VERIFIED | `hybrid_search_tsvector.py` lines 35-39 — `GENERATED ALWAYS AS (to_tsvector('french', content)) STORED`; SUMMARY-01 confirms 4/4 rows backfilled at migration time |
| 2 | doc_chunks has a content_tsv_en generated tsvector column populated for every existing row | VERIFIED | `hybrid_search_tsvector.py` lines 40-44 — `GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`; SUMMARY-01 confirms 4/4 rows backfilled |
| 3 | A GIN index exists on content_tsv_fr and is used by the planner for @@ queries | VERIFIED | `hybrid_search_tsvector.py` lines 47-54; SUMMARY-01 shows `doc_chunks_tsv_fr_idx` confirmed in pg_indexes; EXPLAIN with `enable_seqscan=off` shows Bitmap Index Scan |
| 4 | A GIN index exists on content_tsv_en and is used by the planner for @@ queries | VERIFIED | `hybrid_search_tsvector.py` lines 47-54; SUMMARY-01 shows `doc_chunks_tsv_en_idx` confirmed in pg_indexes |
| 5 | A new module app/rag-service/hybrid.py exports hybrid_enabled(), keyword_search(), rrf_fuse(), hybrid_stats() and per-query stats counters | VERIFIED | `hybrid.py` 240 lines; all 9 exports present and substantive; HYBRID_RRF_K=60, HYBRID_OVERFETCH=30, FTS_CONFIGS=("french","english"), TIE_BREAK="vector_similarity_desc" confirmed |
| 6 | retriever.retrieve_chunks() fans out vector top-30 and keyword top-30 when HYBRID_ENABLED=true, fuses via RRF (k=60), trims to 30, forwards to existing reranker | VERIFIED | `retriever.py` lines 99-173; vector branch uses HYBRID_OVERFETCH when hybrid_on; keyword_search called; rrf_fuse called with k=HYBRID_RRF_K, limit=HYBRID_OVERFETCH |
| 7 | Retrieval cache key includes hybrid_enabled so toggling does not return stale results | VERIFIED | `retriever.py` line 92: `cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)` — exactly 5 elements; confirmed by unit test `test_cache_key_is_5_tuple_ending_in_hybrid_flag` |
| 8 | When HYBRID_ENABLED=false, behavior is byte-identical to the pre-13 vector-only path | VERIFIED | `retriever.py` lines 103, 160-162, 169; keyword_search not called; fused=candidates; confirmed by unit tests `test_hybrid_disabled_skips_keyword_branch` and `test_hybrid_disabled_uses_compute_overfetch_top_k` |
| 9 | BM25 SQL errors propagate as a 500 (fail loud) — no silent vector-only fallback | VERIFIED | `retriever.py` lines 153-159: `except Exception as e: logger.error(...); raise`; confirmed by unit test `test_bm25_error_propagates_fail_loud` PASSED; live smoke in SUMMARY-03 |
| 10 | GET /hybrid-info returns {enabled, fusion:'rrf', k:60, overfetch:30, fts_configs:['french','english'], tie_break:'vector_similarity_desc'} | VERIFIED | `main.py` lines 330-340; live endpoint response documented in SUMMARY-02 |
| 11 | GET /cache-stats includes a hybrid block with all counter fields | VERIFIED | `main.py` line 316: `"hybrid": hybrid_stats()`; hybrid_stats() returns all 10 keys including searches, vector_only_count, keyword_only_count, both_count, keyword_zero_hits, vector_zero_hits; live response in SUMMARY-02 |
| 12 | Per-query INFO log line documents vector_hits, keyword_hits, fused count, returned count, and source_mix | VERIFIED | `retriever.py` lines 192-200; live log captured in SUMMARY-03: `hybrid query='OT-SEED-C49-M20' machine_id=None vector_hits=30 keyword_hits=1 fused=30 returned=5 source_mix=(both:1, vector_only:4, keyword_only:0)` |
| 13 | docker-compose.yml exposes HYBRID_ENABLED with default true, immediately below RERANK_ENABLED | VERIFIED | docker-compose.yml line 237: `HYBRID_ENABLED: ${HYBRID_ENABLED:-true}`; position confirmed at char 8129, RERANK_ENABLED at 7991 |
| 14 | .env.example has a matching HYBRID_ENABLED= line immediately below RERANK_ENABLED= | VERIFIED | .env.example line 41: `HYBRID_ENABLED=`; RERANK_ENABLED on line 40 |
| 15 | Exact-ID smoke query 'OT-SEED-C49-M20' ranks the matching chunk at position 1 when HYBRID_ENABLED=true | VERIFIED | SUMMARY-03 Task 1: OT-SEED-C49-M20 at position 1, similarity=0.636, source=both, keyword_hits=1 |
| 16 | Toggling HYBRID_ENABLED=false changes the top-5 ordering for the exact-ID query | VERIFIED | SUMMARY-03 Task 2: vector-only top-5 [C49,C47,C44,C48,C39] differs from hybrid-on [C49,C47,C44,C46,C48]; OT-SEED-C46-M20 absent in vector-only |
| 17 | /hybrid-info 'enabled' field tracks the env state after container restart | VERIFIED | SUMMARY-03 Task 2: /hybrid-info shows enabled=false after HYBRID_ENABLED=false restart, returns enabled=true after restoring |
| 18 | /cache-stats hybrid counters move after /retrieve calls | VERIFIED | SUMMARY-03 Task 1: searches incremented from 0 to 2 after two calls; both_count=1; keyword_zero_hits=1 |
| 19 | User qualitative chat improvement approved | VERIFIED | SUMMARY-03 Task 4: user verbatim response "approved"; exact-ID queries hit reliably, NL queries preserved |

**Score:** 19/19 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/backend/alembic/versions/hybrid_search_tsvector.py` | Alembic revision adding 2 generated tsvector cols + 2 GIN indexes on doc_chunks | VERIFIED | 67 lines; revision="hybrid_search_tsvector", down_revision="chat_sessions_multi"; both ALTER TABLE GENERATED ALWAYS, both CREATE INDEX USING GIN, lock_timeout guard, symmetric downgrade |
| `app/rag-service/hybrid.py` | hybrid_enabled, keyword_search, rrf_fuse, hybrid_stats, record_call, constants | VERIFIED | 240 lines (min_lines=120 exceeded); all 9 exports present; HYBRID_RRF_K=60, HYBRID_OVERFETCH=30; websearch_to_tsquery SQL; no DB I/O at import time |
| `app/rag-service/retriever.py` | retrieve_chunks() with fan-out + RRF + reranker handoff | VERIFIED | Contains hybrid_enabled, keyword_search, rrf_fuse, record_call, 5-tuple cache key, chunk_id projection, fail-loud raise |
| `app/rag-service/main.py` | /cache-stats with hybrid block + new /hybrid-info endpoint | VERIFIED | hybrid_stats in cache_stats; @app.get("/hybrid-info") endpoint present; correct 6-key response shape |
| `app/rag-service/tests/test_hybrid_rrf.py` | RRF unit tests | VERIFIED | 196 lines, 12 test functions; covers worked example, tie-break, dedup, empty inputs, env toggle; 25 passed in container |
| `app/rag-service/tests/test_retriever_hybrid_toggle.py` | Retriever toggle + fail-loud tests | VERIFIED | 349 lines, 12 test functions; covers 5-tuple cache key, toggle, hybrid-off skip, HYBRID_OVERFETCH, RRF dedup, fail-loud BM25, embedding-fail, empty fusion, record_call; 12 passed in container |
| `docker-compose.yml` | HYBRID_ENABLED env wired into rag-service | VERIFIED | Line 237: `HYBRID_ENABLED: ${HYBRID_ENABLED:-true}` directly below RERANK_ENABLED |
| `.env.example` | HYBRID_ENABLED placeholder | VERIFIED | Line 41: `HYBRID_ENABLED=` directly below RERANK_ENABLED= |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| alembic revision hybrid_search_tsvector | alembic head chat_sessions_multi | down_revision attribute | VERIFIED | `down_revision = "chat_sessions_multi"` confirmed in migration file |
| GENERATED ALWAYS AS expression | doc_chunks.content column | to_tsvector('french'\|'english', content) STORED | VERIFIED | Both ALTER TABLE statements use `to_tsvector('french', content)` and `to_tsvector('english', content)` |
| retriever.retrieve_chunks | hybrid.keyword_search | await call inside hybrid branch | VERIFIED | `retriever.py` line 154: `keyword_hits = await keyword_search(...)` |
| retriever.retrieve_chunks | hybrid.rrf_fuse | Python list fusion before reranker | VERIFIED | `retriever.py` line 165: `fused = rrf_fuse(candidates, keyword_hits, k=HYBRID_RRF_K, limit=HYBRID_OVERFETCH)` |
| retriever cache_key | hybrid.hybrid_enabled | tuple element 5 | VERIFIED | `retriever.py` line 92: `cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)` |
| main.cache_stats | hybrid.hybrid_stats | JSON 'hybrid' block | VERIFIED | `main.py` line 316: `"hybrid": hybrid_stats()` |
| main./hybrid-info endpoint | hybrid module constants | FastAPI route returning {enabled, fusion, k, overfetch, fts_configs, tie_break} | VERIFIED | `@app.get("/hybrid-info")` at line 330; all 6 keys present |
| docker-compose.yml rag-service env | .env.example | HYBRID_ENABLED with default true | VERIFIED | docker-compose uses `${HYBRID_ENABLED:-true}`; .env.example has `HYBRID_ENABLED=` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HYB-01 | 13-01, 13-02 | Add two generated tsvector columns + GIN indexes on doc_chunks via Alembic | SATISFIED | Alembic migration `hybrid_search_tsvector.py` with both columns + indexes; downgrade exists |
| HYB-02 | 13-01, 13-02 | Fan out vector top-30 and keyword top-30 retrieval per query, both filtered by machine_id | SATISFIED | `retriever.py` vector branch + keyword branch both pass machine_id; overfetch=HYBRID_OVERFETCH=30 |
| HYB-03 | 13-02 | Fuse the two lists via RRF (k=60) and trim to 30 candidates | SATISFIED | `rrf_fuse()` in `hybrid.py`; called with k=HYBRID_RRF_K=60, limit=HYBRID_OVERFETCH=30 |
| HYB-04 | 13-02 | Sort ties by (fused_score DESC, vector_similarity DESC) and forward to existing reranker | SATISFIED | `hybrid.py` line 234: `sorted(..., key=lambda h: (h["fused_score"], h.get("similarity", 0.0)), reverse=True)`; forwarded to `rerank()` |
| HYB-05 | 13-02 | Extend cache key with hybrid_enabled; reuse existing TTL + invalidation | SATISFIED | 5-tuple cache key confirmed; TTLCache unchanged; `clear_retrieval_cache()` still used on ingest/delete |
| HYB-06 | 13-02, 13-03 | Add HYBRID_ENABLED env (default true) — mirror RERANK_ENABLED pattern; fail loud on BM25 errors | SATISFIED | `hybrid_enabled()` mirrors `rerank_enabled()` exactly; fail-loud raise in retriever; docker-compose + .env.example wired |
| HYB-07 | 13-02, 13-03 | Extend /cache-stats with hybrid block + new GET /hybrid-info endpoint | SATISFIED | Both endpoints implemented in `main.py`; responses verified live in SUMMARY-02 and SUMMARY-03 |
| HYB-08 | 13-02 | Use websearch_to_tsquery for safe user-input handling | SATISFIED | `hybrid.py` SQL uses `websearch_to_tsquery('french', :q)` and `websearch_to_tsquery('english', :q)` |
| HYB-09 | 13-01, 13-03 | Confirm DB-synced corpus is searchable by ID via smoke-tests | SATISFIED | SUMMARY-03 Task 1: OT-SEED-C49-M20 at top-1 after syncing 130 work orders; keyword_hits=1 confirmed GIN branch fired |
| HYB-10 | 13-02 | Per-query INFO log with source_mix breakdown | SATISFIED | `retriever.py` lines 192-200; format `hybrid query=... source_mix=(both:X, vector_only:Y, keyword_only:Z)` confirmed in live logs |
| HYB-11 | 13-02 | Stats counters (searches, vector_only_count, keyword_only_count, both_count, keyword_zero_hits, vector_zero_hits) accumulate correctly | SATISFIED | `hybrid.py` `record_call()` and `hybrid_stats()` implement all 6 counters; unit test confirms; live delta in SUMMARY-03 |
| HYB-12 | 13-01 | Alembic downgrade -1 cleanly removes both columns and both indexes | SATISFIED | `hybrid_search_tsvector.py` `downgrade()` drops indexes then columns in reverse order with IF EXISTS guards |

**Note on HYB-10, HYB-11, HYB-12:** These IDs appear in PLANs but are not defined in RESEARCH.md's requirement table (which only lists HYB-01..HYB-09). They were added by the planner as implicit extensions: HYB-10 = per-query INFO log; HYB-11 = stats counters; HYB-12 = clean downgrade. All three are satisfied by the code and verified. No REQUIREMENTS.md file exists at project root — the binding contract is CONTEXT.md + RESEARCH.md per RESEARCH §phase_requirements.

**ROADMAP lists:** [HYB-01..HYB-09]. PLANs claim: [HYB-01..HYB-12]. No orphaned requirements found.

---

### Anti-Patterns Found

None. Scanned `hybrid.py`, `retriever.py`, `main.py`, and `hybrid_search_tsvector.py` for TODO/FIXME/PLACEHOLDER, empty returns, and console-only handlers. Zero findings.

---

### Human Verification Required

The following item was verified by the human during plan execution and is recorded here as closed:

**Qualitative chat retrieval improvement** — user tested the hybrid search via the chat UI with exact-ID and natural-language queries and responded "approved" (recorded in 13-03-smoke-toggle-observability-SUMMARY.md Task 4). No further human verification required for Phase 13.1.

---

## Gaps Summary

None. All 19 truths verified, all 8 artifacts pass all three levels (exists, substantive, wired), all 8 key links confirmed, all 12 requirement IDs (HYB-01..HYB-12) satisfied.

**Phase 13.1 (Postgres-native hybrid search) is fully achieved.**

The deliverables are:
- Alembic migration `hybrid_search_tsvector` with two GENERATED tsvector columns + GIN indexes on `doc_chunks`
- `hybrid.py` module (RRF fusion, keyword SQL, env toggle, stats counters)
- Refactored `retriever.retrieve_chunks()` with fan-out, 5-tuple cache key, fail-loud BM25, source attribution + INFO logs
- `/hybrid-info` and extended `/cache-stats` endpoints in `main.py`
- 37 unit tests (25 RRF + 12 retriever toggle) all green inside the container
- `HYBRID_ENABLED` env variable wired through `docker-compose.yml` and `.env.example`
- Live smoke evidence: OT-SEED-C49-M20 at top-1, toggle-off A/B ordering change confirmed, user qualitative approval

---

_Verified: 2026-06-11_
_Verifier: Claude (gsd-verifier)_
