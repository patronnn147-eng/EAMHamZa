---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/backend/alembic/versions/hybrid_search_tsvector.py
autonomous: true
requirements:
  - HYB-01
  - HYB-02
  - HYB-09
  - HYB-12
must_haves:
  truths:
    - "doc_chunks has a content_tsv_fr generated tsvector column populated for every existing row"
    - "doc_chunks has a content_tsv_en generated tsvector column populated for every existing row"
    - "A GIN index exists on content_tsv_fr and is used by the planner for @@ queries"
    - "A GIN index exists on content_tsv_en and is used by the planner for @@ queries"
    - "alembic upgrade head completes within lock_timeout=30s without locking writes longer than necessary"
    - "alembic downgrade -1 cleanly removes both columns and both indexes"
  artifacts:
    - path: "app/backend/alembic/versions/hybrid_search_tsvector.py"
      provides: "Alembic revision adding 2 generated tsvector cols + 2 GIN indexes on doc_chunks"
      contains: "down_revision = \"chat_sessions_multi\""
  key_links:
    - from: "alembic revision hybrid_search_tsvector"
      to: "alembic head chat_sessions_multi"
      via: "down_revision attribute"
      pattern: "down_revision\\s*=\\s*[\"']chat_sessions_multi[\"']"
    - from: "GENERATED ALWAYS AS expression"
      to: "doc_chunks.content column"
      via: "to_tsvector('french'|'english', content) STORED"
      pattern: "to_tsvector\\(\\s*['\"](french|english)['\"]\\s*,\\s*content\\s*\\)"
---

<preflight>
All `<automated>` shell commands in this plan assume bash via `docker compose exec`
(Linux container shell) or WSL/Git-Bash on the Windows host. PowerShell direct
execution is NOT supported — the embedded `awk`, `&&`, single-quoting, and pipe
semantics are bash-only.
</preflight>

<objective>
Add the Postgres-side foundation for BM25-style keyword retrieval on `doc_chunks`:
two GENERATED tsvector columns (french + english configs) plus a GIN index per
column. Existing rows must be backfilled automatically by Postgres at column
creation time (this is what GENERATED ALWAYS gives us for free).

Purpose: Phase 13.1 hybrid search is locked to Postgres native FTS. Without these
columns and indexes there is no keyword branch to fan out to; without the GIN
indexes the keyword query degenerates to a sequential scan. This migration is
the single prerequisite for the hybrid module (Plan 13-02).

Output:
- New Alembic revision file `hybrid_search_tsvector` with down_revision
  `chat_sessions_multi` (current head).
- After `alembic upgrade head`: doc_chunks has 2 new generated columns + 2 GIN
  indexes; existing rows have populated tsvectors (Postgres backfills on ADD
  COLUMN GENERATED).
- Clean `downgrade()` that drops indexes then columns in reverse order.
</objective>

<execution_context>
@C:/Users/Admin/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Admin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-CONTEXT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-RESEARCH.md

@app/backend/alembic/versions/chat_sessions_multi.py
@app/backend/alembic/versions/add_pgvector_rag.py

<interfaces>
<!-- Reference patterns extracted from existing migrations and Postgres docs. -->
<!-- Executor uses these directly — no need to explore the alembic tree. -->

Current alembic head (confirmed in repo):
```python
# app/backend/alembic/versions/chat_sessions_multi.py
revision = "chat_sessions_multi"
down_revision = "upgrade_embedding_dim_1024"
```

GENERATED ALWAYS AS STORED for tsvector (Postgres 15, pgvector/pgvector:pg15 image,
confirmed in CONTEXT.md and RESEARCH.md §3.B):
```sql
ALTER TABLE doc_chunks
  ADD COLUMN content_tsv_fr tsvector
  GENERATED ALWAYS AS (to_tsvector('french',  content)) STORED;

ALTER TABLE doc_chunks
  ADD COLUMN content_tsv_en tsvector
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX doc_chunks_tsv_fr_idx ON doc_chunks USING GIN (content_tsv_fr);
CREATE INDEX doc_chunks_tsv_en_idx ON doc_chunks USING GIN (content_tsv_en);
```

Behavior reminders (from research):
- ADD COLUMN GENERATED rewrites the table once (ACCESS EXCLUSIVE) and backfills.
- CREATE INDEX (non-CONCURRENT) holds a SHARE lock — fine at ~5000 rows.
- Do NOT use CREATE INDEX CONCURRENTLY: Alembic wraps in a transaction and CIC is
  not transactional. We accept ~1s blocking at this scale.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write Alembic revision hybrid_search_tsvector</name>
  <files>app/backend/alembic/versions/hybrid_search_tsvector.py</files>
  <action>
Create a new Alembic revision file at the exact path
`app/backend/alembic/versions/hybrid_search_tsvector.py`.

Required content:

