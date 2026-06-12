---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
plan: 02
type: execute
wave: 2
depends_on:
  - "13-01"
files_modified:
  - app/rag-service/hybrid.py
  - app/rag-service/retriever.py
  - app/rag-service/main.py
  - app/rag-service/requirements.txt
  - docker-compose.yml
  - .env.example
autonomous: true
requirements:
  - HYB-02
  - HYB-03
  - HYB-04
  - HYB-05
  - HYB-06
  - HYB-07
  - HYB-08
  - HYB-10
  - HYB-11
must_haves:
  truths:
    - "A new module app/rag-service/hybrid.py exports hybrid_enabled(), keyword_search(), rrf_fuse(), hybrid_stats() and per-query stats counters"
    - "retriever.retrieve_chunks() fans out a vector top-30 and a keyword top-30 in parallel when HYBRID_ENABLED is true, then fuses via RRF (k=60), trims to 30, and forwards to the existing reranker"
    - "The vector branch SQL at retriever.py:88-97 is reused verbatim (no functional change) when hybrid is on"
    - "Retrieval cache key includes hybrid_enabled so toggling does not return stale results"
    - "When HYBRID_ENABLED is false, retriever.retrieve_chunks() behaves byte-identically to the pre-13 vector-only path"
    - "BM25 SQL errors propagate as a 500 (fail loud) — no silent vector-only fallback"
    - "GET /hybrid-info returns {enabled, fusion:'rrf', k:60, overfetch:30, fts_configs:['french','english'], tie_break:'vector_similarity_desc'}"
    - "GET /cache-stats includes a hybrid block with searches, vector_only_count, keyword_only_count, both_count, keyword_zero_hits, vector_zero_hits counters"
    - "Per-query INFO log line documents vector_hits, keyword_hits, fused count, returned count, and source_mix"
    - "docker-compose.yml exposes HYBRID_ENABLED with default true, immediately below RERANK_ENABLED; .env.example has a matching HYBRID_ENABLED= line"
  artifacts:
    - path: "app/rag-service/hybrid.py"
      provides: "hybrid_enabled, keyword_search, rrf_fuse, hybrid_stats, record_call, HYBRID_OVERFETCH, HYBRID_RRF_K, FTS_CONFIGS, TIE_BREAK"
      exports: ["hybrid_enabled", "keyword_search", "rrf_fuse", "hybrid_stats", "record_call", "HYBRID_OVERFETCH", "HYBRID_RRF_K", "FTS_CONFIGS", "TIE_BREAK"]
      min_lines: 120
    - path: "app/rag-service/retriever.py"
      provides: "retrieve_chunks() with fan-out + RRF + reranker handoff"
      contains: "hybrid_enabled"
    - path: "app/rag-service/main.py"
      provides: "/cache-stats with hybrid block + new /hybrid-info endpoint"
      contains: "hybrid_stats"
    - path: "docker-compose.yml"
      provides: "HYBRID_ENABLED env wired into rag-service"
      contains: "HYBRID_ENABLED"
    - path: ".env.example"
      provides: "HYBRID_ENABLED placeholder"
      contains: "HYBRID_ENABLED"
  key_links:
    - from: "retriever.retrieve_chunks"
      to: "hybrid.keyword_search"
      via: "await call inside hybrid branch"
      pattern: "keyword_search\\("
    - from: "retriever.retrieve_chunks"
      to: "hybrid.rrf_fuse"
      via: "Python list fusion before reranker handoff"
      pattern: "rrf_fuse\\("
    - from: "retriever.retrieve_chunks cache_key"
      to: "hybrid.hybrid_enabled"
      via: "tuple element 5"
      pattern: "cache_key\\s*=\\s*\\(.*hybrid"
    - from: "main.cache_stats"
      to: "hybrid.hybrid_stats"
      via: "JSON 'hybrid' block"
      pattern: "['\"]hybrid['\"]\\s*:\\s*hybrid_stats\\(\\)"
    - from: "main./hybrid-info endpoint"
      to: "hybrid module constants"
      via: "FastAPI route returning {enabled, fusion, k, overfetch, fts_configs, tie_break}"
      pattern: "@app\\.get\\(\\s*[\"']/hybrid-info[\"']"
    - from: "docker-compose.yml rag-service env"
      to: ".env.example"
      via: "HYBRID_ENABLED with default true"
      pattern: "HYBRID_ENABLED:\\s*\\$\\{HYBRID_ENABLED:-true\\}"
