"""
Document ingestion pipeline.

PDF → text extraction (PyMuPDF) → sentence-aware chunking → batch embed → pgvector store.
"""
import io
import logging
import re
import uuid
from typing import Optional

import fitz  # pymupdf — import name is fitz, NOT pymupdf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from embedder import embed_batch, vec_to_str
from retriever import clear_retrieval_cache

logger = logging.getLogger(__name__)

CHUNK_SIZE = 200   # words  — smaller chunks = sharper per-topic embeddings
CHUNK_OVERLAP = 20  # words

# OCR settings
OCR_LANG = "fra+eng"   # French + English — matches installed tesseract language packs
OCR_ZOOM = 3.0         # render at 3x (≈216 DPI) for sharper OCR; higher = slower
OCR_MIN_CHARS = 10     # a page must yield > this many chars to count as text

# Lazy import — pytesseract/Pillow only needed when a PDF has no text layer
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed — OCR fallback disabled.")


# ---------------------------------------------------------------------------
# PDF + text extraction
# ---------------------------------------------------------------------------

def _ocr_page(page: "fitz.Page") -> str:
    """Render a PDF page to an image and OCR it. Returns extracted text (may be empty)."""
    if not _OCR_AVAILABLE:
        return ""
    try:
        matrix = fitz.Matrix(OCR_ZOOM, OCR_ZOOM)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text_out = pytesseract.image_to_string(img, lang=OCR_LANG)
        return text_out.strip()
    except Exception as e:
        logger.warning(f"OCR failed on page: {e}")
        return ""


def extract_pdf_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """
    Extract (page_num, text) pairs from PDF bytes.

    Strategy per page:
      1. Try native text layer (fast, accurate for digital PDFs).
      2. If a page has no/too-little text, fall back to OCR (scanned/image PDFs).

    Raises ValueError only if BOTH text extraction and OCR yield nothing.
    """
    pages: list[tuple[int, str]] = []
    ocr_used = False

    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
        for page_num, page in enumerate(pdf, start=1):
            native = page.get_text("text").strip()
            if len(native) > OCR_MIN_CHARS:
                pages.append((page_num, native))
                continue

            # Native extraction empty/weak → OCR fallback
            ocr_text = _ocr_page(page)
            if len(ocr_text) > OCR_MIN_CHARS:
                ocr_used = True
                pages.append((page_num, ocr_text))

    if not pages:
        if not _OCR_AVAILABLE:
            raise ValueError(
                "PDF has no text layer and OCR is unavailable. "
                "Install tesseract-ocr in the rag-service image."
            )
        raise ValueError("PDF contains no extractable text, even after OCR (blank or unreadable).")

    if ocr_used:
        logger.info("OCR fallback was used for at least one page of this PDF.")
    return pages, ocr_used


def extract_txt_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """Decode plain text file as single page."""
    text = file_bytes.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Text file is empty.")
    return [(1, text)], False


def extract_image_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """OCR an image file directly. Requires pytesseract + Pillow."""
    if not _OCR_AVAILABLE:
        raise ValueError("OCR unavailable — pytesseract/Pillow not installed.")
    try:
        img = Image.open(io.BytesIO(file_bytes))
        extracted = pytesseract.image_to_string(img, lang=OCR_LANG).strip()
    except Exception as e:
        raise ValueError(f"Image OCR failed: {e}")
    if len(extracted) <= OCR_MIN_CHARS:
        raise ValueError("Image contains no readable text after OCR.")
    return [(1, extracted)], True


def extract_docx_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """Extract text from .docx — paragraphs + table cells, one page per section break."""
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        raise ValueError("python-docx not installed — DOCX ingestion unavailable.")

    doc = Document(io.BytesIO(file_bytes))
    pages: list[tuple[int, str]] = []
    current_parts: list[str] = []
    page_num = 1

    for para in doc.paragraphs:
        # Section/page break → flush current page
        for run in para.runs:
            br = run._r.find(qn("w:br"))
            if br is not None and br.get(qn("w:type")) in ("page", "column"):
                if current_parts:
                    pages.append((page_num, "\n".join(current_parts)))
                    page_num += 1
                    current_parts = []
        if para.text.strip():
            current_parts.append(para.text.strip())

    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
            if row_text:
                current_parts.append(row_text)

    if current_parts:
        pages.append((page_num, "\n".join(current_parts)))

    if not pages:
        raise ValueError("DOCX contains no extractable text.")
    return pages, False


def extract_xlsx_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """Extract text from .xlsx — one page per worksheet."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl not installed — XLSX ingestion unavailable.")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    pages: list[tuple[int, str]] = []

    for sheet_num, sheet in enumerate(wb.worksheets, start=1):
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None and str(c).strip()]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            header = f"[Sheet: {sheet.title}]\n"
            pages.append((sheet_num, header + "\n".join(rows)))

    wb.close()
    if not pages:
        raise ValueError("XLSX contains no extractable text.")
    return pages, False


def extract_html_text(file_bytes: bytes) -> tuple[list[tuple[int, str]], bool]:
    """Strip HTML tags and return visible text as single page."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ValueError("beautifulsoup4 not installed — HTML ingestion unavailable.")

    soup = BeautifulSoup(file_bytes.decode("utf-8", errors="ignore"), "lxml")
    for tag in soup(["script", "style", "head", "meta", "noscript"]):
        tag.decompose()
    extracted = soup.get_text(separator="\n").strip()
    extracted = re.sub(r"\n{3,}", "\n\n", extracted)

    if len(extracted) <= OCR_MIN_CHARS:
        raise ValueError("HTML contains no readable text.")
    return [(1, extracted)], False


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
    _extractors = {
        "pdf":  extract_pdf_text,
        "txt":  extract_txt_text,
        "png":  extract_image_text,
        "jpg":  extract_image_text,
        "jpeg": extract_image_text,
        "tiff": extract_image_text,
        "tif":  extract_image_text,
        "bmp":  extract_image_text,
        "webp": extract_image_text,
        "docx": extract_docx_text,
        "xlsx": extract_xlsx_text,
        "html": extract_html_text,
        "htm":  extract_html_text,
    }
    if ext not in _extractors:
        raise ValueError(f"Unsupported file type: .{ext}")
    text_pages, ocr_used = _extractors[ext](file_bytes)

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
                        CAST(:embedding AS vector(1024)), :metadata)
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
    # Invalidate retrieval cache — new chunks may match existing queries
    clear_retrieval_cache()
    logger.info(f"Ingested doc={doc_id} filename={filename} chunks={chunk_count} ocr={ocr_used}")

    return {"doc_id": doc_id, "chunk_count": chunk_count, "ocr_used": ocr_used}
