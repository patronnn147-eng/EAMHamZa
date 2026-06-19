import os
from modules.ml.services.model_registry import scan_models, check_sync, MODEL_CATALOG


def _write(d, name, data):
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(data)


def test_identical_files_match(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"same"); _write(b, fn, b"same")
    rows = scan_models(str(a), str(b))
    row = next(r for r in rows if r["filename"] == fn)
    assert row["in_backend"] and row["in_micro"] and row["hash_match"]
    assert check_sync(str(a), str(b)) == []


def test_hash_mismatch_flagged(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"one"); _write(b, fn, b"two")
    div = check_sync(str(a), str(b))
    assert {"filename": fn, "reason": "hash_mismatch"} in div


def test_missing_in_microservice(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"x")
    div = check_sync(str(a), str(b))
    assert {"filename": fn, "reason": "missing_in_microservice"} in div