---

<objective>
Implement the hybrid retrieval path in `rag-service`:
1. New `hybrid.py` housing the RRF helper, the keyword SQL branch, the env-flag
   toggle, the per-call stats counters, and the constants (`HYBRID_RRF_K=60`,
   `HYBRID_OVERFETCH=30`).
2. Refactor `retriever.retrieve_chunks()` to run vector top-30 and keyword
   top-30 concurrently, fuse via RRF, trim to 30, and forward the fused list to
   the existing reranker. Vector-only path preserved when `HYBRID_ENABLED=false`.
3. Wire `/cache-stats` to include a `hybrid` block and add a new `GET
   /hybrid-info` endpoint.
4. Add `HYBRID_ENABLED` to `docker-compose.yml` and `.env.example`.

Purpose: Phase 13.1 hybrid search is locked to Postgres native FTS + Python-side
RRF. This is the code change that turns the schema added in Plan 13-01 into a
behavior change for `/retrieve` (and therefore for the chat backend).

Output: Exact-ID queries (e.g. `OT-SEED-C49-M20`) start ranking the matching
chunk first; natural-language queries continue to be served by the vector
branch and remain at least as good as the baseline.
</objective>

<execution_context>
@C:/Users/Admin/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Admin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-CONTEXT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-RESEARCH.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-01-migration-tsvector-gin-SUMMARY.md

@app/rag-service/retriever.py
@app/rag-service/reranker.py
@app/rag-service/main.py
@app/rag-service/embedder.py

<interfaces>
<!-- Live contracts extracted from the rag-service code on disk. Use directly. -->

Reranker contract (`app/rag-service/reranker.py:60-97`):
```python
async def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Reads c['content']; preserves all other fields; writes c['rerank_score'];
    sorts by rerank_score desc; trims to top_k. Empty in -> empty out."""
```
Adding `chunk_id`, `fused_score`, `vector_rank`, `keyword_rank`, `ts_rank_cd` to
candidate dicts is safe — the reranker only reads `content` (per RESEARCH.md §7)
and passes every other field through unchanged.

Current retriever cache key (`app/rag-service/retriever.py:71`) — to be widened:
```python
cache_key = (query.strip(), machine_id, top_k, round(threshold, 4))
```

Current vector branch SQL (`app/rag-service/retriever.py:88-97`) — must be reused
verbatim as the vector side of the fan-out. Do NOT rewrite it.

Embedder contract (`app/rag-service/embedder.py`):
```python
async def embed_text(query: str) -> list[float]   # 1024-d
def vec_to_str(vec: list[float]) -> str           # for pgvector cast
```

Existing toggle pattern (`app/rag-service/reranker.py:36-38`):
```python
def rerank_enabled() -> bool:
    return os.getenv("RERANK_ENABLED", "true").strip().lower() in ("1","true","yes","on")
```

Existing stats pattern (`app/rag-service/reranker.py:107-118`):
```python
def rerank_stats() -> dict:
    return { "enabled": ..., "model": ..., "overfetch": ..., "reranks": ..., ... }
```

`/cache-stats` and `/rerank-info` shape (`app/rag-service/main.py:301-318`):
```python
@app.get("/cache-stats")
async def cache_stats():
    return {
        "embedding_cache": embed_cache_stats(),
        "retrieval_cache": retrieve_cache_stats(),
        "reranker": rerank_stats(),
    }

@app.get("/rerank-info")
async def rerank_info():
    return {"enabled": rerank_enabled(), "model": RERANK_MODEL, "overfetch": OVERFETCH}
```

