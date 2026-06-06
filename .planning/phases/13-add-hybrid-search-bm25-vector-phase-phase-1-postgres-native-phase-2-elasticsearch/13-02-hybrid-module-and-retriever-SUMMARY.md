---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
plan: 02
subsystem: rag-service
tags: [hybrid-search, rrf, postgres-fts, bm25, pgvector, fastapi]

# Dependency graph
requires:
  - phase: 13-01
    provides: doc_chunks.content_tsv_fr + content_tsv_en GENERATED columns + GIN indexes
provides:
  - "hybrid.py module with rrf_fuse + keyword_search + hybrid_enabled toggle + hybrid_stats counters"
  - "retriever.retrieve_chunks() fan-out: vector top-30 + keyword top-30 -> RRF -> reranker"
  - "5-tuple cache key (query, machine_id, top_k, threshold, hybrid_enabled) -- toggle-safe"
  - "GET /hybrid-info endpoint"
  - "hybrid block in /cache-stats response"
  - "HYBRID_ENABLED env wired through docker-compose.yml + .env.example"
affects: [13-03-smoke-toggle-observability]

# Tech tracking
tech-stack:
  added: [reciprocal-rank-fusion, postgres-fts-application-layer, pytest-asyncio]
  patterns:
    - "Module-level stats counters + *_stats() dict (mirrors reranker.rerank_stats shape)"
    - "Env-flag toggle, default true (mirrors reranker.rerank_enabled)"
    - "Fail-loud: BM25 errors re-raise; embedding failure preserves pre-13 vector-only behavior"
    - "Cache key tuple widening atomic with behavior change"

key-files:
  created:
    - "app/rag-service/hybrid.py"
    - "app/rag-service/tests/test_hybrid_rrf.py"
    - "app/rag-service/tests/test_retriever_hybrid_toggle.py"
  modified:
    - "app/rag-service/retriever.py"
    - "app/rag-service/main.py"
    - "app/rag-service/requirements.txt"
    - "app/rag-service/.dockerignore"
    - "docker-compose.yml"
    - ".env.example"

key-decisions:
  - "tests/ removed from rag-service .dockerignore so verify command 'docker compose run --rm rag-service pytest tests/...' works as written in plan (Rule 3 -- blocking issue auto-fixed)"
  - "pytest + pytest-asyncio added to requirements.txt (image lacked them) -- plan flagged this as a contingent edit"
  - "Vector branch SQL kept verbatim, additive only: dc.id AS chunk_id projected so rrf_fuse() can dedupe by stable PK"
  - "Cache key widened to 5-tuple (query, machine_id, top_k, threshold, hybrid_enabled) atomically with behavior change so toggling does not return stale cached results"
  - "BM25 SQL errors re-raised (fail loud per CONTEXT.md); embedding failure in hybrid mode lets keyword branch still contribute; in vector-only mode preserves pre-13 [] return"
  - "Source mix computed by checking 'vector_rank' / 'keyword_rank' presence in final returned chunks (post-rerank); record_call() accumulates into module-level counters"

patterns-established:
  - "Hybrid-style fan-out + Python-side fusion: copyable shape for any future second-source addition (e.g. graph search) -- new branch + new column in cache key + new constants in own module"

requirements-completed: [HYB-02, HYB-03, HYB-04, HYB-05, HYB-06, HYB-07, HYB-08, HYB-10, HYB-11]

# Metrics
duration: ~15 min
completed: 2026-06-06
---

# Phase 13 Plan 02: Hybrid Module + Retriever Summary

**Postgres-native hybrid retrieval shipped: a new `hybrid.py` module houses RRF (k=60), the keyword FTS branch, an `HYBRID_ENABLED` toggle, and per-call stats; `retriever.retrieve_chunks()` now fans out a vector top-30 + keyword top-30, fuses by RRF, trims to 30, and forwards to the existing cross-encoder reranker -- with a 5-tuple cache key so toggling is safe and BM25 errors fail loud per CONTEXT.md.**

## Performance

- **Duration:** ~15 min (incl. 3 rag-service rebuilds)
- **Started:** 2026-06-06T16:16:01Z
- **Completed:** 2026-06-06
- **Tasks:** 3
- **Files modified:** 6 (3 new, 3 modified) + 3 infra files

## Accomplishments

