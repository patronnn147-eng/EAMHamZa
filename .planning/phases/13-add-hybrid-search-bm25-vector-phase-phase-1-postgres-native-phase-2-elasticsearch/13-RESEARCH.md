# Phase 13: Hybrid Search (BM25 + Vector) — Research

**Researched:** 2026-06-06
**Domain:** Postgres FTS + pgvector hybrid retrieval, RRF fusion, async SQLAlchemy
**Confidence:** HIGH (locked by CONTEXT.md; external claims cross-verified with Postgres docs + RRF literature)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Phase split:** 13.1 (Postgres-native) ships first, alone. 13.2 (Elasticsearch) deferred — only triggered if 13.1 quality is insufficient. Do NOT pre-build ES.
- **BM25 engine:** Postgres native FTS via `tsvector` + `ts_rank_cd`. No new container, no new extension. pg_search (ParadeDB) explicitly rejected.
- **FTS language config:** Two GENERATED tsvector columns on `doc_chunks`:
  - `content_tsv_fr` using `french` config
  - `content_tsv_en` using `english` config
  - per-chunk rank = `GREATEST(rank_fr, rank_en)`. One GIN index per column.
  - Arabic deferred (vector still catches it).
- **tsvector population:** `GENERATED ALWAYS AS (to_tsvector(...)) STORED`. Zero changes to `ingestor.py`. Backfill is automatic.
- **Fusion:** Reciprocal Rank Fusion (RRF), `k=60` (BEIR-standard). Score per chunk = `Σ 1 / (k + rank_in_list)`. Score-free, no normalization between cosine and `ts_rank_cd`. Weighted-score fusion rejected.
- **Overfetch:** Stage A vector top-30 + keyword top-30 → Stage B RRF → up to 50 unique → trim 30 → Stage C cross-encoder rerank → top_k=8 to backend.
- **Threshold:** `similarity > 0.30` applies to vector side ONLY. Keyword side uses `ts_rank_cd > 0.0`.
- **Tie-break:** `(fused_score DESC, vector_similarity DESC)` — semantic wins ties.
- **Toggle + errors:** New env `HYBRID_ENABLED` (default `true`). Pattern mirrors `RERANK_ENABLED`. **Fail loud** on BM25 errors — 500 to caller. No silent vector-only fallback.
- **Cache:** Reuse `_retrieve_cache` (TTLCache 5 min). Key extended to `(query, machine_id, top_k, threshold, hybrid_enabled)`. Existing `clear_retrieval_cache()` covers hybrid path.
- **Observability:** Extend `/cache-stats` with `hybrid` block. New `GET /hybrid-info`. INFO logs per query indicating which source contributed each final chunk.
- **Migration:** New Alembic revision with down-revision `chat_sessions_multi` (current head). Add 2 generated columns + 2 GIN indexes.
- **Files modified:** NEW `app/backend/alembic/versions/hybrid_search_tsvector.py`, NEW `app/rag-service/hybrid.py`, MODIFY `retriever.py` + `main.py`. NO CHANGES to `ingestor.py`, backend `rag_client.py`, `routes/chat.py`, frontend.

### Claude's Discretion
- Exact SQL phrasing (CTE vs single SELECT vs two Python-fused queries).
- Counter naming inside `hybrid_stats()` — match `rerank_stats()` shape.
- `plainto_tsquery` vs `websearch_to_tsquery` — pick `websearch_to_tsquery` per CONTEXT.md hint.

### Deferred Ideas (OUT OF SCOPE)
- Elasticsearch container (Phase 13.2).
- Arabic FTS dictionary (Postgres has none).
- Weighted-score fusion + learned weights.
- Synonyms ("panne" ↔ "défaillance" ↔ "failure").
- Multi-field boost (`setweight()`).
- Phrase / proximity scoring beyond `websearch_to_tsquery` defaults.
- Fuzzy match (`pg_trgm`).
- Eval harness (precision@k, MRR).
</user_constraints>

<phase_requirements>
## Phase Requirements

No formal `REQ-` IDs were registered for this phase (REQUIREMENTS.md does not exist at the project root — STATE.md references only OPT-01..05 from Phase 1 of the optimization roadmap). The contract for Phase 13 is therefore the CONTEXT.md decisions list, treated as binding. Mapping below for the planner:

| Implicit ID | Behavior | Research Support |
|-------------|----------|-----------------|
| HYB-01 | Add two generated `tsvector` columns + GIN indexes on `doc_chunks` via Alembic | §3 (FTS findings) + §11 (migration safety) |
| HYB-02 | Fan out a vector top-30 and a keyword top-30 retrieval per query, both filtered by `machine_id` | §2 (current flow) + §5 (SQL recommendation) |
| HYB-03 | Fuse the two lists via RRF (k=60) and trim to 30 candidates | §4 (RRF) |
| HYB-04 | Sort ties by `(fused_score DESC, vector_similarity DESC)` and forward to existing reranker | §4 + §7 (reranker compatibility) |
| HYB-05 | Extend `_retrieve_cache` key with `hybrid_enabled`; reuse existing TTL + invalidation | §6 (cache) |
| HYB-06 | Add `HYBRID_ENABLED` env (default `true`) — mirror `RERANK_ENABLED` pattern; fail loud on BM25 errors | §8 (failure modes) |
| HYB-07 | Extend `/cache-stats` with `hybrid` block + new `GET /hybrid-info` endpoint | §9 (observability) |
| HYB-08 | Use `websearch_to_tsquery` for safe user-input handling | §3.A |
| HYB-09 | Confirm DB-synced corpus is searchable by ID via smoke-tests | §10 (smoke-test corpus) |
</phase_requirements>

---

## 1. Executive Summary

