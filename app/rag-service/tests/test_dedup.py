import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestor import _compute_hash


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