- New `app/rag-service/hybrid.py` (231 lines) exports `hybrid_enabled()`, `keyword_search()`, `rrf_fuse()`, `hybrid_stats()`, `record_call()`, and the locked constants `HYBRID_RRF_K=60`, `HYBRID_OVERFETCH=30`, `FTS_CONFIGS=('french','english')`, `TIE_BREAK='vector_similarity_desc'`.
- `retriever.retrieve_chunks()` refactored to fan-out (vector + keyword) -> RRF -> reranker. Cache key widened to 5-tuple. Vector SQL kept verbatim except additive `dc.id AS chunk_id` projection. BM25 errors fail loud. Pre-13 byte-identical behavior preserved when `HYBRID_ENABLED=false`.
- `main.py` exposes `GET /hybrid-info` and adds `hybrid` block to `/cache-stats`.
- `docker-compose.yml` + `.env.example` carry `HYBRID_ENABLED` (default `true`) immediately below `RERANK_ENABLED`.
- 37 unit tests landed (25 RRF + 12 retriever toggle), all green inside the rag-service container.

## Task Commits

1. **Task 1: Create app/rag-service/hybrid.py + RRF unit test** — `681a66e` (feat)
2. **Task 2: Refactor retriever.retrieve_chunks() to fan-out + RRF + reranker + cache widening + tests** — `10d1a09` (feat)
3. **Task 3: Wire /hybrid-info + /cache-stats.hybrid + HYBRID_ENABLED env** — `98a5ca1` (feat)

**Plan metadata commit:** to be added by orchestrator (`docs(13-02): …`).

## Files Created/Modified

### Created
- `app/rag-service/hybrid.py` — 231 lines. Hybrid module: env toggle, keyword FTS CTE SQL, RRF fusion, per-call stats counters, locked constants.
- `app/rag-service/tests/test_hybrid_rrf.py` — 156 lines. 25 tests covering the worked example from RESEARCH §4, tie-break, dedup-by-chunk_id, env truthy/falsy, limit param.
- `app/rag-service/tests/test_retriever_hybrid_toggle.py` — 261 lines. 12 tests covering 5-tuple cache key, toggle changes cache key, hybrid-off skips keyword branch, hybrid-on uses HYBRID_OVERFETCH, RRF dedup, fail-loud BM25, embedding-fail, empty fusion no-rerank, record_call wiring.

### Modified
- `app/rag-service/retriever.py` — cache key widened to 5-tuple; vector SQL adds `dc.id AS chunk_id`; new keyword branch (+ fail-loud); RRF fusion call; INFO log + record_call when hybrid_on. Vector-only path preserved when hybrid_off.
- `app/rag-service/main.py` — new `/hybrid-info` endpoint; `hybrid` block appended to `/cache-stats` response (key order: embedding_cache, retrieval_cache, reranker, hybrid).
- `app/rag-service/requirements.txt` — added `pytest>=8.0.0` and `pytest-asyncio>=0.23.0` so tests run inside the rag-service container.
- `app/rag-service/.dockerignore` — removed `tests/` exclusion so verify commands (`docker compose run --rm rag-service pytest tests/...`) work as written in the plan.
- `docker-compose.yml` — added `HYBRID_ENABLED: ${HYBRID_ENABLED:-true}` under rag-service.environment, immediately below `RERANK_ENABLED`.
- `.env.example` — added `HYBRID_ENABLED=` immediately below `RERANK_ENABLED=`.

## Final Signatures + Cache Key

```python
# app/rag-service/hybrid.py — exports
HYBRID_RRF_K = 60
HYBRID_OVERFETCH = 30
FTS_CONFIGS = ("french", "english")
TIE_BREAK = "vector_similarity_desc"

def hybrid_enabled() -> bool: ...
async def keyword_search(query: str, db: AsyncSession, machine_id: int | None,
                         top_k: int = HYBRID_OVERFETCH) -> list[dict]: ...
def rrf_fuse(vector_hits: list[dict], keyword_hits: list[dict],
             k: int = HYBRID_RRF_K, limit: int = HYBRID_OVERFETCH) -> list[dict]: ...
def hybrid_stats() -> dict: ...
def record_call(vector_n: int, keyword_n: int,
                returned_with_source: list[str]) -> None: ...
```

```python
# app/rag-service/retriever.py — entry point unchanged signature
async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    machine_id: Optional[int] = None,
    top_k: int = 3,
    threshold: float = 0.30,
) -> list[dict]: ...

# 5-tuple cache key (toggle-safe):
hybrid_on = hybrid_enabled()
cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)
```

## Pytest Output (inside rag-service container)

### `pytest tests/test_hybrid_rrf.py`

