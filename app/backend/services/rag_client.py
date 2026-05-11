"""
RAG service client — thin httpx async wrapper.

Main backend calls this instead of embedding/querying pgvector directly.
All heavy ML work (embedding, chunking) is done in the rag-service container.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8003")
_TIMEOUT = httpx.Timeout(30.0, connect=5.0)  # embed can take a moment on first call


async def retrieve_chunks(
    query: str,
    machine_id: Optional[int] = None,
    top_k: int = 3,
    threshold: float = 0.7,
) -> list[dict]:
    """
    Call RAG service /retrieve — returns list of {content, metadata, similarity} dicts.

    Degrades gracefully: returns [] on any error so chat still works.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{RAG_SERVICE_URL}/retrieve",
                json={
                    "query": query,
                    "machine_id": machine_id,
                    "top_k": top_k,
                    "threshold": threshold,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("chunks", [])
    except httpx.ConnectError:
        logger.warning("RAG service unreachable — no context injected.")
        return []
    except Exception as e:
        logger.warning(f"RAG retrieve failed: {e}")
        return []


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    machine_id: Optional[int] = None,
    uploaded_by: Optional[int] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Call RAG service /ingest — returns {doc_id, chunk_count, filename}.

    Raises httpx.HTTPStatusError on 4xx/5xx so caller can handle.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
        files = {"file": (filename, file_bytes, _content_type(filename))}
        data: dict = {"doc_type": doc_type}
        if machine_id is not None:
            data["machine_id"] = str(machine_id)
        if uploaded_by is not None:
            data["uploaded_by"] = str(uploaded_by)
        if description:
            data["description"] = description

        resp = await client.post(
            f"{RAG_SERVICE_URL}/ingest",
            files=files,
            data=data,
        )
        resp.raise_for_status()
        return resp.json()


async def list_documents(
    doc_type: Optional[str] = None,
    machine_id: Optional[int] = None,
) -> list[dict]:
    """Proxy GET /documents from RAG service."""
    params: dict = {}
    if doc_type:
        params["doc_type"] = doc_type
    if machine_id is not None:
        params["machine_id"] = machine_id

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{RAG_SERVICE_URL}/documents", params=params)
        resp.raise_for_status()
        return resp.json()


async def delete_document(doc_id: str) -> None:
    """Proxy DELETE /documents/{id} to RAG service."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(f"{RAG_SERVICE_URL}/documents/{doc_id}")
        resp.raise_for_status()


def _content_type(filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return "application/pdf"
    return "text/plain"
