"""Model registry + pkl-sync check across the two model directories."""

import hashlib
import os

MODEL_CATALOG = [
    {
        "key": "p1",
        "label": "Probabilité de panne",
        "filename": "basic_machine_model.pkl",
    },
    {"key": "p2", "label": "Type de panne", "filename": "ml_model_p2_failure_type.pkl"},
    {"key": "p3", "label": "Durée de vie restante", "filename": "ml_model_p3_rul.pkl"},
    {
        "key": "p4",
        "label": "Détection d'anomalie",
        "filename": "ml_model_p4_anomaly_v2.pkl",
    },
    {"key": "p5", "label": "Priorité", "filename": "ml_model_p5_priority.pkl"},
    {"key": "p6", "label": "Planification", "filename": "ml_model_p6_schedule.pkl"},
    {
        "key": "p7",
        "label": "Besoin en pièces",
        "filename": "ml_model_p7_parts_demand.pkl",
    },
]


def _file_hash(path: str):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def scan_models(backend_dir: str, micro_dir: str) -> list:
    out = []
    for m in MODEL_CATALOG:
        bp = os.path.join(backend_dir, m["filename"])
        mp = os.path.join(micro_dir, m["filename"])
        bh, mh = _file_hash(bp), _file_hash(mp)
        out.append(
            {
                **m,
                "in_backend": bh is not None,
                "in_micro": mh is not None,
                "hash_match": bh is not None and bh == mh,
                "size_backend": os.path.getsize(bp) if bh else None,
                "mtime_backend": os.path.getmtime(bp) if bh else None,
            }
        )
    return out


def check_sync(backend_dir: str, micro_dir: str) -> list:
    div = []
    for m in MODEL_CATALOG:
        bp = os.path.join(backend_dir, m["filename"])
        mp = os.path.join(micro_dir, m["filename"])
        bh, mh = _file_hash(bp), _file_hash(mp)
        if bh is None and mh is None:
            continue
        if bh is None:
            div.append({"filename": m["filename"], "reason": "missing_in_backend"})
        elif mh is None:
            div.append({"filename": m["filename"], "reason": "missing_in_microservice"})
        elif bh != mh:
            div.append({"filename": m["filename"], "reason": "hash_mismatch"})
    return div