docker-compose anchor (`docker-compose.yml:235`):
```
RERANK_ENABLED: ${RERANK_ENABLED:-true}
```
.env.example anchor (line 33): `RERANK_ENABLED=`

Locked keyword SQL shape (from RESEARCH §5 — use exactly this CTE; note the
`dc.id AS chunk_id` projection is required for the dedup key used by `rrf_fuse`):
```sql
WITH ranked AS (
  SELECT dc.id AS chunk_id, dc.content, dc.metadata,
         ts_rank_cd(dc.content_tsv_fr, websearch_to_tsquery('french',  :q)) AS rank_fr,
         ts_rank_cd(dc.content_tsv_en, websearch_to_tsquery('english', :q)) AS rank_en
  FROM doc_chunks dc
  JOIN documents d ON dc.doc_id = d.id
  WHERE (CAST(:machine_id AS integer) IS NULL OR d.machine_id = CAST(:machine_id AS integer))
    AND (
      dc.content_tsv_fr @@ websearch_to_tsquery('french',  :q)
      OR dc.content_tsv_en @@ websearch_to_tsquery('english', :q)
    )
)
SELECT chunk_id, content, metadata,
       GREATEST(rank_fr, rank_en) AS keyword_score
FROM ranked
WHERE GREATEST(rank_fr, rank_en) > 0.0
ORDER BY keyword_score DESC
LIMIT :top_k;
```

