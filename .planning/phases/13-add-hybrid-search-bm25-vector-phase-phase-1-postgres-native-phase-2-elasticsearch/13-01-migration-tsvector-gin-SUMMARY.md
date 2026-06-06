---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
plan: 01
subsystem: database
tags: [postgres, alembic, tsvector, gin, fts, hybrid-search, pgvector]

# Dependency graph
requires:
  - phase: 12.1-rag-implementation-pgvector-document-ingestion-semantic-retrieval-and-chat-context-augmentation
    provides: doc_chunks table with content column + pgvector embedding(1024) + ivfflat index
provides:
  - "doc_chunks.content_tsv_fr (GENERATED tsvector, french config) populated for every row"
  - "doc_chunks.content_tsv_en (GENERATED tsvector, english config) populated for every row"
  - "GIN index doc_chunks_tsv_fr_idx on content_tsv_fr"
  - "GIN index doc_chunks_tsv_en_idx on content_tsv_en"
  - "Alembic head advanced from chat_sessions_multi to hybrid_search_tsvector"
affects: [13-02-hybrid-module-and-retriever, 13-03-smoke-toggle-observability]

# Tech tracking
tech-stack:
  added: [postgres-fts, gin-index, tsvector-generated-column]
  patterns:
    - "GENERATED ALWAYS AS (to_tsvector('<config>', content)) STORED for zero-touch backfill + auto-sync on writes"
    - "SET lock_timeout = '30s' guard around DDL that takes ACCESS EXCLUSIVE lock"

key-files:
  created:
    - "app/backend/alembic/versions/hybrid_search_tsvector.py"
  modified: []

key-decisions:
  - "GENERATED ALWAYS STORED tsvector columns (not application-level UPDATE) — backfill + future inserts are automatic, ingestor.py stays untouched"
  - "Non-CONCURRENT CREATE INDEX — Alembic wraps upgrade in a transaction and CREATE INDEX CONCURRENTLY can't run inside one. ~1s blocking at current 5000-row ceiling is the accepted tradeoff (per RESEARCH §3.E option (a))"
  - "Two language configs (french + english) as separate columns + separate GIN indexes — query side will use GREATEST(rank_fr, rank_en) per CONTEXT.md"
  - "SET lock_timeout = '30s' guard so a stuck ALTER fails loud at 30s instead of blocking writers indefinitely"

patterns-established:
  - "Generated tsvector column + GIN index: copyable shape for any future text column that needs FTS"
  - "DDL safety lock_timeout guard: applies to any future ALTER TABLE that holds ACCESS EXCLUSIVE"

requirements-completed: [HYB-01, HYB-02, HYB-09, HYB-12]

# Metrics
duration: 8 min
completed: 2026-06-06
---

# Phase 13 Plan 01: Migration tsvector + GIN Summary

**Two GENERATED tsvector columns (french + english) plus matching GIN indexes added to `doc_chunks` via a new Alembic revision, unlocking the Postgres-native BM25 branch for Plan 13-02 with zero ingestor changes.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-06T (plan-execution)
- **Completed:** 2026-06-06
- **Tasks:** 2
- **Files modified:** 1 new file

## Accomplishments

- New Alembic revision `hybrid_search_tsvector` (down_revision `chat_sessions_multi`) created and applied to dev DB.
- `doc_chunks` now has two generated tsvector columns (`content_tsv_fr`, `content_tsv_en`) — both populated for every existing row (4/4 backfilled), both auto-update on any future write to `content`.
- Two GIN indexes (`doc_chunks_tsv_fr_idx`, `doc_chunks_tsv_en_idx`) created and verified usable by the planner (Bitmap Index Scan on `doc_chunks_tsv_en_idx` confirmed via `EXPLAIN` with `enable_seqscan=off`).
- DDL guarded with `SET lock_timeout = '30s'` — migration fails loud if it can't get ACCESS EXCLUSIVE within 30 s.
- Symmetric `downgrade()` drops indexes then columns; no manual cleanup needed.

## Task Commits

1. **Task 1: Write Alembic revision `hybrid_search_tsvector`** — `bf120f2` (feat)
2. **Task 2: Apply migration in dev DB and verify schema + indexes are live** — `2615c33` (chore)

**Plan metadata commit:** to be added by orchestrator (`docs(13-01): …`).

## Files Created/Modified

- `app/backend/alembic/versions/hybrid_search_tsvector.py` — NEW. 66 lines. Revision id `hybrid_search_tsvector`, down_revision `chat_sessions_multi`. Two `ALTER TABLE … ADD COLUMN … GENERATED ALWAYS AS STORED` statements, two `CREATE INDEX … USING GIN` statements, `lock_timeout` guard, symmetric downgrade.

## Migration Application — Captured Evidence

### `alembic upgrade head` stdout

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade chat_sessions_multi -> hybrid_search_tsvector,
  Phase 13.1 hybrid search — add two GENERATED tsvector columns + GIN indexes on doc_chunks.
```

### Column listing — `information_schema.columns`

```
  column_name   | data_type
----------------+-----------
 content_tsv_en | tsvector
 content_tsv_fr | tsvector
(2 rows)
```

### Index listing — `pg_indexes`

```
       indexname       |                                      indexdef
-----------------------+------------------------------------------------------------------------------------
 doc_chunks_tsv_fr_idx | CREATE INDEX doc_chunks_tsv_fr_idx ON public.doc_chunks USING gin (content_tsv_fr)
 doc_chunks_tsv_en_idx | CREATE INDEX doc_chunks_tsv_en_idx ON public.doc_chunks USING gin (content_tsv_en)
