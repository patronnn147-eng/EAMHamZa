"""
Shared Feature Engineering Pipeline — V3
=========================================
Centralized sklearn-compatible transformers for all ML models.

Single source of truth for:
- Rolling temporal statistics (mean, std, trend, EMA, min, max, acceleration, volatility)
- Interaction features (thermal_stress, wear_per_rpm, temp_delta, rpm_torque)
- K-Means machine state clustering (cluster_id feature)

Usage:
    from ml_problems.shared.feature_engineering import build_feature_pipeline, SENSOR_COLS

    pipeline = build_feature_pipeline(n_clusters=4)
    X_transformed = pipeline.fit_transform(df[SENSOR_COLS])

    # Save for inference — same pipeline, no mismatch
    joblib.dump(pipeline, 'models/feature_pipeline_v3.pkl')

Design:
- All transformers are sklearn BaseEstimator + TransformerMixin → compatible with Pipeline
- RollingFeatureTransformer uses min_periods=1 to avoid NaN on first rows
- ClusterStateTransformer saves scaler + kmeans internally → single object to serialize
- K optimization via silhouette score (target > 0.5)
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Canonical sensor column names (raw dataset)
SENSOR_COLS = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]',
]

# Short aliases for feature naming
SENSOR_ALIASES = ['air_temp', 'proc_temp', 'rpm', 'torque', 'tool_wear']


class RollingFeatureTransformer(BaseEstimator, TransformerMixin):
    """
    Adds temporal rolling statistics for each sensor column.

    For each sensor: mean, std, trend (diff), EMA, min, max, acceleration (diff²), volatility.
    Window size configurable (default=10 cycles).

    IMPORTANT: Assumes input DataFrame rows are in temporal order (cycle 1 → N).
    Uses min_periods=1 to avoid NaN on first rows.
    """

    def __init__(self, window: int = 10):
        self.window = window

    def fit(self, X, y=None):
        return self  # stateless — no fitting needed

    def transform(self, X, y=None) -> pd.DataFrame:
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X, columns=SENSOR_COLS[:X.shape[1]])

        df = X.copy()
        w = self.window

        for col, alias in zip(SENSOR_COLS, SENSOR_ALIASES):
            if col not in df.columns:
                continue
            s = df[col]
            df[f'{alias}_mean{w}']       = s.rolling(w, min_periods=1).mean()
            df[f'{alias}_std{w}']        = s.rolling(w, min_periods=1).std().fillna(0)
            df[f'{alias}_trend{w}']      = s.diff(w).fillna(0)
            df[f'{alias}_ema{w}']        = s.ewm(span=w, adjust=False).mean()
            df[f'{alias}_min{w}']        = s.rolling(w, min_periods=1).min()
            df[f'{alias}_max{w}']        = s.rolling(w, min_periods=1).max()
            df[f'{alias}_accel{w}']      = s.diff().diff().fillna(0)
            df[f'{alias}_volatility{w}'] = (
                df[f'{alias}_std{w}'] / (df[f'{alias}_mean{w}'].abs() + 1e-6)
            )

        return df

    def get_feature_names_out(self, input_features=None):
        names = list(SENSOR_COLS)
        w = self.window
        for alias in SENSOR_ALIASES:
            for suffix in [f'_mean{w}', f'_std{w}', f'_trend{w}', f'_ema{w}',
                           f'_min{w}', f'_max{w}', f'_accel{w}', f'_volatility{w}']:
                names.append(f'{alias}{suffix}')
        return names


class InteractionFeatureTransformer(BaseEstimator, TransformerMixin):
    """
    Adds engineered interaction features between sensor readings.

    Features added:
    - temp_delta:     process_temp - air_temp (thermal differential)
    - rpm_torque:     rpm * torque (power proxy)
    - thermal_stress: air_temp * torque (combined thermal load)
    - wear_per_rpm:   tool_wear / (rpm + 1) (wear rate per unit speed)
    - tool_wear_sq:   tool_wear² (nonlinear wear acceleration)
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None) -> pd.DataFrame:
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X, columns=SENSOR_COLS[:X.shape[1]])

        df = X.copy()

        air   = df.get('Air temperature [K]',     df.get('air_temp', 0))
        proc  = df.get('Process temperature [K]', df.get('proc_temp', 0))
        rpm   = df.get('Rotational speed [rpm]',  df.get('rpm', 1))
        torq  = df.get('Torque [Nm]',             df.get('torque', 0))
        wear  = df.get('Tool wear [min]',         df.get('tool_wear', 0))

        df['temp_delta']     = proc - air
        df['rpm_torque']     = rpm * torq
        df['thermal_stress'] = air * torq
        df['wear_per_rpm']   = wear / (rpm.abs() + 1)
        df['tool_wear_sq']   = wear ** 2

        return df


