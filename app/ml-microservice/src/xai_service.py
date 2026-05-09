"""
XAI Service — SHAP-based explainability for ML predictions.

Authoritative copy lives here (ml-microservice). Backend must NOT duplicate.

Module-level explainer cache keyed by id(model).
Avoids rebuilding SHAP explainer on every call (~100-500ms overhead for tree models).
Uses id() which may alias after GC — acceptable: worst case is one extra build.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

_explainer_cache: Dict[int, object] = {}


def _get_explainer(model, X: pd.DataFrame) -> object:
    """
    Return cached SHAP explainer for model, creating it on first call.

    Prefers TreeExplainer for sklearn/XGBoost tree models (no background data
    needed, ~10× faster than generic Explainer). Falls back to generic Explainer
    for non-tree models using X as background dataset.
    """
    import shap  # lazy import — optional dependency; install shap>=0.44.0
    key = id(model)
    if key not in _explainer_cache:
        try:
            # TreeExplainer: XGBoost, RandomForest, GradientBoosting, etc.
            # Does NOT need background data → faster and deterministic.
            _explainer_cache[key] = shap.TreeExplainer(model)
            logger.debug(f"SHAP: created TreeExplainer for {type(model).__name__}")
        except Exception:
            # Fallback for non-tree models (LogisticRegression, SVM, etc.)
            _explainer_cache[key] = shap.Explainer(model, X)
            logger.debug(f"SHAP: created generic Explainer for {type(model).__name__}")
    return _explainer_cache[key]


# Internal feature names used by P1 model
_P1_FEATURE_NAMES = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

# Friendly French labels for frontend display
_FRIENDLY_NAMES = {
    "Air temperature [K]":      "Température Ambiante",
    "Process temperature [K]":  "Température du Processus",
    "Rotational speed [rpm]":   "Vitesse de Rotation",
    "Torque [Nm]":              "Couple (Torque)",
    "Tool wear [min]":          "Usure de l'Outil",
    "air_temperature":          "Température Ambiante",
    "process_temperature":      "Température du Processus",
    "rotational_speed":         "Vitesse de Rotation",
    "torque":                   "Couple (Torque)",
    "tool_wear":                "Usure de l'Outil",
}


class XAIService:

    @staticmethod
    def explain_prediction(model, features: List[float], feature_names: List[str]) -> List[Dict]:
        """
        Generate SHAP explanations for a single prediction.

        Args:
            model: Trained ML model (sklearn/XGBoost) or dict with 'model' key.
            features: Feature values matching feature_names order.
            feature_names: Human-readable names matching training order.

        Returns:
            Top-3 SHAP impacts sorted by |impact| descending:
            [{"factor": str, "impact": float, "intensity": "high"|"medium"|"low"}]
        """
        if model is None:
            return []

        try:
            # XGBoost DMatrix forbids [ ] < in feature names — sanitize before
            # building the DataFrame. SHAP values are positional so original
            # feature_names are still used for labelling impacts below.
            safe_names = [
                n.replace("[", "_").replace("]", "_").replace("<", "_")
                for n in feature_names
            ]
            X = pd.DataFrame([features], columns=safe_names)
            actual_model = (
                model['model'] if isinstance(model, dict) and 'model' in model else model
            )

            explainer = _get_explainer(actual_model, X)
            shap_values = explainer(X)

            values = shap_values.values[0]
            if len(values.shape) > 1:
                # Binary classifier: take class 1 (failure) column
                values = values[:, 1] if values.shape[1] > 1 else values.flatten()

            impacts = []
            for i, name in enumerate(feature_names):
                impact_val = float(values[i])
                if abs(impact_val) > 0.01:
                    impacts.append({
                        "factor":    name,
                        "impact":    round(impact_val, 6),
                        "intensity": (
                            "high"   if abs(impact_val) > 0.1  else
                            "medium" if abs(impact_val) > 0.05 else
                            "low"
                        ),
                    })

            impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)
            return impacts[:3]

        except Exception as exc:
            logger.error(f"XAI Error: {exc}", exc_info=True)
            return []

    @staticmethod
    def explain_p1(model, features_5: List[float]) -> List[Dict]:
        """
        Convenience wrapper: SHAP for P1 model using canonical 5-feature names.
        Returns friendly-named impacts for frontend consumption.
        """
        raw = XAIService.explain_prediction(model, features_5, _P1_FEATURE_NAMES)
        for item in raw:
            item["factor"] = _FRIENDLY_NAMES.get(item["factor"], item["factor"])
        return raw

    @staticmethod
    def get_friendly_factor_name(internal_name: str) -> str:
        """Map dataset column names to user-friendly French labels."""
        return _FRIENDLY_NAMES.get(internal_name, internal_name)
