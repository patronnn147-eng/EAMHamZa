"""
Phase 13.1 hybrid retrieval: keyword (Postgres FTS via two GENERATED tsvector
columns on doc_chunks) + vector (existing pgvector cosine), fused via
Reciprocal Rank Fusion (k=60). Stage A each side returns 30 candidates;
Stage B fuses to <=30 unique candidates; Stage C is the existing
cross-encoder reranker (unchanged). Fail-loud on BM25 errors -- no silent
vector-only fallback (per CONTEXT.md).

Exports:
  - hybrid_enabled()        : bool   -- env toggle, default True
  - keyword_search(...)     : coro   -- Postgres FTS branch (CTE, websearch_to_tsquery)
  - rrf_fuse(...)           : list   -- pure-Python RRF fusion
  - hybrid_stats()          : dict   -- counters + config for /cache-stats
  - record_call(...)        : None   -- per-query stats accumulator
  - HYBRID_RRF_K            : int    -- 60
  - HYBRID_OVERFETCH        : int    -- 30
  - FTS_CONFIGS             : tuple  -- ("french", "english")
  - TIE_BREAK               : str    -- "vector_similarity_desc"

Module has no I/O at import time. The only DB-touching function is
keyword_search().
"""
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (locked by CONTEXT.md + RESEARCH.md)
# ---------------------------------------------------------------------------

HYBRID_RRF_K = 60
HYBRID_OVERFETCH = 30
FTS_CONFIGS = ("french", "english")
TIE_BREAK = "vector_similarity_desc"


# ---------------------------------------------------------------------------
# Env toggle -- mirrors reranker.rerank_enabled() exactly
# ---------------------------------------------------------------------------

def hybrid_enabled() -> bool:
    """Toggle: env HYBRID_ENABLED, default true."""
    return os.getenv("HYBRID_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Per-call stats counters (mirror reranker_stats shape)
# ---------------------------------------------------------------------------

_searches = 0
_vector_only_count = 0
_keyword_only_count = 0
_both_count = 0
_keyword_zero_hits = 0
_vector_zero_hits = 0


def record_call(vector_n: int, keyword_n: int, returned_with_source: list[str]) -> None:
    """
    Update module-level counters after a hybrid query completes.

    Args:
        vector_n: number of rows returned by the vector branch this call
        keyword_n: number of rows returned by the keyword branch this call
        returned_with_source: list of per-chunk source labels for the FINAL
            returned list (post-rerank, post-trim-to-top_k). Each entry must
            be one of "both" / "vector_only" / "keyword_only".
    """
    global _searches, _vector_only_count, _keyword_only_count, _both_count
    global _keyword_zero_hits, _vector_zero_hits

    _searches += 1
    if keyword_n == 0:
        _keyword_zero_hits += 1
    if vector_n == 0:
        _vector_zero_hits += 1

    for label in returned_with_source:
        if label == "both":
            _both_count += 1
        elif label == "vector_only":
            _vector_only_count += 1
        elif label == "keyword_only":
            _keyword_only_count += 1


def hybrid_stats() -> dict:
    """Stats endpoint payload -- matches reranker_stats shape."""
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


# ---------------------------------------------------------------------------
# Keyword branch -- Postgres FTS via two GIN-indexed tsvector columns
# ---------------------------------------------------------------------------

# Locked CTE SQL from RESEARCH §5 + plan <interfaces> block. dc.id AS chunk_id
# is projected so rrf_fuse() can dedupe by stable PK.
_KEYWORD_SQL = text("""
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
    LIMIT :top_k
""")


async def keyword_search(
    query: str,
    db: AsyncSession,
    machine_id: int | None,
    top_k: int = HYBRID_OVERFETCH,
) -> list[dict]:
    """
    Postgres FTS keyword search across content_tsv_fr + content_tsv_en.

    Returns list of {chunk_id, content, metadata, ts_rank_cd} dicts ordered
    by GREATEST(rank_fr, rank_en) DESC. Empty list when no rows match.

    Fail-loud: any SQL error propagates -- DO NOT wrap in try/except per
    CONTEXT.md.
    """
    result = await db.execute(
        _KEYWORD_SQL,
        {
            "q": query.strip(),
            "machine_id": machine_id,
            "top_k": top_k,
        },
    )
    rows = result.fetchall()
    return [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "metadata": r.metadata,
            "ts_rank_cd": float(r.keyword_score),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# RRF fusion -- pure Python, no library
# ---------------------------------------------------------------------------

def rrf_fuse(
    vector_hits: list[dict],
    keyword_hits: list[dict],
    k: int = HYBRID_RRF_K,
    limit: int = HYBRID_OVERFETCH,
) -> list[dict]:
    """
    Fuse two ranked lists by Reciprocal Rank Fusion (Cormack 2009).

    Each input dict MUST carry a stable `chunk_id` field -- it's the dedup key
    across the two lists. Vector dicts carry `similarity` (cosine); keyword
    dicts carry `ts_rank_cd`.

    Algorithm:
      - For each list, accumulate fused_score += 1/(k + rank) per chunk_id.
      - Stamp vector_rank / keyword_rank where applicable.
      - For keyword-only chunks, default similarity to 0.0 so the tie-break
        sort key is well-defined.
      - Sort by (fused_score DESC, similarity DESC); Python's stable sort
        keeps deterministic order within ties.
      - Trim to `limit`.

    Returns:
        list of merged dicts. Output preserves `content`, `metadata`, and
        carries new fields (`fused_score`, `vector_rank`/`keyword_rank`,
        `similarity`). The reranker downstream only reads `content` so any
        additional fields pass through unchanged.

    Empty inputs return [].
    Dedup uses chunk_id only -- if the same chunk_id appears in both lists
    with different `content`, the FIRST-SEEN entry by chunk_id wins (this
    case shouldn't happen in production but is tested for safety).
    """
    by_key: dict = {}

    for i, h in enumerate(vector_hits, start=1):
        key = h["chunk_id"]
        entry = by_key.setdefault(key, dict(h))
        # Preserve existing similarity from vector branch.
        entry.setdefault("similarity", float(h.get("similarity", 0.0)))
        entry["vector_rank"] = i
        entry["fused_score"] = entry.get("fused_score", 0.0) + 1.0 / (k + i)

    for i, h in enumerate(keyword_hits, start=1):
        key = h["chunk_id"]
        entry = by_key.setdefault(key, dict(h))
        entry["keyword_rank"] = i
        if "ts_rank_cd" not in entry and "ts_rank_cd" in h:
            entry["ts_rank_cd"] = h["ts_rank_cd"]
        entry["fused_score"] = entry.get("fused_score", 0.0) + 1.0 / (k + i)
        # Keyword-only chunks have no similarity -- default 0.0 for tie-break.
        entry.setdefault("similarity", 0.0)

    fused = sorted(
        by_key.values(),
        key=lambda h: (h["fused_score"], h.get("similarity", 0.0)),
        reverse=True,
    )
    return fused[:limit]