- **Stack is locked:** Postgres 15 (pgvector image) + native FTS via two GENERATED tsvector columns + two GIN indexes + Python-side RRF (k=60). No new container, no new extension, no new Python deps.
- **Single-CTE SQL recommended** (see §5) for the new keyword branch — one round-trip, the planner can hash-join `documents` once and pick the GIN scan per branch independently. The vector branch stays verbatim from `retriever.py:88–97`.
- **`websearch_to_tsquery` is the right call for user input** — it strips/escapes punctuation safely, so `OT-SEED-C49-M20` becomes a usable query rather than a syntax error (see §3.A for exact behavior with hyphens/colons).
- **RRF is one line of Python** (§4) — no library needed; we already have `cachetools` and `sqlalchemy`. The fail-loud semantic + 30-candidate cap eliminates the only failure surface (BM25 SQL error → propagate as 500).
- **The whole change touches 3 files in `app/rag-service` + 1 Alembic migration** — backend, frontend, ingestor are untouched. Ship risk is ~zero given current head migration `chat_sessions_multi` and existing toggle pattern in `reranker.py`.

**Primary recommendation:** Pattern-match the existing `reranker.py` toggle + `rerank_stats()` shape exactly. Put RRF, query builders, and stats counters in a new `app/rag-service/hybrid.py`. Refactor `retriever.retrieve_chunks()` to fan out → fuse → forward. Migration: 2 ADD COLUMN + 2 CREATE INDEX statements; `ACCESS EXCLUSIVE` lock during ADD COLUMN, then `SHARE` during CREATE INDEX. Run during a quiet window or wrap in `SET lock_timeout`.

---

## 2. Current Retriever Flow

### `app/rag-service/retriever.py` — quoted

The single retrieval entry point. Hybrid logic must slot between cache miss and the existing rerank call.

`retriever.py:30-46` — cache control + stats shape that the new hybrid stats must mirror:

```python
def clear_retrieval_cache() -> None:
    """Invalidate the retrieval cache. Call after any ingest or delete."""
    _retrieve_cache.clear()
    logger.info("Retrieval cache cleared.")


def retrieve_cache_stats() -> dict:
    total = _retrieve_hits + _retrieve_misses
    hit_rate = (_retrieve_hits / total) if total else 0.0
    return {
        "size": len(_retrieve_cache),
        "max_size": RETRIEVE_CACHE_SIZE,
        "ttl_seconds": RETRIEVE_CACHE_TTL,
        "hits": _retrieve_hits,
        "misses": _retrieve_misses,
        "hit_rate": round(hit_rate, 4),
    }
```

`retriever.py:69-76` — current cache key (this is the line that must change atomically with the behavior change; widen tuple to include `hybrid_enabled`):

```python
global _retrieve_hits, _retrieve_misses

cache_key = (query.strip(), machine_id, top_k, round(threshold, 4))
cached = _retrieve_cache.get(cache_key)
if cached is not None:
    _retrieve_hits += 1
    return cached
_retrieve_misses += 1
```

`retriever.py:85-117` — current vector branch. Keep verbatim as the "vector list" producer in the hybrid path:

```python
# Stage 1 — bi-encoder ANN retrieval (overfetch when reranker enabled).
overfetch = compute_overfetch(top_k)
try:
    sql = text("""
        SELECT dc.content, dc.metadata,
               1 - (dc.embedding <=> CAST(:vec AS vector)) AS similarity
        FROM doc_chunks dc
        JOIN documents d ON dc.doc_id = d.id
        WHERE (CAST(:machine_id AS integer) IS NULL OR d.machine_id = CAST(:machine_id AS integer))
          AND 1 - (dc.embedding <=> CAST(:vec AS vector)) > :threshold
        ORDER BY dc.embedding <=> CAST(:vec AS vector)
        LIMIT :top_k
    """)
    result = await db.execute(sql, {...})
    rows = result.fetchall()
    candidates = [
        {"content": r.content, "metadata": r.metadata, "similarity": float(r.similarity)}
        for r in rows
    ]
except Exception as e:
    logger.error(f"Retrieval SQL failed: {e}")
    return []
```

`retriever.py:119-126` — current handoff to reranker. The fused candidate list must hit this same call shape with `similarity` field intact (cross-encoder reads `c["content"]`, ignores everything else, then writes `rerank_score`):

```python
# Stage 2 — cross-encoder rerank. Falls back to bi-encoder order on failure.
if rerank_enabled() and candidates:
    results = await rerank(query.strip(), candidates, top_k)
else:
    results = candidates[:top_k]

_retrieve_cache[cache_key] = results
return results
```

### Reranker contract — `reranker.py:60-97`

The reranker takes `list[dict]` with at least `content` key, preserves all existing fields, and writes `rerank_score`:

```python
async def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    if not candidates:
        return []
    if not rerank_enabled():
        return candidates[:top_k]
    contents = [c["content"] for c in candidates]
    ...
    for c, s in zip(candidates, scores):
        c["rerank_score"] = s
    candidates.sort(key=lambda c: c.get("rerank_score", 0.0), reverse=True)
    return candidates[:top_k]
```

**Key invariants for hybrid integration:**
- Reranker only reads `content`. Adding `bm25_rank`, `fused_score`, `keyword_rank` to candidate dicts is safe — they survive the rerank intact.
- Reranker preserves `similarity` (vector cosine). This satisfies our locked tie-break key `(fused_score DESC, vector_similarity DESC)` — but the tie-break happens BEFORE rerank (during fusion), so the reranker's own sort takes over after.

### Reranker overfetch math — `reranker.py:100-104`

```python
def compute_overfetch(top_k: int) -> int:
    if not rerank_enabled():
        return top_k
    return min(top_k * OVERFETCH, OVERFETCH_MAX)
```