RRF (locked, from CONTEXT and RESEARCH §4):
- k = 60
- fused_score = Σ 1/(k + rank_in_list)
- tie-break: (fused_score DESC, similarity DESC), missing similarity → 0.0
- limit after fusion = 30 (HYBRID_OVERFETCH)
- dedup key: `chunk_id` (stable PK from doc_chunks; safer than content hashing)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create app/rag-service/hybrid.py — RRF + keyword SQL + env toggle + stats + RRF unit test</name>
  <files>app/rag-service/hybrid.py, app/rag-service/tests/test_hybrid_rrf.py</files>
  <behavior>
    - rrf_fuse(): given the worked example from RESEARCH §4 (vector list A,B,C,D and keyword list C,E,A,F, each entry carrying its own chunk_id), returns exactly the 6 chunks sorted as [A (fused=0.03227, sim=0.82), C (fused=0.03227, sim=0.71), B (fused=0.01613, sim=0.79), E (fused=0.01613, sim=0.0), D (fused=0.01563, sim=0.68), F (fused=0.01563, sim=0.0)].
    - rrf_fuse(): tie-break sorts keyword-only entries below vector entries at equal fused score because missing similarity is treated as 0.0.
    - rrf_fuse([], []) returns [].
    - rrf_fuse(only_vector, []) returns the vector list with vector_rank set 1..N and fused_score set to 1/(k+rank); no errors.
    - rrf_fuse([], only_keyword) returns the keyword list with similarity defaulted to 0.0 on every entry.
    - rrf_fuse() with limit=2 returns exactly the top 2 entries.
    - rrf_fuse(): when the same chunk_id appears in both lists with different `content` strings (shouldn't happen in prod, but tested for safety), the dedup picks the first-seen entry by chunk_id — the function does NOT key on content.
    - hybrid_enabled(): returns True when env unset (default); False on "false"/"0"/"no"/"off"; True on "1"/"true"/"yes"/"on" (case-insensitive). Mirrors rerank_enabled().
    - HYBRID_RRF_K == 60 and HYBRID_OVERFETCH == 30.
  </behavior>
  <action>
Create `app/rag-service/hybrid.py` with the following structure (full code, not
a sketch):

1. **Module docstring** stating: "Phase 13.1 hybrid retrieval: keyword
   (Postgres FTS via two GENERATED tsvector columns on doc_chunks) + vector
   (existing pgvector cosine), fused via Reciprocal Rank Fusion (k=60). Stage A
   each side returns 30 candidates; Stage B fuses to ≤30 unique candidates;
   Stage C is the existing cross-encoder reranker (unchanged). Fail-loud on BM25
   errors — no silent vector-only fallback (per CONTEXT.md)."

2. **Constants** (module-level):
   ```python
   HYBRID_RRF_K = 60
   HYBRID_OVERFETCH = 30
   FTS_CONFIGS = ("french", "english")
   TIE_BREAK = "vector_similarity_desc"
   ```

3. **Env-flag toggle** — mirror reranker.py:36-38 exactly:
   ```python
   def hybrid_enabled() -> bool:
       return os.getenv("HYBRID_ENABLED", "true").strip().lower() in ("1","true","yes","on")
   ```

4. **Module-level counters** (mirror reranker stats shape):
   ```python
   _searches = 0
   _vector_only_count = 0
   _keyword_only_count = 0
   _both_count = 0
   _keyword_zero_hits = 0
   _vector_zero_hits = 0
   ```
   Plus a `record_call(vector_n, keyword_n, returned_with_source)` helper that
   atomically updates these counters from `retriever.retrieve_chunks()` after
   the reranker returns. `returned_with_source` is a list of "both" /
   "vector_only" / "keyword_only" strings, one per chunk in the FINAL returned
   list (post-rerank, post-trim-to-top_k).

   `record_call(vector_n, keyword_n, returned_with_source)` increments
   `_keyword_zero_hits` when `keyword_n == 0` and `_vector_zero_hits` when
   `vector_n == 0`. It also increments `_searches` by 1 and accumulates the
   per-chunk source classifications into `_vector_only_count`,
   `_keyword_only_count`, and `_both_count` by counting the matching strings in
   `returned_with_source`.

5. **`hybrid_stats()`**:
   ```python
   def hybrid_stats() -> dict:
       return {
           "enabled": hybrid_enabled(),
           "fusion": "rrf",
           "k": HYBRID_RRF_K,
           "overfetch": HYBRID_OVERFETCH,
           "fts_configs": list(FTS_CONFIGS),
           "searches": _searches,
           "vector_only_count": _vector_only_count,
           "keyword_only_count": _keyword_only_count,
           "both_count": _both_count,
           "keyword_zero_hits": _keyword_zero_hits,
           "vector_zero_hits": _vector_zero_hits,
       }
   ```

6. **`async def keyword_search(query, db, machine_id, top_k=HYBRID_OVERFETCH)`**:
   Execute the locked CTE SQL (see <interfaces> block above) with bound params
   `{q: query.strip(), machine_id: machine_id, top_k: top_k}`. Return a
   `list[dict]` with keys `{chunk_id, content, metadata, ts_rank_cd}` — DO NOT
   wrap in try/except (fail loud is the locked behavior). `chunk_id` is the
   `doc_chunks.id` value projected by the CTE — it propagates to `rrf_fuse()`
   for dedup. The CTE filter `GREATEST(rank_fr, rank_en) > 0.0` is the only gate
   (no similarity threshold on the keyword side, per CONTEXT.md). Sort by
   `keyword_score DESC` is done by the SQL.

7. **`rrf_fuse(vector_hits, keyword_hits, k=HYBRID_RRF_K, limit=HYBRID_OVERFETCH)`**:
   Pure-Python implementation following the sketch in RESEARCH §4 exactly:
   - Dedupe across the two lists by `h["chunk_id"]` (the stable doc_chunks PK).
     Both vector_hits and keyword_hits MUST carry a `chunk_id` field — the
     vector branch SQL in Task 2 is updated to project it, and `keyword_search`
     already returns it. Using `chunk_id` (not `content`) avoids false dedup
     misses when two chunks have identical leading text and ensures consistency
     with the SQL primary key.
   - For each list, iterate 1-based ranks, accumulate `fused_score +=
     1/(k+rank)`, and stamp `vector_rank` / `keyword_rank` accordingly.
   - For chunks that appear only on the keyword side, `setdefault("similarity",
     0.0)` so the tie-break key is well-defined.
   - For chunks that appear on the vector side, preserve the existing
     `similarity` value.
   - Sort by `(fused_score DESC, similarity DESC)`. Python's sort is stable so
     order within ties is deterministic.
   - Slice to `limit` and return.
   - Empty inputs → return `[]`.
   - Each output dict still carries `content` so the reranker contract is
     satisfied unchanged (`chunk_id`, `fused_score`, `vector_rank`,
     `keyword_rank`, `ts_rank_cd` are passthrough fields the reranker ignores).

8. **No I/O in module init**, no model loading, no SQL at import time. The only
   thing that touches the DB is `keyword_search()`.

9. **Imports**: `os`, `logging`, `from sqlalchemy import text`, `from
   sqlalchemy.ext.asyncio import AsyncSession`. Do NOT import from
   `retriever.py` (avoid a future circular import — retriever imports from
   hybrid, not the other way around).

Also create `app/rag-service/tests/test_hybrid_rrf.py` with the pytest cases
listed in <behavior>. Use a fixed numerical comparison `pytest.approx(...,
abs=1e-4)` for the floating-point fused scores. The test file should NOT touch
the DB — it only exercises `rrf_fuse()` and `hybrid_enabled()` with
`monkeypatch.setenv`. Test fixtures MUST include a `chunk_id` field on every
entry (e.g. `{"chunk_id": "A", "content": "...", "similarity": 0.82}`).

Run the tests inside the rag-service container (Docker is the canonical env per
CLAUDE.md). The test file must live at `app/rag-service/tests/test_hybrid_rrf.py`
so it is reachable from the rag-service container's working directory.
  </action>
  <verify>
    <automated>docker compose run --rm rag-service pytest -x tests/test_hybrid_rrf.py</automated>
  </verify>
  <done>
`app/rag-service/hybrid.py` exists and exports `hybrid_enabled`,
`keyword_search`, `rrf_fuse`, `hybrid_stats`, `record_call`, `HYBRID_RRF_K`,
`HYBRID_OVERFETCH`, `FTS_CONFIGS`, `TIE_BREAK`. RRF unit test passes inside the
rag-service container (worked example from RESEARCH §4 matches expected sort
order with correct tie-break; dedup keys off `chunk_id`).
`hybrid_enabled()` honors the env var with the same truthy set as
`rerank_enabled()`. No imports from `retriever.py`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Refactor retriever.retrieve_chunks() to fan-out → RRF → reranker, with cache key widening, fail-loud BM25, INFO log, and stats wiring</name>
  <files>app/rag-service/retriever.py, app/rag-service/tests/test_retriever_hybrid_toggle.py, app/rag-service/requirements.txt</files>
  <behavior>
    - When HYBRID_ENABLED=false (monkeypatched), retrieve_chunks() takes only the vector path; cache key tuple has 5 elements with the last one being False; behavior is byte-identical to the pre-13 implementation (same returned chunks for the same query, machine_id, top_k, threshold).
    - When HYBRID_ENABLED=true (default), retrieve_chunks() calls embedder once, runs vector branch with overfetch=HYBRID_OVERFETCH (30), calls hybrid.keyword_search() with top_k=HYBRID_OVERFETCH (30), calls rrf_fuse() with k=60 and limit=30, then forwards the result to rerank() with top_k=request.top_k.
    - Cache key tuple is (query.strip(), machine_id, top_k, round(threshold,4), hybrid_enabled()) — exactly 5 elements; toggling HYBRID_ENABLED produces a different cache key for the same other inputs.
    - When the BM25 SQL raises (simulated by monkeypatching hybrid.keyword_search to raise), retrieve_chunks() re-raises (no silent fallback to vector-only).
    - When the embedding service raises in the vector branch, behavior is unchanged: returns [] (consistent with retriever.py:81-83 pre-13 behavior).
    - When candidates is empty after fusion (both branches returned 0 rows), retrieve_chunks() returns [] without calling rerank().
    - Vector branch SQL now projects `dc.id AS chunk_id` so RRF dedup keys are stable; the SELECT shape that flows into `candidates` becomes `{chunk_id, content, metadata, similarity}`.
  </behavior>
  <action>
Modify `app/rag-service/retriever.py` in place. Keep the docstring updated to
mention the hybrid path.

Changes:

1. **Imports** — add:
   ```python
   import asyncio
   from hybrid import (
       hybrid_enabled, keyword_search, rrf_fuse, record_call,
       HYBRID_OVERFETCH, HYBRID_RRF_K,
   )
   ```

2. **Cache key** at retriever.py:71 — widen to 5-tuple atomically with the
   behavior change:
   ```python
   hybrid_on = hybrid_enabled()
   cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)
   ```

3. **Vector branch** — keep the existing SQL at lines 88-97 verbatim EXCEPT
   add `dc.id AS chunk_id` to the SELECT list so the chunk PK reaches Python:
   ```sql
   SELECT dc.id AS chunk_id, dc.content, dc.metadata,
          1 - (dc.embedding <=> CAST(:vec AS vector)) AS similarity
   FROM doc_chunks dc
   JOIN documents d ON dc.doc_id = d.id
   WHERE (CAST(:machine_id AS integer) IS NULL OR d.machine_id = CAST(:machine_id AS integer))
     AND 1 - (dc.embedding <=> CAST(:vec AS vector)) > :threshold
   ORDER BY dc.embedding <=> CAST(:vec AS vector)
   LIMIT :top_k
   ```
   And update the candidate dict comprehension to read `chunk_id`:
   ```python
   candidates = [
       {"chunk_id": r.chunk_id, "content": r.content,
        "metadata": r.metadata, "similarity": float(r.similarity)}
       for r in rows
   ]
   ```
   Change only the `overfetch` value when hybrid is on:
   ```python
   overfetch = HYBRID_OVERFETCH if hybrid_on else compute_overfetch(top_k)
   ```
   The existing try/except around the vector branch keeps its current behavior
   of returning `[]` on embedding/SQL failure when hybrid_on is False. When
   hybrid_on is True we still let an embedding failure produce an empty vector
   list, but the keyword branch may still find matches — see step 4.

4. **Keyword branch** (only when `hybrid_on`):
   ```python
   if hybrid_on:
       try:
           keyword_hits = await keyword_search(query.strip(), db, machine_id, top_k=HYBRID_OVERFETCH)
       except Exception as e:
           logger.error(f"BM25 keyword branch failed: {e}", exc_info=True)
           raise  # fail loud per CONTEXT.md — no silent fallback
   else:
       keyword_hits = []
   ```
   Place this AFTER the vector branch so vector failures don't mask BM25
   failures. Do NOT wrap in `try: return []` — the `raise` is intentional.

5. **Fusion**:
   ```python
   if hybrid_on:
       fused = rrf_fuse(candidates, keyword_hits, k=HYBRID_RRF_K, limit=HYBRID_OVERFETCH)
   else:
       fused = candidates  # vector-only legacy path
   ```

6. **Reranker handoff** — unchanged shape:
   ```python
   if rerank_enabled() and fused:
       results = await rerank(query.strip(), fused, top_k)
   else:
       results = fused[:top_k]
   ```

7. **Source attribution + stats + INFO log** (only when `hybrid_on`):
   After `results` is finalized, classify each returned chunk by whether it
   had `vector_rank`, `keyword_rank`, or both:
   ```python
   if hybrid_on:
       source_mix = []
       for c in results:
           has_v = "vector_rank" in c
           has_k = "keyword_rank" in c
           source_mix.append("both" if has_v and has_k else ("vector_only" if has_v else "keyword_only"))
       record_call(
           vector_n=len(candidates),
           keyword_n=len(keyword_hits),
           returned_with_source=source_mix,
       )
       logger.info(
           "hybrid query=%r machine_id=%s vector_hits=%d keyword_hits=%d fused=%d returned=%d source_mix=(both:%d, vector_only:%d, keyword_only:%d)",
           query.strip()[:80], machine_id, len(candidates), len(keyword_hits),
           len(fused), len(results),
           source_mix.count("both"), source_mix.count("vector_only"), source_mix.count("keyword_only"),
       )
   ```

8. **Cache store** — unchanged shape, but uses the widened key.

9. **Strip internal hybrid fields from cached values?** No — keep them on the
   in-memory list. The Pydantic `ChunkResult` model in `main.py` already
   filters to `{content, metadata, similarity}` on serialization, so the
   `/retrieve` response shape does NOT change. Internal counters and INFO logs
   benefit from the extra fields staying around. `chunk_id` is also filtered
   out at the Pydantic boundary — no API surface change.

Also create `app/rag-service/tests/test_retriever_hybrid_toggle.py` covering
the <behavior> cases. Use `pytest-asyncio` (already a test dep in the
rag-service container — verify with `docker compose run --rm rag-service pip
show pytest-asyncio`; if missing, add `pytest-asyncio` to
`app/rag-service/requirements.txt` and document the addition in the SUMMARY).
The file `app/rag-service/requirements.txt` is listed in `files_modified:` as a
contingent edit — only touch it if pytest-asyncio is missing from the image.
Mock the DB via a fake `db.execute` that returns fixture rows (each row MUST
include a `chunk_id` attribute); mock `embed_text` and `keyword_search` with
`monkeypatch`. Do NOT hit the real Postgres in these tests — that's covered by
the smoke tests in Plan 13-03.
  </action>
  <verify>
    <automated>docker compose run --rm rag-service pytest -x tests/test_retriever_hybrid_toggle.py</automated>
  </verify>
  <done>
`retrieve_chunks()` cache key is a 5-tuple ending in `hybrid_enabled()`. Vector
branch SQL is unchanged except for the additive `dc.id AS chunk_id` projection;
candidate dicts now carry `chunk_id`. When `HYBRID_ENABLED=true`, both branches
run, RRF fuses by `chunk_id` with k=60 and limit=30, results go through the
existing reranker, and a single INFO log line per call reports source mix. BM25
SQL errors propagate (verified by test). When `HYBRID_ENABLED=false`, behavior
is byte-identical to the pre-13 path (also verified by test). Stats counters
increment correctly.
  </done>
</task>

<task type="auto">
  <name>Task 3: Wire /cache-stats hybrid block + /hybrid-info endpoint + HYBRID_ENABLED in docker-compose + .env.example</name>
  <files>app/rag-service/main.py, docker-compose.yml, .env.example</files>
  <action>
1. **`app/rag-service/main.py`** — extend `/cache-stats` and add `/hybrid-info`:

   - Add import near the existing reranker import:
     ```python
     from hybrid import hybrid_stats, hybrid_enabled, HYBRID_RRF_K, HYBRID_OVERFETCH, FTS_CONFIGS, TIE_BREAK
     ```
   - In the existing `cache_stats()` function (currently lines 301-308), add a
     `"hybrid": hybrid_stats()` entry at the end of the returned dict.
     Preserve key order: `embedding_cache`, `retrieval_cache`, `reranker`,
     `hybrid`.
   - Immediately after the existing `rerank_info()` route (line 318), add:
     ```python
     @app.get("/hybrid-info")
     async def hybrid_info():
         """Hybrid retrieval status for ops visibility."""
         return {
             "enabled": hybrid_enabled(),
             "fusion": "rrf",
             "k": HYBRID_RRF_K,
             "overfetch": HYBRID_OVERFETCH,
             "fts_configs": list(FTS_CONFIGS),
             "tie_break": TIE_BREAK,
         }
     ```

2. **`docker-compose.yml`** — at the rag-service `environment:` block,
   immediately below the existing line:
   ```yaml
   RERANK_ENABLED: ${RERANK_ENABLED:-true}
   ```
   add:
   ```yaml
   HYBRID_ENABLED: ${HYBRID_ENABLED:-true}
   ```
   No other compose changes.

3. **`.env.example`** — immediately below the existing `RERANK_ENABLED=` line
   (currently line 33), add:
   ```
   HYBRID_ENABLED=
   ```

4. **Restart the rag-service container** so the new env + code take effect:
   ```
   docker compose up -d --build rag-service
   ```
   Wait for `docker compose logs --tail=20 rag-service` to show the service
   listening on its port.

5. **Spot-check the two endpoints** (record outputs in the plan summary):
   ```bash
   curl -s http://localhost:8003/hybrid-info | jq .
   curl -s http://localhost:8003/cache-stats | jq .hybrid
   ```
   The first must return all 6 keys (`enabled`, `fusion`, `k`, `overfetch`,
   `fts_configs`, `tie_break`). The second must return the `hybrid` block with
   counters starting at 0.
  </action>
  <verify>
    <automated>curl -sf http://localhost:8003/hybrid-info | python -c "import sys, json; d=json.load(sys.stdin); assert d['enabled'] is True and d['fusion']=='rrf' and d['k']==60 and d['overfetch']==30 and d['fts_configs']==['french','english'] and d['tie_break']=='vector_similarity_desc', d; print('hybrid-info OK')" &amp;&amp; curl -sf http://localhost:8003/cache-stats | python -c "import sys, json; d=json.load(sys.stdin); h=d['hybrid']; assert h['enabled'] is True and h['fusion']=='rrf' and h['k']==60 and h['overfetch']==30 and 'searches' in h and 'vector_only_count' in h and 'keyword_only_count' in h and 'both_count' in h, h; print('cache-stats.hybrid OK')"</automated>
  </verify>
  <done>
`/hybrid-info` returns the documented JSON with `enabled=true`, `fusion='rrf'`,
`k=60`, `overfetch=30`, `fts_configs=['french','english']`, and
`tie_break='vector_similarity_desc'`. `/cache-stats` includes a `hybrid` block
with all six counters plus the four config keys. `docker-compose.yml` exposes
`HYBRID_ENABLED` with default `true` directly below `RERANK_ENABLED`. `.env.example`
has a matching `HYBRID_ENABLED=` line.
  </done>
</task>

</tasks>

<verification>
- All three task `<automated>` commands pass.
- `app/rag-service/hybrid.py` exists with the documented exports and constants.
- `app/rag-service/retriever.py` cache key is widened; vector SQL untouched
  except for additive `dc.id AS chunk_id` projection; BM25 errors propagate;
  INFO log line per call.
- `/cache-stats` and `/hybrid-info` return the documented shapes.
- `docker-compose.yml` and `.env.example` carry `HYBRID_ENABLED`.
- No changes to `app/backend/services/rag_client.py`,
  `app/backend/modules/shared/routes/chat.py`, `app/rag-service/ingestor.py`,
  or any frontend file (per CONTEXT.md).
</verification>

<success_criteria>
- Hybrid path is on by default and exact-ID queries (e.g. `OT-SEED-C49-M20`,
  given the M13 seed corpus is present) rank the matching chunk at position 1
  via `/retrieve`. (Full smoke test is Plan 13-03; this plan only requires the
  unit tests + a single live call to confirm wiring.)
- Toggling `HYBRID_ENABLED=false` and restarting the rag-service produces a
  different cache key and reverts behavior to vector-only. (Toggle-off
  verification is Plan 13-03.)
- `hybrid_stats()` counters increment as queries are issued; no zero-division
  or accumulation bugs.
- Reranker output shape (Pydantic `ChunkResult`) is unchanged from the
  caller's perspective — backend and frontend remain untouched.
</success_criteria>

<output>
After completion, create
`.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-02-hybrid-module-and-retriever-SUMMARY.md`
with:
- Final exports of `hybrid.py` (function signatures).
- Final `retrieve_chunks()` signature + the 5-tuple cache key line.
- `pytest` output for both new test files.
- `curl /hybrid-info` and `curl /cache-stats | jq .hybrid` JSON.
- Docker-compose diff for `HYBRID_ENABLED`.
- Any deviations from the locked SQL or the locked RRF behavior and why.
</output>
</output>
