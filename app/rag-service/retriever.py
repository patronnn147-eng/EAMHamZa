"""
Semantic retrieval via pgvector cosine similarity.

Returns top-k chunks above similarity threshold for a given query.
"""
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from embedder import embed_text, vec_to_str

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    machine_id: Optional[int] = None,
    top_k: int = 3,
    threshold: float = 0.7,
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
            WHERE (:machine_id::int IS NULL OR d.machine_id = :machine_id)
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

        return [
            {
                "content": r.content,
                "metadata": r.metadata,
                "similarity": float(r.similarity),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Retrieval SQL failed: {e}")
        return []
