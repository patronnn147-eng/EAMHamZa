# Doc Versioning + Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent duplicate document chunks from poisoning the RAG corpus — detect identical file content on upload and reject with 409, store a sha256 hash + version number on every document.

**Architecture:** The backend computes sha256 of file bytes before S3 upload and queries the `documents` table directly; a matching hash returns 409 immediately (no S3 write, no rag-service call). The rag-service ingestor also stores the hash on INSERT and includes a race-condition guard. The PUT (replace) endpoint increments the `version` column. A UNIQUE constraint on `content_hash` enforces dedup at the DB layer.

**Tech Stack:** Python `hashlib` (stdlib), SQLAlchemy raw SQL (existing pattern), Alembic (existing), pytest (existing in rag-service tests)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/backend/alembic/versions/doc_versioning_dedup.py` | Add `content_hash VARCHAR(64) UNIQUE` + `version INT DEFAULT 1` to `documents` |
| Modify | `app/rag-service/ingestor.py` | `_compute_hash()` helper + hash in INSERT + race-condition guard |
| Modify | `app/rag-service/main.py` | Convert duplicate return value to HTTP 409 response |
| Modify | `app/backend/modules/shared/routes/rag_docs.py` | Pre-check hash before S3 upload; PUT increments version |
| Create | `app/rag-service/tests/test_dedup.py` | Unit tests for hash computation + duplicate detection |

---

## Task 1: Alembic Migration — content_hash + version columns

**Files:**
- Create: `app/backend/alembic/versions/doc_versioning_dedup.py`

- [ ] **Step 1: Create the migration file**

```python
# app/backend/alembic/versions/doc_versioning_dedup.py
"""Add content_hash and version columns to documents for dedup support.

content_hash: sha256 hex digest of the raw file bytes. UNIQUE — DB-level dedup guard.
              NULL allowed for documents ingested before this migration.
version: integer counter, starts at 1, incremented on each PUT replace.

Revision ID: doc_versioning_dedup
Revises: hybrid_search_tsvector
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "doc_versioning_dedup"
down_revision: Union[str, Sequence[str], None] = "hybrid_search_tsvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _column_exists("documents", "content_hash"):
        op.add_column(
            "documents",
            sa.Column("content_hash", sa.String(64), nullable=True),
        )
        # UNIQUE index allows multiple NULLs (pre-migration rows)
        op.create_index(
            "uq_documents_content_hash",
            "documents",
            ["content_hash"],
            unique=True,
            postgresql_where=sa.text("content_hash IS NOT NULL"),
        )

    if not _column_exists("documents", "version"):
        op.add_column(
            "documents",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_index("uq_documents_content_hash", table_name="documents")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "version")
```

- [ ] **Step 2: Run the migration**

```bash
docker compose exec backend alembic upgrade head
```

Expected output ends with: `Running upgrade hybrid_search_tsvector -> doc_versioning_dedup`

- [ ] **Step 3: Verify columns exist**

```bash
docker compose exec db psql -U postgres -d eam_db -c "\d documents"
```

Expected: `content_hash` (character varying(64), nullable) and `version` (integer, not null, default 1) visible in the column list.

- [ ] **Step 4: Commit**

```bash
git add app/backend/alembic/versions/doc_versioning_dedup.py
git commit -m "feat(rag): add content_hash + version columns to documents via migration"
```

---

## Task 2: Hash Computation in Ingestor

**Files:**
- Modify: `app/rag-service/ingestor.py`

- [ ] **Step 1: Write the failing test**

Create `app/rag-service/tests/test_dedup.py`:

```python
# app/rag-service/tests/test_dedup.py
import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestor import _compute_hash


def test_compute_hash_deterministic():
    """Same bytes always produce the same sha256 hex string."""
    data = b"hello world"
    assert _compute_hash(data) == _compute_hash(data)


def test_compute_hash_known_value():
    """sha256 of b'hello world' is a known constant."""
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert _compute_hash(b"hello world") == expected
    assert len(_compute_hash(b"hello world")) == 64


def test_compute_hash_different_content():
    """Different byte sequences produce different hashes."""
    assert _compute_hash(b"file_v1") != _compute_hash(b"file_v2")


def test_compute_hash_empty():
    """Empty bytes has a deterministic sha256."""
    expected = hashlib.sha256(b"").hexdigest()
    assert _compute_hash(b"") == expected
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec rag-service pytest tests/test_dedup.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name '_compute_hash' from 'ingestor'`

- [ ] **Step 3: Add `_compute_hash` to ingestor.py**

Add `import hashlib` at the top of `app/rag-service/ingestor.py` alongside existing imports:

```python
import hashlib
```

Add the function immediately before the `extract_pdf_text` function (after the OCR imports block, around line 37):

```python
def _compute_hash(file_bytes: bytes) -> str:
    """Return sha256 hex digest of raw file bytes. Used for exact-duplicate detection."""
    return hashlib.sha256(file_bytes).hexdigest()
```

- [ ] **Step 4: Run tests — should pass**

```bash
docker compose exec rag-service pytest tests/test_dedup.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add app/rag-service/ingestor.py app/rag-service/tests/test_dedup.py
git commit -m "feat(rag): add _compute_hash helper to ingestor + unit tests"
```

---

## Task 3: Store Hash in INSERT + Race-Condition Guard

**Files:**
- Modify: `app/rag-service/ingestor.py` (the `ingest_document` function)

- [ ] **Step 1: Write the failing test**

Add to `app/rag-service/tests/test_dedup.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from ingestor import ingest_document


@pytest.mark.asyncio
async def test_ingest_document_returns_duplicate_flag_when_hash_exists():
    """When the DB already has a row with the same content_hash, ingest_document
    returns {"duplicate": True, "doc_id": existing_id, ...} without inserting."""
    existing_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    file_bytes = b"%PDF fake pdf content unique"

    mock_db = AsyncMock()

    # First execute: SELECT content_hash → returns a row
    hash_check_result = MagicMock()
    hash_check_result.first.return_value = (existing_id,)

    mock_db.execute.return_value = hash_check_result

    with patch("ingestor.extract_pdf_text", return_value=([(1, "some text")], False)), \
         patch("ingestor.embed_batch", new_callable=AsyncMock, return_value=[[0.1] * 1024]):
        result = await ingest_document(
            file_bytes=file_bytes,
            filename="test.pdf",
            doc_type="manual",
            db=mock_db,
        )

    assert result["duplicate"] is True
    assert result["doc_id"] == existing_id
    # DB execute called only once (the hash check SELECT), no INSERT
    assert mock_db.execute.call_count == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec rag-service pytest tests/test_dedup.py::test_ingest_document_returns_duplicate_flag_when_hash_exists -v
```

Expected: `FAILED` — `ingest_document` does no hash check currently.

- [ ] **Step 3: Update `ingest_document` in ingestor.py**

In `ingest_document`, replace the current step 1 ("# 1. Extract text") section header block. The function currently starts with the extension lookup. Add hash computation and duplicate check BEFORE the text extraction, and include `content_hash` + `version` in the INSERT.

Replace the beginning of `ingest_document` (from `ext = filename.rsplit(...)` down to just before `# 2. Insert document record`) with:

```python
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # 0. Compute content hash for dedup
    content_hash = _compute_hash(file_bytes)

    # Race-condition guard: check if this exact file was already ingested
    existing = await db.execute(
        text("SELECT id FROM documents WHERE content_hash = :h LIMIT 1"),
        {"h": content_hash},
    )
    dup_row = existing.first()
    if dup_row:
        logger.info(f"Duplicate detected hash={content_hash[:12]}… existing_id={dup_row[0]}")
        return {"duplicate": True, "doc_id": str(dup_row[0]), "chunk_count": 0, "ocr_used": False}

    # 1. Extract text
```

Then update the `# 2. Insert document record` SQL to include `content_hash` and `version`:

```python
    # 2. Insert document record (raw SQL — no ORM models in this service)
    doc_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO documents (id, filename, doc_type, description, machine_id,
                                   uploaded_by, file_size_bytes, content_hash, version)
            VALUES (:id, :filename, :doc_type, :description, :machine_id,
                    :uploaded_by, :file_size_bytes, :content_hash, :version)
        """),
        {
            "id": doc_id,
            "filename": filename,
            "doc_type": doc_type,
            "description": description,
            "machine_id": machine_id,
            "uploaded_by": uploaded_by,
            "file_size_bytes": len(file_bytes),
            "content_hash": content_hash,
            "version": 1,
        },
    )