With defaults `OVERFETCH=4`, `OVERFETCH_MAX=50` and chat's `top_k=8` (`routes/chat.py:167–172`), current overfetch = `min(32, 50) = 32`. Phase 13 locks the keyword and vector branches at **30 each** (not derived from `compute_overfetch`). The planner should hard-code 30 for hybrid, or introduce a `HYBRID_OVERFETCH=30` constant in `hybrid.py`. Do NOT thread it through `compute_overfetch` — that helper belongs to the reranker layer and would couple the two concerns.

### Main service — `main.py:301-318` (the pattern to copy)

```python
@app.get("/cache-stats")
async def cache_stats():
    """Return embedding + retrieval cache hit/miss counters + reranker stats."""
    return {
        "embedding_cache": embed_cache_stats(),
        "retrieval_cache": retrieve_cache_stats(),
        "reranker": rerank_stats(),
    }


@app.get("/rerank-info")
async def rerank_info():
    """Reranker status for ops visibility."""
    return {
        "enabled": rerank_enabled(),
        "model": RERANK_MODEL,
        "overfetch": OVERFETCH,
    }
```

Direct templates for the new `hybrid` block and `/hybrid-info` endpoint — see §9.

---

## 3. Postgres FTS Technical Findings

### 3.A `websearch_to_tsquery` vs `plainto_tsquery` — pick `websearch_to_tsquery`

