import hashlib
import sys
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestor import _compute_hash, ingest_document


def test_compute_hash_deterministic():
    data = b"hello world"
    assert _compute_hash(data) == _compute_hash(data)


def test_compute_hash_known_value():
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert _compute_hash(b"hello world") == expected
    assert len(_compute_hash(b"hello world")) == 64


def test_compute_hash_different_content():
    assert _compute_hash(b"file_v1") != _compute_hash(b"file_v2")


def test_compute_hash_empty():
    expected = hashlib.sha256(b"").hexdigest()
    assert _compute_hash(b"") == expected


@pytest.mark.asyncio
async def test_ingest_document_returns_duplicate_flag_when_hash_exists():
    """When DB has a row with same content_hash, ingest_document returns duplicate flag without inserting."""
    existing_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    file_bytes = b"%PDF fake pdf content unique"

    mock_db = AsyncMock()
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
    assert mock_db.execute.call_count == 1
