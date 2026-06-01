"""
Semantic retrieval via pgvector cosine similarity.

Returns top-k chunks above similarity threshold for a given query.

Caching: identical (query, machine_id, top_k, threshold) tuples are cached
in-memory for 5 minutes. Reset on container restart and on any ingest/delete
(see clear_retrieval_cache()).
"""
import logging
from typing import Optional

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from embedder import embed_text, vec_to_str

logger = logging.getLogger(__name__)

# Retrieval result cache
RETRIEVE_CACHE_SIZE = 512
RETRIEVE_CACHE_TTL = 300  # 5 minutes
_retrieve_cache: TTLCache = TTLCache(maxsize=RETRIEVE_CACHE_SIZE, ttl=RETRIEVE_CACHE_TTL)
_retrieve_hits = 0
_retrieve_misses = 0


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


async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    machine_id: Optional[int] = None,
    top_k: int = 3,
    threshold: float = 0.30,
) -> list[dict]:
    """
    Embed query → cosine similarity search → return top-k chunks above threshold.

    Args:
        query: Natural language query string
        db: Async DB session
        machine_id: Optional filter — only chunks from docs linked to this machine
        top_k: Max number of chunks to return
        threshold: Min cosine similarity (0.0-1.0). Chunks below this are excluded.

    Returns:
        List of {content, metadata, similarity} dicts. Empty list if nothing above threshold.
    """
    global _retrieve_hits, _retrieve_misses

    cache_key = (query.strip(), machine_id, top_k, round(threshold, 4))
    cached = _retrieve_cache.get(cache_key)
    if cached is not None:
        _retrieve_hits += 1
        return cached
    _retrieve_misses += 1

    try:
        query_vec = await embed_text(query)
        vec_str = vec_to_str(query_vec)
    except Exception as e:
        logger.error(f"Embedding failed for query: {e}")
        return []

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

        result = await db.execute(sql, {
            "vec": vec_str,
            "machine_id": machine_id,
            "threshold": threshold,
            "top_k": top_k,
        })
        rows = result.fetchall()

        results = [
            {
                "content": r.content,
                "metadata": r.metadata,
                "similarity": float(r.similarity),
            }
            for r in rows
        ]
        _retrieve_cache[cache_key] = results
        return results
    except Exception as e:
        logger.error(f"Retrieval SQL failed: {e}")
        return []
