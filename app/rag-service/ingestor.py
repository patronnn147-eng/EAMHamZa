"""
Document ingestion pipeline.

PDF → text extraction (PyMuPDF) → sentence-aware chunking → batch embed → pgvector store.
"""
import logging
import re
import uuid
from typing import Optional

import fitz  # pymupdf — import name is fitz, NOT pymupdf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from embedder import embed_batch, vec_to_str

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512   # words
CHUNK_OVERLAP = 50  # words


# ---------------------------------------------------------------------------
# PDF + text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(file_bytes: bytes) -> list[tuple[int, str]]:
    """Extract (page_num, text) pairs from PDF bytes. Skips blank pages."""
    pages = []
    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
        for page_num, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((page_num, text))
    if not pages:
        raise ValueError("PDF contains no extractable text (scanned image or empty).")
    return pages


def extract_txt_text(file_bytes: bytes) -> list[tuple[int, str]]:
    """Decode plain text file as single page."""
    text = file_bytes.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Text file is empty.")
    return [(1, text)]


# ---------------------------------------------------------------------------
# Sentence-aware chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Sentence-aware recursive chunking.

    Splits on sentence boundaries first, then accumulates words up to chunk_size.
    Overlap keeps last `overlap` words of previous chunk at start of next chunk.
    """
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        words = sentence.split()
        if not words:
            continue

        if current_len + len(words) > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep overlap words from end of current chunk
            overlap_words = current[-overlap:] if len(current) > overlap else current[:]
            current = overlap_words + words
            current_len = len(current)
        else:
            current.extend(words)
            current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    # Filter out tiny/empty chunks
    return [c for c in chunks if len(c.strip()) > 20]


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

async def ingest_document(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    db: AsyncSession,
    machine_id: Optional[int] = None,
    uploaded_by: Optional[int] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Full ingestion pipeline:
    1. Extract text (PDF or TXT)
    2. Insert document record
    3. Chunk all pages
    4. Batch embed (32 at a time)
    5. Insert chunks with vector embeddings

    Returns dict with doc_id and chunk_count.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # 1. Extract text
    if ext == "pdf":
        text_pages = extract_pdf_text(file_bytes)
    elif ext == "txt":
        text_pages = extract_txt_text(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    # 2. Insert document record (raw SQL — no ORM models in this service)
    doc_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO documents (id, filename, doc_type, description, machine_id,
                                   uploaded_by, file_size_bytes)
            VALUES (:id, :filename, :doc_type, :description, :machine_id,
                    :uploaded_by, :file_size_bytes)
        """),
        {
            "id": doc_id,
            "filename": filename,
            "doc_type": doc_type,
            "description": description,
            "machine_id": machine_id,
            "uploaded_by": uploaded_by,
            "file_size_bytes": len(file_bytes),
        },
    )

    # 3. Build all chunks with metadata
    all_chunks: list[tuple[str, dict]] = []
    for page_num, page_text in text_pages:
        for chunk in chunk_text(page_text):
            all_chunks.append((
                chunk,
                {
                    "page": page_num,
                    "filename": filename,
                    "doc_type": doc_type,
                    "machine_id": machine_id,
                },
            ))

    if not all_chunks:
        raise ValueError("Document produced no chunks after extraction.")

    # 4. Embed in batches of 32
    texts = [c[0] for c in all_chunks]
    vectors = await embed_batch(texts)

    # 5. Insert chunks
    import json
    for idx, ((chunk_content, meta), vector) in enumerate(zip(all_chunks, vectors)):
        vec_str = vec_to_str(vector)
        await db.execute(
            text("""
                INSERT INTO doc_chunks (id, doc_id, chunk_index, content, embedding, metadata)
                VALUES (:id, :doc_id, :chunk_index, :content,
                        CAST(:embedding AS vector(384)), :metadata)
            """),
            {
                "id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "chunk_index": idx,
                "content": chunk_content,
                "embedding": vec_str,
                "metadata": json.dumps(meta),
            },
        )

    chunk_count = len(all_chunks)

    # 6. Update chunk_count on document
    await db.execute(
        text("UPDATE documents SET chunk_count = :count WHERE id = :id"),
        {"count": chunk_count, "id": doc_id},
    )

    await db.commit()
    logger.info(f"Ingested doc={doc_id} filename={filename} chunks={chunk_count}")

    return {"doc_id": doc_id, "chunk_count": chunk_count}
