"""
Shared Validation Utilities — V3
==================================
Custom scorers and CV strategies for temporal ML models.

Provides:
- ordinal_mae_scorer:    penalizes large label jumps (LOW→CRITICAL worse than LOW→MEDIUM)
- concordance_index_scorer: rank-order quality for RUL regression
- walk_forward_cv:       manual walk-forward for LSTM + models needing refitting per fold
- temporal_train_test_split: temporal-safe split (no shuffle, last N% = test)
"""

import numpy as np
import pandas as pd
from sklearn.metrics import make_scorer, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit


# ── Ordinal MAE Scorer ────────────────────────────────────────────────────────

def ordinal_mae(y_true, y_pred):
    """
    MAE on ordinal class indices.
    Priority: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3.
    Predicting CRITICAL (3) as LOW (0) → error=3 (severe).
    Predicting CRITICAL (3) as HIGH (2) → error=1 (acceptable).
    """
    return mean_absolute_error(y_true, np.round(y_pred).astype(int))


ordinal_mae_scorer = make_scorer(ordinal_mae, greater_is_better=False)


# ── Concordance Index Scorer ──────────────────────────────────────────────────

def concordance_index_score(y_true, y_pred):
    """
    Concordance Index (C-index) for RUL regression.
    Measures rank ordering quality: 1.0=perfect, 0.5=random.

    Unlike MAE, C-index cares about RELATIVE ranking:
    - MAE=5 at RUL=10 is catastrophic (missed imminent failure)
    - MAE=5 at RUL=200 is fine (distant future, less critical)
    C-index captures this; MAE does not.

    Requires: pip install lifelines
    """
    try:
        from lifelines.utils import concordance_index
        return concordance_index(y_true, y_pred)
    except ImportError:
        raise ImportError(
            "C-index requires lifelines: pip install lifelines"
        )


def try_concordance_index(y_true, y_pred) -> float:
    """Returns C-index or None if lifelines not installed."""
    try:
        return concordance_index_score(y_true, y_pred)
    except ImportError:
        return None


# ── Temporal Train/Test Split ─────────────────────────────────────────────────

def temporal_train_test_split(X, y, test_size: float = 0.2):
    """
    Temporal-safe train/test split. No shuffling — last test_size fraction = test.

    Args:
        X: Features (DataFrame or array), ordered by time
        y: Target, ordered by time
        test_size: Fraction of data for test (default 0.2 = last 20%)

    Returns:
        X_train, X_test, y_train, y_test
    """
    split_idx = int(len(X) * (1 - test_size))

    if isinstance(X, pd.DataFrame):
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    else:
        X_train, X_test = X[:split_idx], X[split_idx:]

    if isinstance(y, pd.Series):
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    else:
        y_train, y_test = y[:split_idx], y[split_idx:]

    return X_train, X_test, y_train, y_test


# ── Walk-Forward Cross-Validation ─────────────────────────────────────────────

def walk_forward_cv(model_factory, X, y, n_splits: int = 5, scorer=None):
    """
    Walk-forward (expanding window) cross-validation.

    Used for: LSTM, models that need full refitting per fold, models where
    TimeSeriesSplit + cross_val_score isn't applicable (e.g. Keras models).

    Each fold: train on [0..split_i], predict [split_i..split_i+step]
    No future data leaks into training.

    Args:
        model_factory: Callable() → fresh unfitted model instance
        X: Features ordered by time (DataFrame or array)
        y: Target ordered by time
        n_splits: Number of walk-forward folds
        scorer: Callable(y_true, y_pred) → float. Defaults to neg_MAE.

    Returns:
        dict with 'scores', 'mean', 'std'

    Example:
        from sklearn.metrics import mean_absolute_error
        results = walk_forward_cv(
            model_factory=lambda: XGBRegressor(**best_params),
            X=X, y=y, n_splits=5,
            scorer=lambda yt, yp: -mean_absolute_error(yt, yp)
        )
        print(f"Walk-forward MAE: {-results['mean']:.2f} ± {results['std']:.2f}")
    """
    if scorer is None:
        from sklearn.metrics import mean_absolute_error
        scorer = lambda yt, yp: -mean_absolute_error(yt, yp)

    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []

    if isinstance(X, pd.DataFrame):
        X_arr = X.values
    else:
        X_arr = np.array(X)

    if isinstance(y, pd.Series):
        y_arr = y.values
    else:
        y_arr = np.array(y)

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_arr)):
        model = model_factory()
        model.fit(X_arr[train_idx], y_arr[train_idx])
        y_pred = model.predict(X_arr[val_idx])
        score = scorer(y_arr[val_idx], y_pred)
        scores.append(score)
        print(f"  Fold {fold+1}/{n_splits}: score={score:.4f}")

    scores = np.array(scores)
    return {
        'scores': scores.tolist(),
        'mean':   float(scores.mean()),
        'std':    float(scores.std()),
    }
