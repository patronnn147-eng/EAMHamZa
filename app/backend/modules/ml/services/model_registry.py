"""Model registry + pkl-sync check across the two model directories."""

import hashlib
import os
from typing import Optional

# Which metric key best represents each model's accuracy, and how to label it.
# p4 is unsupervised (IsolationForest) — no accuracy label exists.
_HEADLINE_METRIC = {
    "p1": [("roc_auc", "ROC-AUC"), ("f1_failure", "F1"), ("val_f1", "F1")],
    "p2": [("_f1_per_label_avg", "F1 moyen")],
    "p3": [("val_r2", "R²"), ("r2", "R²")],
    "p5": [("val_f1_macro", "F1 macro")],
    "p6": [("r2", "R²")],
    "p7": [("f1", "F1")],
}


# Phase 4.1 reporting hygiene: every model's accuracy number now carries an
# honest trust label instead of being displayed as if all numbers were equally
# real. Three states only (per roadmap doc, Phase 4.1):
#   leaked                    -> label is a deterministic formula of an input
#                                 feature (tool_wear); the number is real
#                                 arithmetic but not a real prediction.
#   unverified                -> no group-holdout (or no ground truth at all)
#                                 backs this number; could be leakage-inflated.
#   group-holdout-validated   -> scored against a machine never seen in
#                                 training; the closest thing to a trustworthy
#                                 number this app can currently produce.
# P1/P2/P5 are "leaked" unconditionally — group-holdout doesn't fix a label
# that's a formula of an input feature (see roadmap doc §6 for each model).
# This overrides whatever a retrain run stored, since methodology can't cure
# a labeling problem.
_VALIDATION_STATUS_OVERRIDE = {"p1": "leaked", "p2": "leaked", "p5": "leaked"}
# Fallback for models that never carry a live validation_status in their pkl
# metrics (P4 is unsupervised — no accuracy exists to validate; P6 is
# hard-skipped from retraining; P7 is a deterministic pipeline, not trained).
_VALIDATION_STATUS_DEFAULT = {"p4": "unverified", "p6": "unverified", "p7": "unverified"}
_VALIDATION_STATUS_LABEL = {
    "leaked": "Non fiable",
    "unverified": "Non vérifié",
    "group-holdout-validated": "Vérifié",
}


def _validation_status(key: str, metrics: Optional[dict]) -> dict:
    if key in _VALIDATION_STATUS_OVERRIDE:
        status = _VALIDATION_STATUS_OVERRIDE[key]
    elif metrics and metrics.get("validation_status"):
        status = metrics["validation_status"]
    else:
        status = _VALIDATION_STATUS_DEFAULT.get(key, "unverified")
    return {"status": status, "label": _VALIDATION_STATUS_LABEL.get(status, status)}


def _headline_metric(key: str, metrics: Optional[dict]) -> Optional[dict]:
    if not metrics:
        return None
    if key == "p2" and "f1_per_label" in metrics:
        per_label = metrics["f1_per_label"]
        if per_label:
            avg = sum(per_label.values()) / len(per_label)
            return {"name": "F1 moyen", "value": round(avg, 4), "per_label": per_label}
        return None
    for source_key, display_name in _HEADLINE_METRIC.get(key, []):
        if source_key in metrics and metrics[source_key] is not None:
            return {"name": display_name, "value": round(float(metrics[source_key]), 4)}
    return None


def _load_metrics(path: str) -> Optional[dict]:
    try:
        import joblib

        data = joblib.load(path)
        if isinstance(data, dict):
            return data.get("metrics") or data.get("meta")
    except Exception:
        return None
    return None

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
        raw_metrics = _load_metrics(bp) if bh else None
        out.append(
            {
                **m,
                "in_backend": bh is not None,
                "in_micro": mh is not None,
                "hash_match": bh is not None and bh == mh,
                "size_backend": os.path.getsize(bp) if bh else None,
                "mtime_backend": os.path.getmtime(bp) if bh else None,
                "headline_metric": _headline_metric(m["key"], raw_metrics),
                "validation_status": _validation_status(m["key"], raw_metrics),
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