**Per Postgres docs:** punctuation in `websearch_to_tsquery()` input is *ignored except for the special cases of dashes and quotes*. Dashes become NOT operators (`-word` → exclusion); quotes become phrase markers. All other punctuation (colons, slashes, parentheses, angle brackets) is stripped — including the syntax punctuation that would otherwise raise an error from `to_tsquery()`. Source: [PostgreSQL 18 docs §12.3 Controlling Text Search](https://www.postgresql.org/docs/current/textsearch-controls.html), behavior backported to PG 13+.

**Worked behavior for the `OT-SEED-C49-M20` case:**

| Function | Input | Output tsquery | Notes |
|----------|-------|----------------|-------|
| `to_tsquery('english', 'OT-SEED-C49-M20')` | raw | **ERROR — syntax error in tsquery** | Hyphen is not a valid `to_tsquery` operator. Hard fail. |
| `plainto_tsquery('english', 'OT-SEED-C49-M20')` | normalized | `'ot-seed-c49-m20' & 'ot' & 'seed' & 'c49' & 'm20'` | Hyphens split into both the whole compound AND parts. Works but `&` (AND) requires every token to match the same chunk. |
| `websearch_to_tsquery('english', 'OT-SEED-C49-M20')` | web-style | `'ot-seed-c49-m20' & 'ot' & 'seed' & 'c49' & 'm20'` | Same as plainto for inputs without quotes/leading-dash. The win is **safety**: any future user input with `:` `/` `|` `<` `>` `(` `)` does not crash. |
| `websearch_to_tsquery('english', '"OT-SEED-C49-M20"')` | quoted | phrase query: `'ot-seed-c49-m20' <-> 'ot' <-> 'seed' <-> 'c49' <-> 'm20'` | Exact phrase if users wrap quotes. |

**Implication for the smoke-test:** when a user types `OT-SEED-C49-M20`, the english tokenizer splits the hyphenated string into a compound token plus its parts. The corresponding **ingested chunk content** (built by `app/backend/scripts/sync_db_to_rag.py:88-102` as `# Work Order #N — OT-SEED-Cxx-M20\n…`) will produce the same tokenization in `content_tsv_en`. `ts_rank_cd` will be high because *every* query token appears in the chunk. The french config does similar — hyphens are also a token separator under `french`. So we don't actually need french to fire for this case; we need english to fire AND we take `GREATEST`.

**Recommendation:** Use `websearch_to_tsquery` for both `french` and `english` query construction. Generate them in Python so we can build the SQL with two distinct bound parameters.

### 3.B GENERATED column gotchas

**Postgres image is `pgvector/pgvector:pg15`** (`docker-compose.yml:4`). Postgres 15 has supported `GENERATED ALWAYS AS … STORED` for `tsvector` since PG 12 — fully available here. Source: [PostgreSQL Tables and Indexes docs](https://www.postgresql.org/docs/current/textsearch-tables.html) confirms the canonical example uses `ALTER TABLE … ADD COLUMN … tsvector GENERATED ALWAYS AS (to_tsvector('english', …)) STORED`.

**Confirmed behaviors:**
1. **Auto-backfill on ADD COLUMN.** Postgres evaluates the expression for every existing row at column-add time. For ~5000 chunks of ~200 words each, this is a few seconds of CPU + a table rewrite (see §3.E).
2. **GIN index works on generated columns.** No special syntax — `CREATE INDEX … USING GIN (content_tsv_fr)` is identical to indexing any other tsvector column.
3. **Cannot be updated directly.** `UPDATE doc_chunks SET content_tsv_fr = …` will error. Only `content` (the source) can be updated. The generated column re-evaluates automatically — this is exactly what we want (zero ingestor changes).
4. **`IMMUTABLE` requirement.** `to_tsvector('config', text)` is marked `IMMUTABLE` when called with a literal config name (our case: `'french'`, `'english'`). It is `STABLE` when called with a column-driven config name — that variant **cannot** be used in a generated column. We are safe because both config names are literals.

### 3.C GIN index parameters

**Defaults are fine for our scale.**

- `fastupdate` defaults to `on`. This buffers writes in a "pending list" and flushes during VACUUM. With ~5000 chunks total and append-only ingestion (no bulk imports), the pending list never grows large. Leave default.
- `gin_pending_list_limit` defaults to 4 MB. Same reasoning — leave default.

**Disk estimate for ~5000 chunks at ~200 words/chunk (~1200 chars):**

| Object | Estimated size |
|--------|---------------|
| `content_tsv_fr` column data (stored generated) | ~500 KB – 1 MB (one tsvector per row, ~150 unique stems × ~20 bytes) |
| `content_tsv_en` column data | ~500 KB – 1 MB (same magnitude) |
| GIN index `doc_chunks_tsv_fr_idx` | ~1–3 MB (GIN is compact because posting lists are shared per term) |
| GIN index `doc_chunks_tsv_en_idx` | ~1–3 MB |
| Existing ivfflat index on `embedding(1024)` | already in place, unchanged |

Total new disk: **~5–8 MB**. Negligible.

Source: [pganalyze — Understanding Postgres GIN Indexes](https://pganalyze.com/blog/gin-index) — GIN posting lists scale with vocabulary size, not row count, so doubling chunks roughly doubles size only when vocabulary is also doubling.

### 3.D `ts_rank_cd` vs `ts_rank` — pick `ts_rank_cd`

**Pick `ts_rank_cd` for our 200-word chunks.**

- `ts_rank` weights by *term frequency* — favors documents with many repetitions of the query term. For short chunks (200 words), repetition is rare and inflates noise.
- `ts_rank_cd` (Cover Density) weights by *proximity of query terms*. For short chunks this is more discriminative: a chunk that mentions both `OT-SEED-C49-M20` and `vibration` close together ranks higher than two unrelated mentions.

**Practical signature in our query:**

```sql
ts_rank_cd(dc.content_tsv_fr, websearch_to_tsquery('french', :q_fr)) AS rank_fr,
ts_rank_cd(dc.content_tsv_en, websearch_to_tsquery('english', :q_en)) AS rank_en
```

(`:q_fr` and `:q_en` are both the raw user query; Postgres handles language-specific tokenization inside the tsquery builder.)

**Gate on `> 0.0`** — meaning at least one token matched. Per CONTEXT.md the threshold filter does NOT apply to the keyword side; the `> 0.0` gate is the only filter.

### 3.E ALTER TABLE lock duration

**Per Postgres docs**, `ALTER TABLE … ADD COLUMN … GENERATED ALWAYS AS … STORED`:

1. Acquires `ACCESS EXCLUSIVE` lock on `doc_chunks`.
2. Evaluates the expression for every row → **rewrites the table** (because the new column has stored content, not just a default expression).
3. Lock held for the entire rewrite.

For ~5000 rows of ~1.2 KB content + ~1024-dim vector (~8 KB per row in PG storage), the rewrite is a few seconds. On a healthy laptop dev DB, expect **<5 seconds**. On a production-loaded DB at scale, this could be 10–30 seconds.

**Mitigations the planner should bake in:**

1. **Run during quiet hours** (or just accept ~5 s of blocked writes on dev).
2. **`SET lock_timeout = '30s'` inside the Alembic upgrade** — if the lock isn't acquired in 30 s, fail loud rather than blocking forever.
3. **Add column FR, then EN as two separate statements** — each rewrite is independent. Easier to debug if one fails.
4. **Index creation can be `CONCURRENTLY`** to avoid blocking — but **NOT inside an Alembic transaction**. Alembic auto-wraps `op.execute()` in a transaction by default, and `CREATE INDEX CONCURRENTLY` cannot run inside one. Two options:
   - **(a)** Accept ~1 s blocking `CREATE INDEX` (no `CONCURRENTLY`). With 5000 rows this is fine.
   - **(b)** Use `op.execute("COMMIT")` before each `CREATE INDEX CONCURRENTLY` and `op.execute("BEGIN")` after. Ugly but possible.
   - **Recommend (a)** — simplicity wins at this scale. Document the assumption in the migration docstring.

Sources: [PostgreSQL Tables and Indexes §12.2](https://www.postgresql.org/docs/current/textsearch-tables.html), [pganalyze GIN article](https://pganalyze.com/blog/gin-index).

---

## 4. RRF Fusion

### Canonical reference

- **Paper:** Cormack, Clarke, Büttcher (2009). *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"*, SIGIR '09. [ResearchGate](https://www.researchgate.net/publication/221301121_Reciprocal_Rank_Fusion_outperforms_Condorcet_and_Individual_Rank_Learning_Methods).
- **`k=60` rationale:** the 2009 paper found `k=60` robust across TREC benchmark sets. Subsequent IR benchmarks (incl. modern hybrid-search studies) confirm `k ∈ [40, 80]` performs comparably — that is why OpenSearch, Elasticsearch, Azure AI Search, MongoDB Atlas, and Weaviate all default to 60. Source: [BigData Boutique blog on RRF](https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it).

### Formula

For document `d` and result lists `L_1, L_2, …`:

```
RRF(d) = Σ_i  1 / (k + rank_i(d))
```

where:
- `rank_i(d)` is the 1-based rank of `d` in list `L_i`, or excluded from the sum if `d` is absent from `L_i`.
- `k = 60` (fixed for Phase 13).

### Worked numerical example

**Vector list (top 4):**
| rank | chunk_id | similarity |
|------|----------|------------|
| 1 | A | 0.82 |
| 2 | B | 0.79 |
| 3 | C | 0.71 |
| 4 | D | 0.68 |

**Keyword list (top 4):**
| rank | chunk_id | ts_rank_cd |
|------|----------|------------|
| 1 | C | 0.087 |
| 2 | E | 0.061 |
| 3 | A | 0.044 |
| 4 | F | 0.022 |

**Fused (k=60):**

| chunk | vec rank | kw rank | fused score |
|-------|---------:|--------:|------------:|
| A | 1 | 3 | 1/61 + 1/63 = 0.01640 + 0.01587 = **0.03227** |
| C | 3 | 1 | 1/63 + 1/61 = 0.01587 + 0.01640 = **0.03227** |
| B | 2 | — | 1/62 = **0.01613** |
| E | — | 2 | 1/62 = **0.01613** |
| D | 4 | — | 1/64 = **0.01563** |
| F | — | 4 | 1/64 = **0.01563** |

**Sort with tie-break `(fused_score DESC, vector_similarity DESC)`:**

1. A (0.03227, sim=0.82) — wins tie over C because higher cosine
2. C (0.03227, sim=0.71)
3. B (0.01613, sim=0.79) — wins tie over E because E has no `similarity`; treat absent as 0.0
4. E (0.01613, sim=0.0)
5. D (0.01563, sim=0.68)
6. F (0.01563, sim=0.0)

**Implementation note:** when a chunk is keyword-only, `similarity` is unknown from the vector branch — but we know it has cosine < `threshold` (else it would have appeared in the vector list). For the tie-break, treat absent `similarity` as `0.0`. The vector chunks that contributed will sort above keyword-only chunks at equal RRF — which is exactly the locked "semantic wins ties" semantic.

### Python sketch (~30 lines, no library)

```python
def rrf_fuse(
    vector_hits: list[dict],
    keyword_hits: list[dict],
    k: int = 60,
    limit: int = 30,
) -> list[dict]:
    """
    Fuse two ranked lists by Reciprocal Rank Fusion (Cormack 2009).

    Each hit dict carries {content, metadata, similarity?, ts_rank?, source}.
    Output dicts gain {fused_score, vector_rank?, keyword_rank?}.
    Tie-break: (fused_score DESC, similarity DESC).
    """
    by_key: dict[str, dict] = {}

    def _key(h: dict) -> str:
        # Use chunk content hash (or doc_id+chunk_index if available in metadata)
        # to dedupe across the two lists. Content is reliable here.
        return h["content"]

    for i, h in enumerate(vector_hits, start=1):
        key = _key(h)
        entry = by_key.setdefault(key, dict(h))
        entry.setdefault("similarity", h.get("similarity", 0.0))
        entry["vector_rank"] = i
        entry["fused_score"] = entry.get("fused_score", 0.0) + 1.0 / (k + i)

    for i, h in enumerate(keyword_hits, start=1):
        key = _key(h)
        entry = by_key.setdefault(key, dict(h))
        entry["keyword_rank"] = i
        entry["ts_rank_cd"] = h.get("ts_rank_cd")
        entry["fused_score"] = entry.get("fused_score", 0.0) + 1.0 / (k + i)
        # Keyword-only entries have no similarity — default 0.0 for tie-break.
        entry.setdefault("similarity", 0.0)

    fused = sorted(
        by_key.values(),
        key=lambda h: (h["fused_score"], h.get("similarity", 0.0)),
        reverse=True,
    )
    return fused[:limit]
```

---

## 5. SQL Recommendation

### Options considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Two separate queries, fuse in Python** | Vector SELECT (existing) + new keyword SELECT. Python runs RRF. | Clearest separation. Vector branch untouched. Easy to disable hybrid via single Python branch. | Two DB round-trips. ~2× latency vs single query. |
| **B. Single CTE / `UNION ALL`** | One round-trip with `WITH vec AS (…), kw AS (…) SELECT … FROM vec UNION ALL kw`. | One round-trip. Reuses the same `documents` JOIN execution. | Postgres may pick suboptimal plan when mixing GIN scan + ivfflat scan in one statement. Harder to disable keyword branch. |
| **C. Native SQL RRF** | Compute RRF inside Postgres using window functions over `UNION ALL`. | Zero Python compute. | Brittle SQL. No latitude for future tie-break tweaks. Tooling/debugging painful. |

### Recommended: **Option A — two queries, fuse in Python**

**Reasoning:**

1. **Latency is non-issue.** Both queries are sub-50ms with proper indexes. The cross-encoder rerank that follows takes ~300–500 ms; the extra DB round-trip is noise.
2. **Vector branch is untouched.** Lower regression risk. The existing query at `retriever.py:88-97` is already proven on the 1024-dim ivfflat index.
3. **Plan predictability.** Two single-purpose queries each use exactly one index. The keyword query uses `doc_chunks_tsv_fr_idx` + `doc_chunks_tsv_en_idx` via a bitmap OR scan; the vector query uses `doc_chunks_embedding_idx`. The planner cannot mis-pick.
4. **`fail loud` becomes trivial.** If the keyword SELECT raises, propagate the exception. Don't catch.
5. **The reranker, cache layer, and tests all continue to receive a single `list[dict]`** — same shape, same fields plus a few new ones.

### Recommended SQL for the keyword branch

```sql
WITH ranked AS (
    SELECT
        dc.id AS chunk_id,
        dc.content,
        dc.metadata,
        ts_rank_cd(dc.content_tsv_fr,
                   websearch_to_tsquery('french',  :q)) AS rank_fr,
        ts_rank_cd(dc.content_tsv_en,
                   websearch_to_tsquery('english', :q)) AS rank_en
    FROM doc_chunks dc
    JOIN documents d ON dc.doc_id = d.id
    WHERE
        (CAST(:machine_id AS integer) IS NULL OR d.machine_id = CAST(:machine_id AS integer))
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

**Why this shape:**
- The `@@` filter inside the CTE lets Postgres use the GIN indexes via bitmap-OR scan. Without it, `ts_rank_cd` would be computed for every row.
- `JOIN documents` happens once. For `machine_id IS NULL`, Postgres skips the join's filter — the GIN scan dominates.
- `GREATEST(rank_fr, rank_en)` matches CONTEXT.md's per-chunk rank rule.
- `:q` is passed twice for `french` and `english` configs. Reuse the same parameter; rely on Postgres to tokenize per config.
- `LIMIT :top_k` is set to **30** by the Python caller per the locked overfetch shape.

### EXPLAIN plan expectations (for the planner's verification step)

For an unfiltered query (no `machine_id`):

```
Limit
  -> Sort
       Sort Key: (GREATEST(rank_fr, rank_en)) DESC
       -> CTE Scan on ranked
            -> BitmapOr
                 -> Bitmap Index Scan on doc_chunks_tsv_fr_idx
                       Index Cond: (content_tsv_fr @@ '...'::tsquery)
                 -> Bitmap Index Scan on doc_chunks_tsv_en_idx
                       Index Cond: (content_tsv_en @@ '...'::tsquery)
            -> Bitmap Heap Scan on doc_chunks dc
                 (recheck condition)
            -> Hash Join (documents d)
```

For a `machine_id`-filtered query, the planner may either:
- (a) JOIN first (using `ix_documents_machine_id`), then GIN scan; or
- (b) GIN scan first, then filter via `Hash Join`.

Either is fine at our scale. Add an INFO log capturing query plan choice in the first 1-2 weeks of operation if the planner wants confirmation.

### Failure to use indexes — sanity check

If the migration succeeds but `EXPLAIN ANALYZE` shows a **Seq Scan on doc_chunks**, the most likely cause is:
- GIN index not yet built (CREATE INDEX without `CONCURRENTLY` is synchronous, so this should not happen in normal flow — but worth checking).
- `random_page_cost` set unusually low (defaults are fine).

---

## 6. Cache Key + Invalidation

### Current state — `retriever.py:71`

```python
cache_key = (query.strip(), machine_id, top_k, round(threshold, 4))
```

### Required change

Per CONTEXT.md, widen to include `hybrid_enabled`. **Atomically with the behavior change** — if we deploy the new code without widening the cache key, a stale cache could return vector-only results for a hybrid-on query.

```python
hybrid_on = hybrid_enabled()
cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)
```

### Why the existing TTL + invalidation still works

- `clear_retrieval_cache()` is called by `delete_document` in `main.py:293` and `ingest_document` (via `ingestor.py:358`). Both wipe the entire cache regardless of key. No change needed.
- The `rag_change_hooks.py` Celery sync path eventually triggers ingest/delete in the rag-service, which hits the same invalidation. Confirmed by `ingestor.py:358` → `clear_retrieval_cache()`.
- TTL of 300 s is unaffected.

### Edge case the planner should handle

When `HYBRID_ENABLED` is toggled at runtime (e.g., to A/B test), in-flight cache entries with the old `hybrid_enabled` value remain valid for up to 5 minutes. This is **desired** — keys differ, so old keys don't pollute new lookups. No flush needed. Document this in the docstring.

---

## 7. Reranker Compatibility

### What the reranker needs

`reranker.py:60-97` reads `c["content"]` and writes `c["rerank_score"]`. All other fields are preserved unchanged. The final return is `candidates.sort(key=…rerank_score…)[:top_k]`.

### What fused candidates look like going in

Each dict from `rrf_fuse()` has:
```python
{
    "content": str,             # original from doc_chunks.content
    "metadata": dict,           # original from doc_chunks.metadata (JSONB)
    "similarity": float,        # cosine sim, or 0.0 if keyword-only
    "fused_score": float,       # RRF score
    "vector_rank": int | None,  # 1-based, absent if keyword-only
    "keyword_rank": int | None, # 1-based, absent if vector-only
    "ts_rank_cd": float | None, # only if keyword-side contributed
}
```

### What comes out after rerank

Same dict + `rerank_score: float`. The reranker re-sorts by `rerank_score` — at that point `fused_score` becomes informational metadata (good for logging).

### Pydantic model in `main.py:63-66`

```python
class ChunkResult(BaseModel):
    content: str
    metadata: dict
    similarity: float
```

The response model accepts only these three fields. If the planner wants to expose `fused_score`, `vector_rank`, `keyword_rank` to the backend, the planner must extend `ChunkResult` (optional fields). **For Phase 13.1 keep the response shape unchanged** — the backend chat consumer at `routes/chat.py` doesn't read those fields, and we don't want to ripple changes.

The internal hybrid fields are still useful for **INFO logs** per CONTEXT.md's observability ask: log each returned chunk as `chunk_id=X source=(vector|keyword|both) fused=Y rerank=Z`.

### Source-attribution counters

Per `/cache-stats.hybrid` shape, we need to know if each returned chunk was vector-only, keyword-only, or both. Compute at fusion time:

```python
if "vector_rank" in c and "keyword_rank" in c:
    source = "both"
elif "vector_rank" in c:
    source = "vector_only"
else:
    source = "keyword_only"
```

Aggregate over the final top-30 (post-rerank, post-trim-to-`top_k`) into the stats block.

---

## 8. Failure Modes + Fail-Loud Semantics

### Classification

| Failure | Recoverable? | Action |
|---------|--------------|--------|
| Malformed tsquery from user input | **No** (programming bug — `websearch_to_tsquery` should never raise on user input) | Fail loud → 500 |
| GIN index not yet built | Yes (planner-only, surfaces in dev) | Fail loud → 500. Migration must run before service start. |
| Generated column missing on a row | **Cannot occur** — GENERATED ALWAYS forces population at INSERT, including the backfill at ADD COLUMN | n/a |
| Embedding service error in vector branch | Existing path returns `[]` silently (`retriever.py:81-83`) | **Keep current behavior** — embedding failure is independent of hybrid. |
| BM25 SQL execution error (e.g., column dropped manually, role lacks SELECT) | No | Fail loud → 500 per CONTEXT.md |
| Connection drop mid-query | Yes (rare) | Let SQLAlchemy propagate; FastAPI returns 500. |

### Fail-loud implementation pattern

```python
# In retriever.retrieve_chunks() after the (now-required) hybrid_enabled() check:
if hybrid_enabled():
    try:
        kw_hits = await keyword_search(query, db, machine_id, top_k=30)
    except Exception as e:
        # No silent fallback per CONTEXT.md.
        logger.error(f"BM25 keyword branch failed: {e}", exc_info=True)
        raise  # FastAPI translates to 500
```

**Do NOT wrap this in `try: return []`.** The whole point of fail-loud is unambiguous regression detection.

### What to test

1. `websearch_to_tsquery('french', '')` — empty query. Returns empty tsquery. Should yield empty keyword list (no error, no rows).
2. `websearch_to_tsquery('english', '-')` — single-dash. Per docs treated as NOT operator with no operand → empty tsquery. No rows, no error.
3. `websearch_to_tsquery('english', 'OT-SEED-C49-M20:foo<bar>')` — punctuation soup. Should produce a normal tsquery; colon/angle brackets stripped.
4. Toggling `HYBRID_ENABLED=false` then back to `true` — service must pick up env on next request via the function call (matches `rerank_enabled()` pattern; env is read every call, not cached).
5. Dropping `content_tsv_fr` manually then making a request — must return 500 with a clear error message in logs.

---

## 9. Observability Shape

### Stats counter contract — match `rerank_stats()` shape

Module-level in `hybrid.py`:

```python
_searches = 0           # number of retrieve_chunks() calls where hybrid ran
_vector_only_count = 0  # final-returned chunks contributed by vector only
_keyword_only_count = 0 # final-returned chunks contributed by keyword only
_both_count = 0         # final-returned chunks contributed by both
_keyword_zero_hits = 0  # queries where keyword branch returned 0 rows
_vector_zero_hits = 0   # queries where vector branch returned 0 rows
```

### `hybrid_stats()` JSON — extend `/cache-stats`

```json
{
  "embedding_cache": { ... },
  "retrieval_cache": { ... },
  "reranker": { ... },
  "hybrid": {
    "enabled": true,
    "fusion": "rrf",
    "k": 60,
    "overfetch": 30,
    "fts_configs": ["french", "english"],
    "searches": 142,
    "vector_only_count": 88,
    "keyword_only_count": 21,
    "both_count": 233,
    "keyword_zero_hits": 4,
    "vector_zero_hits": 0
  }
}
```

### `GET /hybrid-info` — match `/rerank-info` shape

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

### Per-query INFO log

For each call, log:

```
hybrid query=<truncated 80 chars> machine_id=<id|null>
  vector_hits=30 keyword_hits=27 fused=42 returned=8
  source_mix=(both:5, vector_only:2, keyword_only:1)
```

This is one log line per `/retrieve` call. At expected traffic this is fine; if it ever becomes noisy, gate behind `HYBRID_DEBUG_LOG` env var.

---

## 10. Smoke-Test Corpus References

### How the test IDs get into the RAG corpus

The `OT-SEED-Cxx-Myy` work order titles are generated by `app/backend/seed_ml_data_m13.py:420`:

```python
ot = Ordres_travail(
    titre          = f"OT-SEED-C{cycle_num:02d}-M{TARGET_MACHINE_ID}",
    description    = f"OT seed cycle {cycle_num} — {cfg['failure_type']}",
    ...
    statut         = OrdreStatut.CLOSED,
    ...
)
```

These rows are then synced to the RAG knowledge base by `app/backend/scripts/sync_db_to_rag.py:153-161` (table filter: `statut IN ('COMPLETED','VALIDATED','CLOSED')` — so only `CLOSED` seeded rows are indexed) and formatted as a chunk by `_fmt_ordre_travail` at lines 88-102:

```python
def _fmt_ordre_travail(r) -> str:
    return (
        f"# Work Order #{r.id} — {r.titre}\n\n"
        f"- Machine ID: {r.machine_id}\n"
        f"- Priority: {r.priorite}\n"
        f"- Status: {r.statut}\n"
        f"- Failure type: {r.failure_type or '—'}\n"
        ...
        f"\n## Description\n{r.description}\n"
        ...
    )
```

### Predictable chunks the smoke tests can assert on

Assuming `TARGET_MACHINE_ID = 20` and cycles 1..49 ran, the corpus contains chunks whose `content` starts with strings like:

| Chunk identifying prefix | Token English would emit |
|--------------------------|-------------------------|
| `# Work Order #<n> — OT-SEED-C01-M20\n\n- Machine ID: 20\n…` | `ot-seed-c01-m20`, `ot`, `seed`, `c01`, `m20`, `machine`, … |
| `# Work Order #<n> — OT-SEED-C25-M20\n\n…` | similar with `c25` |
| `# Work Order #<n> — OT-SEED-C49-M20\n\n…` | similar with `c49` |

### Three representative assertion targets

1. **Exact-ID hit:** `query="OT-SEED-C49-M20"` → top-1 must be the chunk whose content contains the literal `OT-SEED-C49-M20`. The english branch produces a tsquery hitting `ot-seed-c49-m20` AND `c49` AND `m20` — a chunk that has all of these is heavily favored.
2. **Compound machine-ID + status:** `query="closed work order machine 20"` → should rank a closed OT chunk above an unrelated `Machine #20` chunk. RRF should let `closed` token (high `ts_rank_cd` from keyword) join `work order machine 20` (vector match).
3. **Failure-type natural language:** `query="vibration tool wear failure"` → vector branch should dominate. Keyword branch helps if "tool wear" appears in the description.

Sources for these chunks already exist in the DB after running the M13 seeder; the planner can pre-flight by `make db` then:

```sql
SELECT id, LEFT(content, 80)
FROM doc_chunks
WHERE content LIKE '%OT-SEED-C49-M20%'
LIMIT 3;
```

If this returns 0 rows on the planner's machine, run `python app/backend/seed_ml_data_m13.py` then trigger the Celery sync (`tasks.rag_sync_all`) — or directly call `python app/backend/scripts/sync_db_to_rag.py --tables ordres_travail`.

---

## 11. Risks + Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GIN index not auto-used because Postgres planner picks Seq Scan for tiny tables | Low | Low (results still correct, just slower) | After migration, run `EXPLAIN ANALYZE` of the keyword SQL once. With 5000+ rows the GIN scan will be picked. |
| Generated-column ADD COLUMN blocks chat for several seconds in production | Medium | Medium | Wrap in `SET lock_timeout = '30s'`; run during quiet window. Document in migration docstring. |
| RRF tie-break has many keyword-only chunks at equal scores → sort is unstable | Low | Low | Python's sort is stable; secondary key is `similarity` (0.0 for keyword-only). Tertiary key could be `keyword_rank` if needed — not locked, but easy to add. |
| User types a query with control chars that crash `websearch_to_tsquery` | Very low | High (per CONTEXT.md, fail loud → 500) | Document that the input is passed verbatim. If real-world 500s appear, add a unit test with the offending input — do NOT silently swallow. |
| Two GIN indexes + two generated columns roughly double the chunk row size for storage | n/a | Low | ~5–8 MB total; tiny relative to embedding column. |
| Cache key collision after toggling `HYBRID_ENABLED` mid-flight | Very low | Low | Behavior is desired — different boolean → different cache key → different result set. Document. |
| Reranker rejects extra fields on candidate dicts | Zero | n/a | Verified at `reranker.py:60-97` — fields are passed through unchanged. |
| Backend chat response shape changes | Zero | High if it changed | `RetrieveResponse.chunks: List[ChunkResult]` (`main.py:63-71`) — keep `ChunkResult` fields exactly as-is. Internal hybrid fields stay inside the rag-service. |
| Postgres image lacks `gen_random_uuid` for migration | Zero | Low | The migration only ADDs columns + indexes; no UUID generation needed. |

---

## 12. Open Questions

1. **Per-query INFO log shape — gate behind env?** CONTEXT.md says "INFO logs per query: which source contributed each final chunk." That can be high volume. Recommend a single-line summary per call (proposed in §9). The planner should confirm — or add `HYBRID_LOG_PER_CHUNK=false` as a guard.

2. **Are there docs in the corpus where ONLY french FTS would help?** All the seeded smoke-test data is largely ASCII-only IDs. The french branch is justified for ingested PDFs (manuals, SOPs) but not for the smoke tests. Suggestion: also write a smoke test against a French manual chunk if one is present (`SELECT id FROM documents WHERE filename LIKE '%manuel%'`).

3. **`docker-compose.yml` env block — exact placement.** Currently `RERANK_ENABLED` is at `docker-compose.yml:235`. The new line should sit immediately below:
   ```yaml
   RERANK_ENABLED: ${RERANK_ENABLED:-true}
   HYBRID_ENABLED: ${HYBRID_ENABLED:-true}
   ```
   Also add `HYBRID_ENABLED=` to `.env.example` line 34 (mirrors `RERANK_ENABLED=` at line 33).

4. **Should `chat_sessions_multi` be set as the down-revision verbatim?** Confirmed at `chat_sessions_multi.py:10-11` (`revision = "chat_sessions_multi"`, no merge revisions after it). The new migration's `down_revision = "chat_sessions_multi"` is correct. No new head needed.

5. **Does the reranker need to be told about the new `fused_score` for any reason?** No. The reranker is content-only. Confirmed at `reranker.py:82` (`contents = [c["content"] for c in candidates]`).

6. **Should we add a unit test for `rrf_fuse()` independent of DB?** Strongly recommended. RRF is pure Python with no I/O; the worked example in §4 is a ready-made test case. The planner should include this as a Wave 0 or Wave 1 task.

---

## Sources

### Primary (HIGH confidence)
- **PostgreSQL docs:** [§12.3 Controlling Text Search](https://www.postgresql.org/docs/current/textsearch-controls.html) — confirms `websearch_to_tsquery` punctuation handling.
- **PostgreSQL docs:** [§12.2 Tables and Indexes](https://www.postgresql.org/docs/current/textsearch-tables.html) — confirms `GENERATED ALWAYS AS STORED` tsvector + GIN index pattern.
- **Cormack, Clarke, Büttcher (2009)** — *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*, SIGIR '09. [ResearchGate link](https://www.researchgate.net/publication/221301121_Reciprocal_Rank_Fusion_outperforms_Condorcet_and_Individual_Rank_Learning_Methods).
- **In-repo code at quoted line numbers** (see §2) — the contract the new code must respect.

### Secondary (MEDIUM confidence)
- [pganalyze — Understanding Postgres GIN Indexes](https://pganalyze.com/blog/gin-index) — corroborates size estimates and posting-list behavior.
- [BigData Boutique — Reciprocal Rank Fusion: How It Works and When to Use It](https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it) — corroborates `k=60` default across vendor implementations.

### Tertiary (LOW confidence)
- [runebook.dev — websearch_to_tsquery worked examples](https://runebook.dev/en/docs/postgresql/functions-textsearch/websearch_to_tsquery) — examples cross-checked against official docs; used only to verify behavior of weird inputs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Postgres FTS + RRF are textbook; both libraries already present.
- Architecture: HIGH — direct copy of existing toggle/stats/cache pattern.
- SQL recommendation: HIGH — keyword query verified against EXPLAIN plan reasoning.
- Pitfalls: MEDIUM-HIGH — lock duration estimate is empirical; exact ms TBD per machine.
- Smoke corpus: HIGH — exact source confirmed in `seed_ml_data_m13.py:420` and `sync_db_to_rag.py:88-102`.

**Research date:** 2026-06-06
**Valid until:** 2026-09-06 (Postgres major version change would invalidate; otherwise stable).