class ClusterStateTransformer(BaseEstimator, TransformerMixin):
    """
    Adds K-Means machine state cluster_id as a feature.

    Automatically selects optimal K via silhouette score (range 3–7).
    Target silhouette > 0.5.

    Saves internally: StandardScaler (for cluster distance computation) + KMeans model.
    Both serialized together when pipeline is saved → no mismatch at inference.

    Expected cluster semantics (validated via UMAP):
    - Cluster 0: Heavy Load (low RPM, high torque)
    - Cluster 1: Healthy (normal operating range)
    - Cluster 2: Degrading (high temp, high wear)
    - Cluster 3: Critical (extreme values)
    """

    def __init__(self, n_clusters: int = None, max_k: int = 7, random_state: int = 42):
        self.n_clusters = n_clusters   # None = auto-select via silhouette
        self.max_k = max_k
        self.random_state = random_state
        self.scaler_ = None
        self.kmeans_ = None
        self.best_k_ = None
        self.silhouette_score_ = None

    def fit(self, X, y=None):
        if isinstance(X, np.ndarray):
            df = pd.DataFrame(X)
        else:
            df = X.copy()

        # Use only original 5 sensor columns for clustering
        sensor_data = self._extract_sensors(df)

        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(sensor_data)

        if self.n_clusters is not None:
            # Use specified K
            self.best_k_ = self.n_clusters
        else:
            # Auto-select K via silhouette score
            print(f"  [ClusterTransformer] Searching optimal K (3–{self.max_k})...")
            best_score, best_k = -1, 3
            for k in range(3, self.max_k + 1):
                km = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                labels = km.fit_predict(X_scaled)
                score = silhouette_score(X_scaled, labels)
                print(f"    K={k}: silhouette={score:.4f}")
                if score > best_score:
                    best_score, best_k = score, k
            self.best_k_ = best_k
            self.silhouette_score_ = best_score
            print(f"  [ClusterTransformer] Best K={best_k} (silhouette={best_score:.4f})")
            if best_score < 0.5:
                print(f"  [ClusterTransformer] WARNING: silhouette {best_score:.4f} < 0.5 — clusters may not be well-separated")

        self.kmeans_ = KMeans(n_clusters=self.best_k_, random_state=self.random_state, n_init=10)
        self.kmeans_.fit(X_scaled)
        return self

    def transform(self, X, y=None) -> pd.DataFrame:
        if isinstance(X, np.ndarray):
            df = pd.DataFrame(X)
        else:
            df = X.copy()

        sensor_data = self._extract_sensors(df)
        X_scaled = self.scaler_.transform(sensor_data)
        df['cluster_id'] = self.kmeans_.predict(X_scaled)

        # Also add distance to assigned cluster center (used in P4 anomaly ensemble)
        centers = self.kmeans_.cluster_centers_
        cluster_ids = df['cluster_id'].values
        df['cluster_distance'] = np.array([
            np.linalg.norm(X_scaled[i] - centers[cluster_ids[i]])
            for i in range(len(X_scaled))
        ])

        return df

    def _extract_sensors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract original 5 sensor columns for clustering (ignore engineered features)."""
        available = [c for c in SENSOR_COLS if c in df.columns]
        if available:
            return df[available]
        # Fallback: use first 5 numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns[:5]
        return df[numeric_cols]

    def get_cluster_labels(self) -> dict:
        """Return cluster semantic labels (set after UMAP validation)."""
        return {
            0: 'Heavy Load',
            1: 'Healthy',
            2: 'Degrading',
            3: 'Critical',
        }


def build_feature_pipeline(
    window: int = 10,
    n_clusters: int = None,
    include_rolling: bool = True,
    include_interactions: bool = True,
    include_clustering: bool = True,
) -> Pipeline:
    """
    Build the full V3 feature engineering pipeline.

    Args:
        window: Rolling window size for temporal features (default=10 cycles)
        n_clusters: K for K-Means. None = auto-select via silhouette.
        include_rolling: Add rolling temporal stats
        include_interactions: Add interaction features
        include_clustering: Add K-Means cluster_id

    Returns:
        sklearn Pipeline (not yet fitted — call pipeline.fit_transform(df))

    Example:
        pipeline = build_feature_pipeline(n_clusters=4)
        X_v3 = pipeline.fit_transform(df[SENSOR_COLS])
        joblib.dump(pipeline, 'models/feature_pipeline_v3.pkl')

        # Inference (same pipeline, guaranteed identical transforms):
        pipeline = joblib.load('models/feature_pipeline_v3.pkl')
        X_inference = pipeline.transform(new_df[SENSOR_COLS])
    """
    steps = []

    if include_interactions:
        steps.append(('interactions', InteractionFeatureTransformer()))

    if include_rolling:
        steps.append(('rolling', RollingFeatureTransformer(window=window)))

    if include_clustering:
        steps.append(('clustering', ClusterStateTransformer(n_clusters=n_clusters)))

    if not steps:
        raise ValueError("At least one transformer must be enabled")

    return Pipeline(steps)


def load_feature_pipeline(path: str) -> Pipeline:
    """Load serialized feature pipeline for inference."""
    return joblib.load(path)