```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0
rootdir: /app
plugins: asyncio-1.4.0, anyio-4.13.0
collected 25 items

tests/test_hybrid_rrf.py .........................                       [100%]

============================== 25 passed in 0.36s ==============================
```

### `pytest tests/test_retriever_hybrid_toggle.py`

```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0
rootdir: /app
plugins: asyncio-1.4.0, anyio-4.13.0
collected 12 items

tests/test_retriever_hybrid_toggle.py ............                       [100%]

============================== 12 passed in 7.15s ==============================
```

### Combined: `pytest tests/test_hybrid_rrf.py tests/test_retriever_hybrid_toggle.py`

```
collected 37 items
tests/test_hybrid_rrf.py .........................                       [ 67%]
tests/test_retriever_hybrid_toggle.py ............                       [100%]
============================== 37 passed in 6.68s ==============================
```

## Live Endpoint Spot-Checks

### `curl http://localhost:8003/hybrid-info`

```json
{
  "enabled": true,
  "fusion": "rrf",
  "k": 60,
  "overfetch": 30,
  "fts_configs": ["french", "english"],
  "tie_break": "vector_similarity_desc"
}
```

### `curl http://localhost:8003/cache-stats | jq .hybrid`

```json
{
  "enabled": true,
  "fusion": "rrf",
  "k": 60,
  "overfetch": 30,
  "fts_configs": ["french", "english"],
  "searches": 0,
  "vector_only_count": 0,
  "keyword_only_count": 0,
  "both_count": 0,
  "keyword_zero_hits": 0,
  "vector_zero_hits": 0
}
```

### Plan's automated verify command

```
hybrid-info OK
cache-stats.hybrid OK
```

## docker-compose.yml diff (HYBRID_ENABLED wiring)

```diff
       # Reranker toggle — set to "false" to disable cross-encoder reranking (A/B test)
       RERANK_ENABLED: ${RERANK_ENABLED:-true}
+      # Hybrid retrieval toggle (Phase 13.1) — set to "false" to fall back to vector-only
+      HYBRID_ENABLED: ${HYBRID_ENABLED:-true}
```

## .env.example diff

```diff
 RERANK_ENABLED=
+HYBRID_ENABLED=
```

## Decisions Made

