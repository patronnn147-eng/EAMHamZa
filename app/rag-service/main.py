"""
EAM RAG Microservice

Handles: document ingestion, semantic retrieval, document management.
Runs isolated from main backend. Called via HTTP by main backend.

Endpoints:
  GET  /health                   — healthcheck
  POST /ingest                   — multipart file + metadata → ingest
  POST /retrieve                 — {query, machine_id?, top_k?, threshold?} → {chunks}
  GET  /documents                — list documents
  DELETE /documents/{id}         — delete doc + all chunks (CASCADE)
"""

import logging
import os
from typing import List, Optional

from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ingestor import ingest_document, extract_image_text
from retriever import retrieve_chunks, clear_retrieval_cache, retrieve_cache_stats
from embedder import embed_cache_stats
from reranker import rerank_stats, rerank_enabled, MODEL_NAME as RERANK_MODEL, OVERFETCH
from hybrid import (
    FTS_CONFIGS,
    HYBRID_OVERFETCH,
    HYBRID_RRF_K,
    TIE_BREAK,
    hybrid_enabled,
    hybrid_stats,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EAM RAG Service", version="1.0.0")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".bmp",
    ".webp",
    ".docx",
    ".xlsx",
    ".html",
    ".htm",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "rag"}


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


class RetrieveRequest(BaseModel):
    query: str
    machine_id: Optional[int] = None
    top_k: int = 3
    threshold: float = 0.7


class ChunkResult(BaseModel):
    content: str
    metadata: dict
    similarity: float


class RetrieveResponse(BaseModel):
    chunks: List[ChunkResult]
    count: int


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    request: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic retrieval — returns top-k chunks above similarity threshold."""
    chunks = await retrieve_chunks(
        query=request.query,
        db=db,
        machine_id=request.machine_id,
        top_k=request.top_k,
        threshold=request.threshold,
    )
    return RetrieveResponse(
        chunks=[ChunkResult(**c) for c in chunks],
        count=len(chunks),
    )


# ---------------------------------------------------------------------------
# OCR test endpoint
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


class OCRTestResponse(BaseModel):
    filename: str
    char_count: int
    extracted_text: str


@app.post("/ocr-test", response_model=OCRTestResponse)
async def ocr_test(
    file: UploadFile = File(..., description="Image file to OCR"),
):
    """
    Debug endpoint — upload an image, get back the raw OCR text.
    Does NOT store anything in the database.
    """
    import os as _os

    ext = _os.path.splitext(file.filename or "")[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected image file. Got '{ext}'. Allowed: {', '.join(sorted(IMAGE_EXTENSIONS))}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file."
        )

    try:
        pages, _ = extract_image_text(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )

    extracted = pages[0][1]
    return OCRTestResponse(
        filename=file.filename or "unknown",
        char_count=len(extracted),
        extracted_text=extracted,
    )


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class IngestResponse(BaseModel):
    doc_id: str
    chunk_count: int
    filename: str
    ocr_used: bool = False


@app.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(
    file: UploadFile = File(..., description="PDF or TXT file"),
    doc_type: str = Form(..., description="manual | sop | report"),
    machine_id: Optional[int] = Form(default=None),
    uploaded_by: Optional[int] = Form(default=None),
    description: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a document: extract → chunk → embed → store in pgvector."""
    import os as _os

    ext = _os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if doc_type not in ("manual", "sop", "report"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_type must be: manual, sop, or report",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE // 1024 // 1024}MB",
        )
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file."
        )

    try:
        result = await ingest_document(
            file_bytes=file_bytes,
            filename=file.filename or "document",
            doc_type=doc_type,
            db=db,
            machine_id=machine_id,
            uploaded_by=uploaded_by,
            description=description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion failed. Check RAG service logs.",
        )

    if result.get("duplicate"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate: identical file already ingested.",
                "existing_doc_id": result["doc_id"],
            },
        )

    return IngestResponse(
        doc_id=result["doc_id"],
        chunk_count=result["chunk_count"],
        filename=file.filename or "document",
        ocr_used=result.get("ocr_used", False),
    )


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


class DocumentRecord(BaseModel):
    id: str
    filename: str
    doc_type: str
    description: Optional[str] = None
    machine_id: Optional[int] = None
    chunk_count: int
    file_size_bytes: Optional[int] = None
    uploaded_by: Optional[int] = None
    uploader_name: Optional[str] = None
    created_at: Optional[str] = None


@app.get("/documents", response_model=List[DocumentRecord])
async def list_documents(
    doc_type: Optional[str] = None,
    machine_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List ingested documents with optional filters."""
    where_clauses = []
    params: dict = {}

    if doc_type:
        where_clauses.append("doc_type = :doc_type")
        params["doc_type"] = doc_type
    if machine_id is not None:
        where_clauses.append("machine_id = :machine_id")
        params["machine_id"] = machine_id

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    # nosemgrep: sqlalchemy-raw-sql-interpolation,python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text -- where_sql is a static clause skeleton (see above); values are bound via params below, not interpolated into SQL text.
    sql = text(f"""
        SELECT d.id, d.filename, d.doc_type, d.description, d.machine_id,
               d.chunk_count, d.file_size_bytes, d.uploaded_by,
               u.nom AS uploader_name,
               d.created_at
        FROM documents d
        LEFT JOIN utilisateurs u ON u.id = d.uploaded_by
        {where_sql}
        ORDER BY d.created_at DESC
        LIMIT 100
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        DocumentRecord(
            id=str(r.id),
            filename=r.filename,
            doc_type=r.doc_type,
            description=r.description,
            machine_id=r.machine_id,
            chunk_count=r.chunk_count,
            file_size_bytes=r.file_size_bytes,
            uploaded_by=r.uploaded_by,
            uploader_name=r.uploader_name,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@app.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete document and all its chunks (FK CASCADE handles chunk deletion)."""
    result = await db.execute(
        text("SELECT id FROM documents WHERE id = :id"),
        {"id": doc_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Document not found.")

    await db.execute(text("DELETE FROM documents WHERE id = :id"), {"id": doc_id})
    await db.commit()
    # Stale retrieval results may reference deleted chunks
    clear_retrieval_cache()
    return None


# ---------------------------------------------------------------------------
# Cache debug
# ---------------------------------------------------------------------------


@app.get("/cache-stats")
async def cache_stats():
    """Return embedding + retrieval cache hit/miss counters + reranker + hybrid stats."""
    return {
        "embedding_cache": embed_cache_stats(),
        "retrieval_cache": retrieve_cache_stats(),
        "reranker": rerank_stats(),
        "hybrid": hybrid_stats(),
    }


@app.get("/rerank-info")
async def rerank_info():
    """Reranker status for ops visibility."""
    return {
        "enabled": rerank_enabled(),
        "model": RERANK_MODEL,
        "overfetch": OVERFETCH,
    }


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


@app.post("/cache-clear", status_code=204)
async def cache_clear():
    """Force clear retrieval cache (embedding cache TTL is short — left as-is)."""
    clear_retrieval_cache()
    return None