```

- [ ] **Step 4: Run tests**

```bash
docker compose exec rag-service pytest tests/test_dedup.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add app/rag-service/ingestor.py app/rag-service/tests/test_dedup.py
git commit -m "feat(rag): store content_hash+version on ingest, return duplicate flag on exact match"
```

---

## Task 4: Rag-Service `/ingest` Returns 409 on Duplicate

**Files:**
- Modify: `app/rag-service/main.py`

- [ ] **Step 1: Write the failing test**

Add to `app/rag-service/tests/test_dedup.py`:

```python
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app

client = TestClient(app)


def test_ingest_returns_409_when_duplicate():
    """POST /ingest returns 409 with existing_doc_id when ingest_document detects duplicate."""
    existing_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    async def mock_ingest(*args, **kwargs):
        return {"duplicate": True, "doc_id": existing_id, "chunk_count": 0, "ocr_used": False}

    with patch("main.ingest_document", side_effect=mock_ingest), \
         patch("main.get_db"):
        response = client.post(
            "/ingest",
            files={"file": ("test.pdf", b"%PDF fake", "application/pdf")},
            data={"doc_type": "manual"},
        )

    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["existing_doc_id"] == existing_id
    assert "duplicate" in body["detail"]["message"].lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec rag-service pytest tests/test_dedup.py::test_ingest_returns_409_when_duplicate -v
