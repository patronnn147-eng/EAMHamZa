"""
RAG document management API.

File blobs live in MinIO bucket `rag-docs`; metadata + chunks in Postgres
via the rag-service container.

Routes:
- POST   /api/v1/rag/documents                  upload + ingest single file (ADMIN)
- POST   /api/v1/rag/documents/bulk             bulk import N files in parallel (ADMIN)
- GET    /api/v1/rag/documents                  list documents (any role)
- GET    /api/v1/rag/documents/{id}/download    presigned S3 URL (ADMIN)
- PUT    /api/v1/rag/documents/{id}             replace file + re-ingest (ADMIN)
- DELETE /api/v1/rag/documents/{id}             delete doc + chunks + S3 (ADMIN)
"""
import asyncio
import hashlib
import logging
import os
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs
import services.rag_client as rag_client
import services.rag_storage as rag_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
BULK_PARALLELISM = 4                    # concurrent ingests per bulk request


# ── Schemas ────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
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
    s3_object_key: Optional[str] = None
    download_url: Optional[str] = None
    version: int = 1
    content_hash: Optional[str] = None


class BulkUploadResponse(BaseModel):
    succeeded: List[DocumentResponse]
    failed: List[dict]   # [{filename, error}]
    total: int


# ── Helpers ────────────────────────────────────────────────────────────────

def _require_admin(user: Utilisateurs) -> None:
    role = (user.role.value if hasattr(user.role, "value") else str(user.role or "")).upper()
    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN can modify RAG documents.",
        )


def _validate_file(filename: str, size: int) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB",
        )
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")


