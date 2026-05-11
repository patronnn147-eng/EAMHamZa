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
from ingestor import ingest_document
from retriever import retrieve_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EAM RAG Service", version="1.0.0")

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
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
# Ingestion
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    doc_id: str
    chunk_count: int
    filename: str


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
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")

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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion failed. Check RAG service logs.",
        )

    return IngestResponse(
        doc_id=result["doc_id"],
        chunk_count=result["chunk_count"],
        filename=file.filename or "document",
    )


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------

class DocumentRecord(BaseModel):
    id: str
    filename: str
    doc_type: str
    description: Optional[str]
    machine_id: Optional[int]
    chunk_count: int
    file_size_bytes: Optional[int]
    uploaded_by: Optional[int]


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
    sql = text(f"""
        SELECT id, filename, doc_type, description, machine_id,
               chunk_count, file_size_bytes, uploaded_by
        FROM documents
        {where_sql}
        ORDER BY created_at DESC
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
    return None