```

Expected: `FAILED` — 201 returned instead of 409.

- [ ] **Step 3: Update `/ingest` endpoint in main.py**

In `app/rag-service/main.py`, find the `try:` block inside the `/ingest` handler that calls `ingest_document` and returns `IngestResponse`. After the `result = await ingest_document(...)` line, add the duplicate check:

```python
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

    if result.get("duplicate"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Identical file already ingested.",
                "existing_doc_id": result["doc_id"],
            },
        )

    return IngestResponse(
        doc_id=result["doc_id"],
        chunk_count=result["chunk_count"],
        filename=file.filename or "document",
        ocr_used=result.get("ocr_used", False),
    )
```

The `if result.get("duplicate")` block must be placed AFTER the `except` block and BEFORE the `return IngestResponse(...)`.

- [ ] **Step 4: Run tests**

```bash
docker compose exec rag-service pytest tests/test_dedup.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add app/rag-service/main.py app/rag-service/tests/test_dedup.py
git commit -m "feat(rag): /ingest returns HTTP 409 with existing_doc_id on duplicate content"
```

---

## Task 5: Backend Pre-Check Before S3 Upload

**Files:**
- Modify: `app/backend/modules/shared/routes/rag_docs.py`

The backend checks the hash BEFORE uploading to S3, avoiding an upload + rollback on every duplicate.

- [ ] **Step 1: Add `import hashlib` to rag_docs.py**

At the top of `app/backend/modules/shared/routes/rag_docs.py`, add `import hashlib` alongside the existing `import os`:

```python
import hashlib
```

- [ ] **Step 2: Add hash pre-check to `upload_document` endpoint**

In the `upload_document` handler in `rag_docs.py`, after `_validate_file(file.filename or "", len(file_bytes))`, add:

```python
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
```

- [ ] **Step 3: Add hash pre-check to `bulk_upload_documents` endpoint**

In `_process` inside `bulk_upload_documents`, after `_validate_file(f.filename or "", len(file_bytes))`, add:

```python
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
```

- [ ] **Step 4: Manual smoke test — duplicate upload**

```bash
# Upload a file once
curl -s -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@/path/to/any.pdf" \
  -F "doc_type=manual" | jq .

# Upload the SAME file again — should return 409
curl -s -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@/path/to/any.pdf" \
  -F "doc_type=manual" | jq .
```

Expected second response: `{"detail": {"message": "Identical file already ingested.", "existing_doc_id": "...", "existing_filename": "..."}}`

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/shared/routes/rag_docs.py
git commit -m "feat(rag): pre-check content_hash before S3 upload to prevent duplicate ingestion"
```

---

## Task 6: PUT Increments Version on Replace

**Files:**
- Modify: `app/backend/modules/shared/routes/rag_docs.py` (`replace_document` handler)

- [ ] **Step 1: Update `replace_document` to bump version**

In the `replace_document` handler, the existing query loads `doc_type, description, machine_id, s3_object_key`. Add `version` to that SELECT, then pass `version + 1` to the new ingestion, and update the `documents` row after ingest.

Replace the existing SELECT in `replace_document`:

```python
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
```

After `new_doc = await _ingest_one(...)`, add the version bump:

```python
    # Stamp the new document row with version = old_version + 1
    try:
        await db.execute(
            text("UPDATE documents SET version = :v WHERE id = CAST(:id AS uuid)"),
            {"v": current_version + 1, "id": new_doc.id},
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to set version for {new_doc.id}: {e}")

    return new_doc
```

- [ ] **Step 2: Add `version` field to `DocumentResponse` schema**

In `rag_docs.py`, update `DocumentResponse`:

```python
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
```

- [ ] **Step 3: Run all existing rag-service tests to check for regressions**

```bash
docker compose exec rag-service pytest tests/ -v
```

Expected: all existing tests still pass (the new `version` and `content_hash` fields in `ingest_document`'s INSERT statement may require DB to be running — these are integration-style tests, skip with `-k "not integration"` if DB unavailable in test env).

- [ ] **Step 4: Commit**

```bash
git add app/backend/modules/shared/routes/rag_docs.py
git commit -m "feat(rag): increment version on document replace (PUT), expose version+hash in DocumentResponse"
```

---

## Task 7: Final Integration Smoke Test

- [ ] **Step 1: Run full migration stack**

```bash
docker compose exec backend alembic upgrade head
```

Expected: already at `doc_versioning_dedup`, no-op.

- [ ] **Step 2: Upload a fresh document**

```bash
curl -s -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@app/ml-microservice/ml_research/README.md" \
  -F "doc_type=manual" | jq '{id, filename, version, content_hash}'
```

Expected: `version: 1`, `content_hash: "<64-char hex>"`

- [ ] **Step 3: Upload the same file again — expect 409**

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@app/ml-microservice/ml_research/README.md" \
  -F "doc_type=manual"
```

Expected: `409`

- [ ] **Step 4: Replace document via PUT — expect version 2**

```bash
DOC_ID="<id from Step 2>"
curl -s -X PUT http://localhost:8000/api/v1/rag/documents/$DOC_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@CLAUDE.md" | jq '{id, version}'
```

Expected: `version: 2`

- [ ] **Step 5: Run all rag-service tests**

```bash
docker compose exec rag-service pytest tests/ -v
```

Expected: all green.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat(rag): doc versioning + dedup complete — hash check, 409 on duplicate, version increment on replace"
```