async def _ingest_one(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    machine_id: Optional[int],
    description: Optional[str],
    uploaded_by: int,
    db: AsyncSession,
) -> DocumentResponse:
    """Upload to S3 → call rag-service → save s3 key → return response."""
    pre_doc_id = str(uuid.uuid4())
    object_key = rag_storage.build_object_key(pre_doc_id, filename)

    # 1. Upload to S3 BEFORE ingest so we can roll it back on chunk failure
    try:
        rag_storage.upload_bytes(file_bytes, object_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"S3 storage unavailable: {e}",
        )

    # 2. Forward to rag-service for chunk + embed
    try:
        result = await rag_client.ingest_document(
            file_bytes=file_bytes,
            filename=filename,
            doc_type=doc_type,
            machine_id=machine_id,
            uploaded_by=uploaded_by,
            description=description,
        )
    except Exception as e:
        # Roll back the S3 upload — chunks never landed
        rag_storage.delete_object(object_key)
        if isinstance(e, httpx.HTTPStatusError):
            raise HTTPException(
                status_code=e.response.status_code if e.response else 500,
                detail=f"RAG service error: {e.response.text if e.response else str(e)}",
            )
        if isinstance(e, httpx.ConnectError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG service is unavailable.",
            )
        logger.error(f"Ingest failed for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed.")

    doc_id = result["doc_id"]

    # 3. Persist S3 key on the documents row (rag-service uses its own doc_id)
    try:
        await db.execute(
            text("UPDATE documents SET s3_object_key = :k WHERE id = CAST(:id AS uuid)"),
            {"k": object_key, "id": doc_id},
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist s3_object_key for {doc_id}: {e}")

    return DocumentResponse(
        id=doc_id,
        filename=result["filename"],
        doc_type=doc_type,
        description=description,
        machine_id=machine_id,
        chunk_count=result["chunk_count"],
        file_size_bytes=len(file_bytes),
        uploaded_by=uploaded_by,
        s3_object_key=object_key,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="PDF or TXT file"),
    doc_type: str = Form(..., description="manual | sop | report"),
    machine_id: Optional[int] = Form(default=None),
    description: Optional[str] = Form(default=None),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single document — S3 + ingest. ADMIN only."""
    _require_admin(current_user)

    if doc_type not in ("manual", "sop", "report"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_type must be: manual, sop, or report",
        )

    file_bytes = await file.read()
    _validate_file(file.filename or "", len(file_bytes))

    # Dedup: reject before S3 upload if same bytes already ingested
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    existing_row = await db.execute(
        text("SELECT id::text, filename FROM documents WHERE content_hash = :h LIMIT 1"),
        {"h": content_hash},
    )
    existing = existing_row.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Identical file already ingested.",
                "existing_doc_id": existing[0],
                "existing_filename": existing[1],
            },
        )

    return await _ingest_one(
        file_bytes=file_bytes,
        filename=file.filename or "document",
        doc_type=doc_type,
        machine_id=machine_id,
        description=description,
        uploaded_by=current_user.id,
        db=db,
    )


@router.post("/documents/sync", response_model=BulkUploadResponse, status_code=200)
async def sync_from_minio(
    doc_type: str = Form(default="manual"),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan the rag-docs bucket for files that aren't yet in the documents table
    and ingest them. Useful when an admin uploads files directly into MinIO
    via the console and wants them registered as RAG sources. ADMIN only.
    """
    _require_admin(current_user)

    # 1. List S3 objects
    objects = rag_storage.list_bucket_objects()
    if not objects:
        return BulkUploadResponse(succeeded=[], failed=[], total=0)

    # 2. Get already-known keys from DB
    rows = await db.execute(text("SELECT s3_object_key FROM documents WHERE s3_object_key IS NOT NULL"))
    known_keys = {row[0] for row in rows.fetchall()}

    # 3. Filter — keep only new objects, only PDF/TXT
    new_objects = [
        o for o in objects
        if o["key"] not in known_keys
        and os.path.splitext(o["key"])[1].lower() in ALLOWED_EXTENSIONS
    ]

    if not new_objects:
        return BulkUploadResponse(succeeded=[], failed=[], total=0)

    succeeded: List[DocumentResponse] = []
    failed:    List[dict] = []

    # 4. Sequential ingest (sync is rare, no need to parallelize and stress S3)
    for obj in new_objects[:50]:  # cap at 50 per sync request
        try:
            file_bytes = rag_storage.get_object_bytes(obj["key"])
            if file_bytes is None:
                failed.append({"filename": obj["key"], "error": "S3 fetch failed"})
                continue
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                failed.append({"filename": obj["key"], "error": "File too large"})
                continue

            # Derive a friendly filename from the key (strip uuid prefix if present)
            display_name = obj["key"].split("/")[-1]

            # Inline a simplified _ingest_one: file is ALREADY in S3, do not re-upload
            result = await rag_client.ingest_document(
                file_bytes=file_bytes,
                filename=display_name,
                doc_type=doc_type,
                machine_id=None,
                uploaded_by=current_user.id,
                description="Synced from S3",
            )
            doc_id = result["doc_id"]
            await db.execute(
                text("UPDATE documents SET s3_object_key = :k WHERE id = CAST(:id AS uuid)"),
                {"k": obj["key"], "id": doc_id},
            )
            await db.commit()

            succeeded.append(DocumentResponse(
                id=doc_id,
                filename=result["filename"],
                doc_type=doc_type,
                description="Synced from S3",
                machine_id=None,
                chunk_count=result["chunk_count"],
                file_size_bytes=len(file_bytes),
                uploaded_by=current_user.id,
                s3_object_key=obj["key"],
            ))
        except Exception as e:
            logger.error(f"Sync failed for {obj['key']}: {e}")
            failed.append({"filename": obj["key"], "error": str(e)})

    return BulkUploadResponse(succeeded=succeeded, failed=failed, total=len(new_objects))


@router.post("/documents/bulk", response_model=BulkUploadResponse, status_code=201)
async def bulk_upload_documents(
    files: List[UploadFile] = File(..., description="Multiple PDF/TXT files"),
    doc_type: str = Form(default="manual"),
    machine_id: Optional[int] = Form(default=None),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import N documents for RAG training. Runs ingests in parallel
    (max BULK_PARALLELISM at a time). Per-file errors are reported,
    successful files are still saved. ADMIN only.
    """
    _require_admin(current_user)

    if doc_type not in ("manual", "sop", "report"):
        raise HTTPException(status_code=400, detail="Invalid doc_type")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Max 50 files per bulk request")

    semaphore = asyncio.Semaphore(BULK_PARALLELISM)
    succeeded: List[DocumentResponse] = []
    failed:    List[dict] = []

    async def _process(f: UploadFile) -> None:
        async with semaphore:
            try:
                file_bytes = await f.read()
                _validate_file(f.filename or "", len(file_bytes))
                content_hash = hashlib.sha256(file_bytes).hexdigest()
                dup_row = await db.execute(
                    text("SELECT id::text FROM documents WHERE content_hash = :h LIMIT 1"),
                    {"h": content_hash},
                )
                dup = dup_row.first()
                if dup:
                    failed.append({
                        "filename": f.filename,
                        "error": f"Duplicate: already ingested as {dup[0]}",
                    })
                    return
                result = await _ingest_one(
                    file_bytes=file_bytes,
                    filename=f.filename or "document",
                    doc_type=doc_type,
                    machine_id=machine_id,
                    description=None,
                    uploaded_by=current_user.id,
                    db=db,
                )
                succeeded.append(result)
            except HTTPException as he:
                failed.append({"filename": f.filename, "error": he.detail})
            except Exception as e:
                failed.append({"filename": f.filename, "error": str(e)})

    await asyncio.gather(*[_process(f) for f in files])

    return BulkUploadResponse(
        succeeded=succeeded,
        failed=failed,
        total=len(files),
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    doc_type: Optional[str] = None,
    machine_id: Optional[int] = None,
    include_download_url: bool = False,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents. Admins can request presigned download URLs."""
    try:
        docs = await rag_client.list_documents(doc_type=doc_type, machine_id=machine_id)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="RAG service is unavailable.")
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document list.")

    # Fetch s3_object_key directly from documents table (rag-service doesn't know about it)
    doc_ids = [d["id"] for d in docs]
    s3_map: dict[str, str] = {}
    if doc_ids:
        rows = await db.execute(
            text("SELECT id::text AS id, s3_object_key FROM documents WHERE id::text = ANY(:ids)"),
            {"ids": doc_ids},
        )
        for row in rows.mappings():
            if row["s3_object_key"]:
                s3_map[row["id"]] = row["s3_object_key"]

    role = (current_user.role.value if hasattr(current_user.role, "value")
            else str(current_user.role or "")).upper()
    is_admin = role == "ADMIN"

    out: List[DocumentResponse] = []
    for d in docs:
        key = s3_map.get(d["id"])
        download_url = None
        if include_download_url and is_admin and key:
            download_url = rag_storage.presigned_download_url(key)
        out.append(DocumentResponse(
            **d,
            s3_object_key=key,
            download_url=download_url,
        ))
    return out


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return presigned URL for the doc file. ADMIN only."""
    _require_admin(current_user)
    row = await db.execute(
        text("SELECT s3_object_key FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": doc_id},
    )
    record = row.first()
    if not record or not record[0]:
        raise HTTPException(status_code=404, detail="File not stored in S3.")
    url = rag_storage.presigned_download_url(record[0])
    if not url:
        raise HTTPException(status_code=503, detail="Storage backend unavailable.")
    return {"download_url": url}


@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def replace_document(
    doc_id: str,
    file: UploadFile = File(..., description="Replacement PDF/TXT"),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Replace a document's file: deletes old chunks + old S3 object,
    uploads new file, re-ingests. Keeps the SAME doc_id. ADMIN only.
    """
    _require_admin(current_user)

    # Load existing metadata (doc_type/description/machine_id/version)
    row = await db.execute(
        text("""
            SELECT doc_type, description, machine_id, s3_object_key, COALESCE(version, 1) AS version
            FROM documents WHERE id = CAST(:id AS uuid)
        """),
        {"id": doc_id},
    )
    record = row.first()
    if not record:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_type, description, machine_id, old_key, current_version = record

    file_bytes = await file.read()
    _validate_file(file.filename or "", len(file_bytes))

    # 1. Delete old chunks via rag-service
    try:
        await rag_client.delete_document(doc_id)
    except Exception as e:
        logger.warning(f"Old chunk delete failed for {doc_id}: {e}")

    # 2. Delete old S3 object
    if old_key:
        rag_storage.delete_object(old_key)

    # 3. Ingest new — uses fresh doc_id from rag-service
    new_doc = await _ingest_one(
        file_bytes=file_bytes,
        filename=file.filename or "document",
        doc_type=doc_type,
        machine_id=machine_id,
        description=description,
        uploaded_by=current_user.id,
        db=db,
    )

    # Stamp new document row with version = old_version + 1
    try:
        await db.execute(
            text("UPDATE documents SET version = :v WHERE id = CAST(:id AS uuid)"),
            {"v": current_version + 1, "id": new_doc.id},
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to set version for {new_doc.id}: {e}")

    return new_doc


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete doc, chunks, and S3 file. ADMIN only."""
    _require_admin(current_user)

    # Get S3 key before delete
    row = await db.execute(
        text("SELECT s3_object_key FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": doc_id},
    )
    record = row.first()
    s3_key = record[0] if record else None

    # 1. Delete doc + chunks in rag-service / DB
    try:
        await rag_client.delete_document(doc_id)
    except httpx.HTTPStatusError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Document not found.")
        raise HTTPException(status_code=500, detail="Failed to delete document.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="RAG service is unavailable.")

    # 2. Best-effort S3 cleanup
    if s3_key:
        rag_storage.delete_object(s3_key)

    return None