(2 rows)
```

### Backfill — NULL check on `doc_chunks`

```
 total | fr_populated | en_populated
-------+--------------+--------------
     4 |            4 |            4
(1 row)
```

100% backfilled (4 of 4 rows). Note: row count is low (4) because Plan 13's dev DB has only the seed SAGEMCOM Production Zones markdown ingested at the time of the migration. Plan 13-03 smoke tests should re-seed work-order chunks (`OT-SEED-Cxx-M20`) before asserting on exact-ID retrieval.

### EXPLAIN — keyword query plan

With default planner settings (4 rows total, planner correctly prefers Seq Scan at this scale):

```
                                      QUERY PLAN
---------------------------------------------------------------------------------------
 Limit
   ->  Sort
         Sort Key: (ts_rank_cd(content_tsv_en, '''machin'' & ''zone'''::tsquery)) DESC
         ->  Seq Scan on doc_chunks  (cost=0.00..1.06 rows=3 width=20)
               Filter: (content_tsv_en @@ '''machin'' & ''zone'''::tsquery)
```

This is correct behavior — at 4 rows, GIN overhead exceeds Seq Scan. The plan's failure threshold is "Seq Scan AND ≥ 1000 rows", which is not triggered here.

Forcing the planner with `SET enable_seqscan = off` confirms the GIN index is functional:

```
                                           QUERY PLAN
-------------------------------------------------------------------------------------------------
 Limit
   ->  Sort
         Sort Key: (ts_rank_cd(content_tsv_en, '''machin'' & ''zone'''::tsquery)) DESC
         ->  Bitmap Heap Scan on doc_chunks
               Recheck Cond: (content_tsv_en @@ '''machin'' & ''zone'''::tsquery)
               ->  Bitmap Index Scan on doc_chunks_tsv_en_idx
                     Index Cond: (content_tsv_en @@ '''machin'' & ''zone'''::tsquery)
```

### Row count at migration time

`SELECT COUNT(*) FROM doc_chunks` = **4** rows at the moment of the migration.

This is informational for Plan 13-03 smoke tests: they should ingest or re-sync the work-order corpus (`OT-SEED-Cxx-M20`) before running EXPLAIN assertions, because at < 1000 rows the planner will continue to pick Seq Scan and "BitmapIndexScan present" cannot be asserted on the default plan.

## Decisions Made

- **GENERATED ALWAYS STORED, not application-level UPDATE.** Postgres backfills automatically when the column is added, and re-evaluates on every future write to `content`. This is exactly the "zero changes to `ingestor.py`" promise CONTEXT.md locks in.
- **Non-CONCURRENT CREATE INDEX.** Alembic wraps upgrades in a transaction; `CREATE INDEX CONCURRENTLY` can't run inside one. Per RESEARCH §3.E option (a), accepted the ~1 s blocking tradeoff over the alembic-COMMIT/BEGIN hack.
- **Each ALTER and CREATE as a separate `op.execute()`.** Easier to localize a failure in psql output if any single statement fails.
- **`SET lock_timeout = '30s'` guard.** Migration fails loud at 30 s rather than blocking writers indefinitely if a long-running session holds an incompatible lock.

## Deviations from Plan

None — plan executed exactly as written.

The only operational note: at Task 2 step 2 the backend container's image had a stale alembic versions directory (the new revision file lives on the host bind-less layer that's baked into the image). Resolved by `docker cp` of the migration file into the running container before `alembic upgrade head`. This is an environment quirk (backend has no source volume mount), not a plan deviation, and was already implicit in the plan's "Apply the migration inside the backend container" step.

---

**Total deviations:** 0 auto-fixed.
**Impact on plan:** None.

## Issues Encountered

- **Backend container has no source volume mount.** First `alembic upgrade head` reported no upgrade because the new revision file existed only on host, not inside the container. Fixed by `docker cp app/backend/alembic/versions/hybrid_search_tsvector.py asset_management_backend:/app/alembic/versions/`. For Plan 13-03 this means CI / future migrations must either rebuild the backend image or `docker cp` the new revision before invoking alembic — worth flagging in Plan 13-03's preflight.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Ready for Plan 13-02** (hybrid module + retriever fan-out). All required schema (2 tsvector columns + 2 GIN indexes) is live on the dev DB. The keyword SQL recommended in RESEARCH §5 can be written against this schema verbatim.
- **Note for Plan 13-03 smoke tests:** the dev DB currently has 4 chunks. Before running EXPLAIN assertions that require the planner to pick GIN, ingest more corpus (e.g., re-run `app/backend/scripts/sync_db_to_rag.py --tables ordres_travail` after `seed_ml_data_m13.py`) so the planner crosses its seq-scan-preferred threshold.
- **Image rebuild requirement:** when Plan 13-02 lands new code in the backend or rag-service containers, a `docker compose build` (or `make rebuild`) is required before `alembic upgrade head` from inside the container. Alternative: `docker cp` the revision file as done here.

## Self-Check: PASSED

- File `app/backend/alembic/versions/hybrid_search_tsvector.py` exists on disk.
- Commit `bf120f2` (Task 1) present in `git log` on branch `clean_Phase_1`.
- Commit `2615c33` (Task 2) present in `git log` on branch `clean_Phase_1`.
- `alembic current` reports `hybrid_search_tsvector (head)` inside the backend container.
- `information_schema.columns` confirms both tsvector columns.
- `pg_indexes` confirms both GIN indexes.
- `doc_chunks` backfill: 4/4 rows have non-null `content_tsv_fr` and `content_tsv_en`.

---
*Phase: 13-add-hybrid-search-bm25-vector*
*Completed: 2026-06-06*