- **Vector branch SQL kept verbatim except additive `dc.id AS chunk_id` projection.** RESEARCH §5 and the plan both lock chunk_id as the dedup key. Adding the projection is the minimal-risk way to surface a stable PK without restructuring the existing query that's been in production since Phase 12.1.
- **Cache key widened atomically with the behavior change.** Toggling `HYBRID_ENABLED` between requests would have returned stale entries if the key change lagged the behavior change.
- **BM25 fail-loud literally re-raises.** No retry, no fallback, no wrapping. CONTEXT.md is explicit and that semantic is the entire point of being able to detect regressions in chat quality immediately.
- **Embedding failure handling diverges by mode.** In vector-only mode (hybrid_off) it returns `[]` (pre-13 behavior preserved exactly). In hybrid mode it still lets the keyword branch run so the query can still produce keyword-only hits -- aligned with the plan's "byte-identical when off" + "keyword may still contribute when on" mandate.
- **Source mix labels derived from rank-key presence in final results** (`'vector_rank' in c` / `'keyword_rank' in c`). Post-rerank the chunk dicts still carry these fields because the reranker only reads `content` and preserves everything else (verified at `reranker.py:60-97`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest + pytest-asyncio missing from rag-service image**
- **Found during:** Task 1 (first attempt at the verify command).
- **Issue:** The image had neither `pytest` nor `pytest-asyncio`, so `docker compose run --rm rag-service pytest -x tests/...` exited with "no tests collected" / module-not-found before the plan's automated verify could pass.
- **Fix:** Added `pytest>=8.0.0` and `pytest-asyncio>=0.23.0` to `app/rag-service/requirements.txt`. The plan explicitly listed `requirements.txt` as a contingent edit in Task 2's `<files>` so this is anticipated, not a deviation in spirit -- but it had to happen during Task 1 to make the verify command run.
- **Files modified:** `app/rag-service/requirements.txt`
- **Commit:** `681a66e` (folded into Task 1 commit because it was required to run Task 1's verify)

**2. [Rule 3 - Blocking] rag-service `.dockerignore` was excluding `tests/`**
- **Found during:** Task 1 (after rebuild with pytest, the verify command found 0 tests because tests/ wasn't shipped in the image).
- **Issue:** `app/rag-service/.dockerignore` had `tests/` in its exclusion list, so `tests/test_hybrid_rrf.py` was not in the built image. `docker compose run --rm rag-service pytest -x tests/test_hybrid_rrf.py` reported `file or directory not found: tests/test_hybrid_rrf.py`.
- **Fix:** Removed `tests/` from `.dockerignore` (kept the more specific `pytest.ini` and `.pytest_cache/` excludes; added a comment explaining the trade-off). The image now ships tests; verify command runs as written.
- **Files modified:** `app/rag-service/.dockerignore`
- **Commit:** `681a66e`

### Other Notes

- Both Task 1 and Task 2 had `tdd="true"`. Task 1 was effectively a spec-first test against a brand-new module so RED never actually went red (the module was created in the same step). The intent of TDD -- locking the contract in test code before implementation drifts -- is preserved because the test file pins the exact RESEARCH §4 worked example and the locked constants, providing a regression boundary for any future tweak.

**Total auto-fix attempts:** 2 (both Rule 3, both required to make the plan's verify commands runnable).
**Impact on plan:** None on the deliverable contract; both fixes preserved or strengthened the plan's "tests run inside the container" requirement.

## Issues Encountered

- **Git Bash path-mangling on Windows host.** `docker compose exec rag-service ls /app/tests/` was rewritten by Git Bash to `C:/Program Files/Git/app/tests/`. Resolved by prefixing with `MSYS_NO_PATHCONV=1`. Documented for Plan 13-03 -- any shell-out into the container from this Windows host needs the same env guard.
- **rag-service container needed a full rebuild after each source change.** The rag-service has no source volume mount (same as backend, flagged in Plan 13-01's "Issues Encountered"). For Plan 13-03's smoke tests, expect to rebuild + restart before running curl-based verifications.

## User Setup Required

None — no external service configuration. `HYBRID_ENABLED` defaults to `true` so the hybrid path is on out-of-the-box. Users can set `HYBRID_ENABLED=false` in `.env` to fall back to vector-only.

## Next Phase Readiness

- **Ready for Plan 13-03** (smoke tests, toggle behavior verification, observability assertions). The schema (13-01) + the code path (13-02) are both live and verified. Plan 13-03's smoke tests should:
  - Re-sync the work-order corpus (`OT-SEED-Cxx-M20`) per Plan 13-01's note (current 4-chunk dev DB is too small for meaningful BM25 vs vector spread).
  - Hit `/retrieve` with exact-ID queries to assert position-1 ranking.
  - Toggle `HYBRID_ENABLED=false` (restart rag-service), re-query, confirm ordering changes.
  - Assert `/cache-stats.hybrid.searches` increments across calls.
  - Assert INFO log line `hybrid query=...` appears in `docker compose logs rag-service` per query.
- **Backend chat caller unchanged.** The Pydantic `ChunkResult` model in `main.py` still filters to `{content, metadata, similarity}` so the `/retrieve` JSON response shape is byte-identical from the chat backend's perspective.
- **No frontend changes.** Per CONTEXT.md the entire phase is server-only.

## Self-Check: PASSED

- File `app/rag-service/hybrid.py` exists on disk (231 lines).
- File `app/rag-service/tests/test_hybrid_rrf.py` exists on disk (25 tests).
- File `app/rag-service/tests/test_retriever_hybrid_toggle.py` exists on disk (12 tests).
- Commit `681a66e` (Task 1) present in `git log` on branch `clean_Phase_1`.
- Commit `10d1a09` (Task 2) present in `git log` on branch `clean_Phase_1`.
- Commit `98a5ca1` (Task 3) present in `git log` on branch `clean_Phase_1`.
- `docker compose run --rm rag-service pytest tests/test_hybrid_rrf.py tests/test_retriever_hybrid_toggle.py` returns `37 passed`.
- `curl http://localhost:8003/hybrid-info` returns all 6 documented keys with locked values.
- `curl http://localhost:8003/cache-stats` includes `hybrid` block with all 10 documented keys.
- `docker-compose.yml` contains `HYBRID_ENABLED: ${HYBRID_ENABLED:-true}` directly below `RERANK_ENABLED`.
- `.env.example` contains `HYBRID_ENABLED=` directly below `RERANK_ENABLED=`.
- No edits to `app/backend/services/rag_client.py`, `app/backend/modules/shared/routes/chat.py`, `app/rag-service/ingestor.py`, or any frontend file.

---
*Phase: 13-add-hybrid-search-bm25-vector*
*Completed: 2026-06-06*