1. Module docstring explaining the goal: "Phase 13.1 hybrid search — add two
   GENERATED tsvector columns + GIN indexes on doc_chunks. French + english
   stemming. Backfill is automatic via GENERATED ALWAYS. Locks: ACCESS EXCLUSIVE
   during ADD COLUMN rewrite (~few seconds at current scale)."

2. Revision identifiers:
   - `revision = "hybrid_search_tsvector"`
   - `down_revision = "chat_sessions_multi"`  (current head — verified in
     `app/backend/alembic/versions/chat_sessions_multi.py:10-11`)
   - `branch_labels = None`
   - `depends_on = None`

3. `upgrade()` body — execute exactly these statements in order, each via
   `op.execute(sa.text(...))`:

   a. `SET lock_timeout = '30s'`  (per RESEARCH §3.E mitigation — fail loud if
      we can't get the lock in 30 s rather than blocking forever).

   b. `ALTER TABLE doc_chunks ADD COLUMN content_tsv_fr tsvector GENERATED ALWAYS AS (to_tsvector('french', content)) STORED`

   c. `ALTER TABLE doc_chunks ADD COLUMN content_tsv_en tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`

   d. `CREATE INDEX doc_chunks_tsv_fr_idx ON doc_chunks USING GIN (content_tsv_fr)`

   e. `CREATE INDEX doc_chunks_tsv_en_idx ON doc_chunks USING GIN (content_tsv_en)`

   f. `SET lock_timeout = '0'`  (reset for the rest of the session).

   Each statement on its own `op.execute()` call. Add a brief inline comment
   above the two ALTER TABLEs noting they rewrite the table once and backfill
   automatically.

4. `downgrade()` body — reverse order:
   - `DROP INDEX IF EXISTS doc_chunks_tsv_en_idx`
   - `DROP INDEX IF EXISTS doc_chunks_tsv_fr_idx`
   - `ALTER TABLE doc_chunks DROP COLUMN IF EXISTS content_tsv_en`
   - `ALTER TABLE doc_chunks DROP COLUMN IF EXISTS content_tsv_fr`

Do NOT use CREATE INDEX CONCURRENTLY — Alembic wraps the upgrade in a transaction
and CIC is not transactional. The accepted tradeoff at ~5000 rows (per RESEARCH
§3.E option (a)) is a ~1 second blocking CREATE INDEX.

Do NOT touch `embedding`, `embedding_dim`, the ivfflat index, or any other
column. This migration is additive only.
  </action>
  <verify>
    <automated>cd C:/Users/Admin/Downloads/EAM/EAMSagemCom &amp;&amp; python -c "import ast,sys; tree=ast.parse(open('app/backend/alembic/versions/hybrid_search_tsvector.py').read()); src=open('app/backend/alembic/versions/hybrid_search_tsvector.py').read(); assert 'down_revision = \"chat_sessions_multi\"' in src, 'wrong down_revision'; assert 'revision = \"hybrid_search_tsvector\"' in src, 'wrong revision id'; assert 'content_tsv_fr' in src and 'content_tsv_en' in src, 'missing tsvector cols'; assert 'GIN' in src.upper(), 'missing GIN index'; assert \"to_tsvector('french'\" in src and \"to_tsvector('english'\" in src, 'missing FTS configs'; assert 'GENERATED ALWAYS AS' in src.upper(), 'missing GENERATED clause'; assert 'lock_timeout' in src, 'missing lock_timeout safety'; assert 'def upgrade' in src and 'def downgrade' in src, 'missing up/down'; print('OK')"</automated>
  </verify>
  <done>
File `app/backend/alembic/versions/hybrid_search_tsvector.py` exists. It declares
`revision = "hybrid_search_tsvector"` and `down_revision = "chat_sessions_multi"`.
It contains both ALTER TABLE … ADD COLUMN GENERATED statements (french + english),
both CREATE INDEX … USING GIN statements, a `SET lock_timeout = '30s'` guard,
and a symmetric downgrade. No CREATE INDEX CONCURRENTLY anywhere.
  </done>
</task>

<task type="auto">
  <name>Task 2: Apply migration in dev DB and verify schema + indexes are live</name>
  <files>(no source code changes — runtime verification only)</files>
  <action>
Apply the migration against the dev Postgres in Docker and prove the schema and
indexes are real (not just the file).

Steps (run from project root):

1. Ensure stack is up: `docker compose ps postgres` shows running. If not, run
   `make up` and wait for postgres healthcheck.

2. Apply the migration inside the backend container (this is where alembic
   tooling lives):
   ```
   docker compose exec backend alembic upgrade head
   ```
   Confirm in stdout that the new revision `hybrid_search_tsvector` is reported
   as applied. If the command errors out with a "lock_timeout" or "could not
   acquire lock", retry once during a quieter moment (no chat traffic).

3. Verify schema via `make db` (or `docker compose exec postgres psql -U …`):
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name='doc_chunks'
     AND column_name IN ('content_tsv_fr','content_tsv_en');
   ```
   Expected: 2 rows, both `tsvector`.

4. Verify GIN indexes:
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename='doc_chunks'
     AND indexname IN ('doc_chunks_tsv_fr_idx','doc_chunks_tsv_en_idx');
   ```
   Expected: 2 rows, both `USING gin`.

5. Verify backfill happened — every existing chunk has a non-null tsvector:
   ```sql
   SELECT
     COUNT(*) AS total,
     COUNT(content_tsv_fr) AS fr_populated,
     COUNT(content_tsv_en) AS en_populated
   FROM doc_chunks;
   ```
   Expected: `fr_populated == total` and `en_populated == total`.

6. Verify the GIN indexes are actually used by the planner. Pick a token known
   to exist in the corpus (per RESEARCH §10, `OT-SEED-C49-M20` is a safe bet
   after M13 seeding; if no seed has been run yet, pick any word from
   `SELECT content FROM doc_chunks LIMIT 1`):
   ```sql
   EXPLAIN
   SELECT id, ts_rank_cd(content_tsv_en, websearch_to_tsquery('english','OT-SEED-C49-M20')) AS r
   FROM doc_chunks
   WHERE content_tsv_en @@ websearch_to_tsquery('english','OT-SEED-C49-M20')
   ORDER BY r DESC LIMIT 30;
   ```
   Expected: plan shows `Bitmap Index Scan on doc_chunks_tsv_en_idx` (or a
   BitmapOr including it). If it shows `Seq Scan on doc_chunks` AND the table
   has ≥1000 rows, that is a failure — run `ANALYZE doc_chunks` and retry; if
   still seq scan, escalate.

Record the EXPLAIN output and the three SELECT results in the plan summary.
  </action>
  <verify>
    <automated>docker compose exec -T postgres psql -U postgres -d eam -tA -c "SELECT (SELECT COUNT(*) FROM information_schema.columns WHERE table_name='doc_chunks' AND column_name IN ('content_tsv_fr','content_tsv_en'))::int AS cols, (SELECT COUNT(*) FROM pg_indexes WHERE tablename='doc_chunks' AND indexname IN ('doc_chunks_tsv_fr_idx','doc_chunks_tsv_en_idx'))::int AS idx, (SELECT COUNT(*) FROM doc_chunks WHERE content_tsv_fr IS NULL OR content_tsv_en IS NULL)::int AS null_rows" | awk -F'|' 'NR==1 { if ($1==2 &amp;&amp; $2==2 &amp;&amp; $3==0) print "OK"; else { print "FAIL cols="$1" idx="$2" null_rows="$3; exit 1 } }'</automated>
  </verify>
  <done>
`alembic upgrade head` succeeded. `information_schema.columns` shows both
tsvector columns. `pg_indexes` shows both GIN indexes. Zero `doc_chunks` rows
have a NULL `content_tsv_fr` or `content_tsv_en`. EXPLAIN on a real-token query
shows a Bitmap Index Scan on one of the new GIN indexes (not a Seq Scan on
doc_chunks).
  </done>
</task>

</tasks>

<verification>
- Migration file is committed and present at `app/backend/alembic/versions/hybrid_search_tsvector.py`.
- `down_revision = "chat_sessions_multi"`; revision id is `hybrid_search_tsvector`.
- Both GENERATED columns and both GIN indexes exist on `doc_chunks` in the dev DB.
- Backfill is complete (every existing row has populated tsvectors — Postgres
  does this for free on ADD COLUMN GENERATED).
- `EXPLAIN` confirms the planner picks the GIN index for the keyword `@@` query.
- `alembic downgrade -1` (smoke-tested locally, not committed in CI) cleanly
  removes the columns and indexes.
</verification>

<success_criteria>
- File `app/backend/alembic/versions/hybrid_search_tsvector.py` exists with the
  exact revision id, down_revision, both ALTER TABLE statements, both CREATE
  INDEX statements, and a symmetric `downgrade()`.
- After `alembic upgrade head`: `doc_chunks` has `content_tsv_fr` and
  `content_tsv_en` (both `tsvector`, both populated for every row), and
  `pg_indexes` lists `doc_chunks_tsv_fr_idx` and `doc_chunks_tsv_en_idx` (both
  `USING gin`).
- EXPLAIN of a `websearch_to_tsquery` query against either tsvector column shows
  a Bitmap Index Scan on the corresponding GIN index.
- No regression: existing `documents` listing, `/ingest`, `/retrieve`, and the
  ivfflat embedding index are unchanged.
</success_criteria>

<output>
After completion, create
`.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-01-migration-tsvector-gin-SUMMARY.md`
with:
- Revision id + down_revision actually written.
- `alembic upgrade head` stdout snippet showing the revision applied.
- The three psql SELECT outputs (column listing, index listing, NULL count).
- The EXPLAIN output showing a Bitmap Index Scan on the new GIN index.
- Row count at migration time (so 13-03 smoke tests can reason about scale).
- Any deviations from this plan and why.
</output>
</output>
