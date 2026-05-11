"""
RAG document management API — proxies to rag-service container.

POST   /api/v1/rag/documents          — upload + ingest PDF or TXT
GET    /api/v1/rag/documents          — list all documents
DELETE /api/v1/rag/documents/{id}     — delete doc + all chunks
"""
import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
import services.rag_client as rag_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


class DocumentResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    description: Optional[str] = None
    machine_id: Optional[int] = None
    chunk_count: int
    file_size_bytes: Optional[int] = None
    uploaded_by: Optional[int] = None


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="PDF or TXT file"),
    doc_type: str = Form(..., description="manual | sop | report"),
    machine_id: Optional[int] = Form(default=None, description="Link to specific machine"),
    description: Optional[str] = Form(default=None),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Upload and ingest a document into the RAG vector store."""
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
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
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB",
        )
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")

    try:
        result = await rag_client.ingest_document(
            file_bytes=file_bytes,
            filename=file.filename or "document",
            doc_type=doc_type,
            machine_id=machine_id,
            uploaded_by=current_user.id,
            description=description,
        )
    except httpx.HTTPStatusError as e:
        body = e.response.text if e.response else str(e)
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"RAG service error: {body}",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is unavailable.",
        )
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion failed.",
        )

    return DocumentResponse(
        id=result["doc_id"],
        filename=result["filename"],
        doc_type=doc_type,
        description=description,
        machine_id=machine_id,
        chunk_count=result["chunk_count"],
        file_size_bytes=len(file_bytes),
        uploaded_by=current_user.id,
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    doc_type: Optional[str] = None,
    machine_id: Optional[int] = None,
    current_user: Utilisateurs = Depends(get_current_user),
):
    """List all ingested documents with optional filters."""
    try:
        docs = await rag_client.list_documents(doc_type=doc_type, machine_id=machine_id)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is unavailable.",
        )
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list.",
        )

    return [DocumentResponse(**d) for d in docs]


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Delete document and all its chunks."""
    try:
        await rag_client.delete_document(doc_id)
    except httpx.HTTPStatusError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Document not found.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document.",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is unavailable.",
        )
    return None
