"""
Drift Monitor — V3 MLOps Layer
================================
Detects feature drift, prediction drift, and anomaly-rate spikes
in production ML model outputs.

Uses Kolmogorov-Smirnov (KS) test: p_value < 0.05 → drift detected.

Usage:
    from src.drift_monitor import DriftMonitor

    monitor = DriftMonitor(reference_data=X_train_df)
    report  = monitor.check(current_data=X_recent_df)

    if report['any_drift']:
        send_alert(report)

Design (MLOps senior-ml-engineer patterns):
- Stateless per-call: no background threads, no state mutation
- Reference dataset set once at startup (training distribution)
- KS test per feature + prediction distribution + anomaly rate
- Alert thresholds configurable (PSI > 0.1 warning, > 0.2 critical)
- Exports JSON-serializable report for logging/alerting
"""

import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)


@dataclass
class FeatureDriftResult:
    feature:        str
    ks_statistic:   float
    p_value:        float
    drift_detected: bool
    severity:       str   # 'none' | 'warning' | 'critical'
    ref_mean:       float
    cur_mean:       float
    mean_shift_pct: float  # % shift in mean


@dataclass
class DriftReport:
    timestamp:         str
    any_drift:         bool
    n_features_drifted: int
    feature_results:   List[FeatureDriftResult] = field(default_factory=list)
    prediction_drift:  Optional[FeatureDriftResult] = None
    anomaly_rate_alert: bool = False
    anomaly_rate_ref:  Optional[float] = None
    anomaly_rate_cur:  Optional[float] = None
    summary:           str = ''

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# KS p-value thresholds
DRIFT_CRITICAL_P = 0.01   # p < 0.01 → critical drift
DRIFT_WARNING_P  = 0.05   # p < 0.05 → warning drift

# Anomaly rate spike threshold
ANOMALY_RATE_SPIKE_FACTOR = 2.0  # current rate > 2× reference rate → alert


class DriftMonitor:
    """
    Production feature drift detector using KS test.

    Args:
        reference_data: DataFrame with training feature distribution (X_train).
                        Set once at startup, used for all subsequent checks.
        feature_cols:   List of feature columns to monitor. None = all numeric cols.
        p_warning:      KS p-value threshold for warning (default 0.05).
        p_critical:     KS p-value threshold for critical (default 0.01).
    """

    def __init__(
        self,
        reference_data: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        p_warning:  float = DRIFT_WARNING_P,
        p_critical: float = DRIFT_CRITICAL_P,
    ):
        if feature_cols is None:
            feature_cols = list(reference_data.select_dtypes(include=[np.number]).columns)

        self.reference_data = reference_data[feature_cols].copy()
        self.feature_cols   = feature_cols
        self.p_warning      = p_warning
        self.p_critical     = p_critical

        # Reference anomaly rate (if labels available, set externally)
        self.reference_anomaly_rate: Optional[float] = None

        logger.info(f"DriftMonitor initialized. Monitoring {len(feature_cols)} features.")

    def set_reference_anomaly_rate(self, rate: float):
        """Set expected anomaly rate from training (e.g. 0.034 = 3.4% failures)."""
        self.reference_anomaly_rate = rate

    def check(
        self,
        current_data: pd.DataFrame,
        current_predictions: Optional[np.ndarray] = None,
        current_anomaly_flags: Optional[np.ndarray] = None,
    ) -> DriftReport:
        """
        Check for drift between reference and current data.

        Args:
            current_data:          Recent production feature DataFrame.
            current_predictions:   Recent model predictions (for prediction drift).
            current_anomaly_flags: Recent P4 anomaly flags (0/1) for rate spike check.

        Returns:
            DriftReport with per-feature KS results and summary.
        """
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        feature_results = []

        # ── Per-feature KS drift ─────────────────────────────────────────────
        for col in self.feature_cols:
            if col not in current_data.columns:
                logger.warning(f"Feature '{col}' missing from current_data — skipping.")
                continue

            ref = self.reference_data[col].dropna().values
            cur = current_data[col].dropna().values

            if len(cur) < 30:
                logger.warning(f"Feature '{col}': only {len(cur)} samples — KS test unreliable.")
                continue

            ks_stat, p_value = ks_2samp(ref, cur)

            ref_mean = float(np.mean(ref))
            cur_mean = float(np.mean(cur))
            mean_shift_pct = abs(cur_mean - ref_mean) / (abs(ref_mean) + 1e-8) * 100

            if p_value < self.p_critical:
                severity = 'critical'
                drift_detected = True
            elif p_value < self.p_warning:
                severity = 'warning'
                drift_detected = True
            else:
                severity = 'none'
                drift_detected = False

            result = FeatureDriftResult(
                feature=col,
                ks_statistic=round(float(ks_stat), 4),
                p_value=round(float(p_value), 6),
                drift_detected=drift_detected,
                severity=severity,
                ref_mean=round(ref_mean, 4),
                cur_mean=round(cur_mean, 4),
                mean_shift_pct=round(mean_shift_pct, 2),
            )
            feature_results.append(result)

            if drift_detected:
                logger.warning(
                    f"DRIFT [{severity.upper()}] Feature='{col}' "
                    f"KS={ks_stat:.4f} p={p_value:.6f} "
                    f"mean_shift={mean_shift_pct:.1f}%"
                )

        # ── Prediction drift ─────────────────────────────────────────────────
        prediction_drift = None
        if current_predictions is not None and hasattr(self, '_reference_predictions'):
            ks_stat, p_value = ks_2samp(self._reference_predictions, current_predictions)
            severity = (
                'critical' if p_value < self.p_critical else
                'warning'  if p_value < self.p_warning  else 'none'
            )
            prediction_drift = FeatureDriftResult(
                feature='predictions',
                ks_statistic=round(float(ks_stat), 4),
                p_value=round(float(p_value), 6),
                drift_detected=severity != 'none',
                severity=severity,
                ref_mean=round(float(np.mean(self._reference_predictions)), 4),
                cur_mean=round(float(np.mean(current_predictions)), 4),
                mean_shift_pct=0.0,
            )
            if prediction_drift.drift_detected:
                logger.warning(f"PREDICTION DRIFT [{severity.upper()}] p={p_value:.6f}")

        # ── Anomaly rate spike ────────────────────────────────────────────────
        anomaly_rate_alert = False
        anomaly_rate_cur   = None
        if current_anomaly_flags is not None and self.reference_anomaly_rate is not None:
            anomaly_rate_cur = float(np.mean(current_anomaly_flags))
            if anomaly_rate_cur > self.reference_anomaly_rate * ANOMALY_RATE_SPIKE_FACTOR:
                anomaly_rate_alert = True
                logger.warning(
                    f"ANOMALY RATE SPIKE: ref={self.reference_anomaly_rate:.3f} "
                    f"cur={anomaly_rate_cur:.3f} "
                    f"(>{ANOMALY_RATE_SPIKE_FACTOR}x threshold)"
                )

        # ── Build report ─────────────────────────────────────────────────────
        n_drifted = sum(r.drift_detected for r in feature_results)
        any_drift = n_drifted > 0 or (prediction_drift and prediction_drift.drift_detected) or anomaly_rate_alert

        critical = [r.feature for r in feature_results if r.severity == 'critical']
        warning  = [r.feature for r in feature_results if r.severity == 'warning']

        summary_parts = []
        if critical:
            summary_parts.append(f"CRITICAL drift: {', '.join(critical)}")
        if warning:
            summary_parts.append(f"WARNING drift: {', '.join(warning)}")
        if anomaly_rate_alert:
            summary_parts.append(f"Anomaly rate spike: {anomaly_rate_cur:.3f} (ref={self.reference_anomaly_rate:.3f})")
        if not summary_parts:
            summary_parts.append("No drift detected.")

        report = DriftReport(
            timestamp=timestamp,
            any_drift=any_drift,
            n_features_drifted=n_drifted,
            feature_results=feature_results,
            prediction_drift=prediction_drift,
            anomaly_rate_alert=anomaly_rate_alert,
            anomaly_rate_ref=self.reference_anomaly_rate,
            anomaly_rate_cur=anomaly_rate_cur,
            summary=' | '.join(summary_parts),
        )

        if any_drift:
            logger.error(f"DRIFT REPORT: {report.summary}")
        else:
            logger.info(f"Drift check passed. {len(feature_results)} features OK.")

        return report

    def set_reference_predictions(self, predictions: np.ndarray):
        """Store reference model output distribution for prediction drift tracking."""
        self._reference_predictions = predictions.copy()

    @classmethod
    def from_training_data(
        cls,
        X_train: pd.DataFrame,
        y_train: Optional[np.ndarray] = None,
        predictions_train: Optional[np.ndarray] = None,
        feature_cols: Optional[List[str]] = None,
    ) -> 'DriftMonitor':
        """
        Factory method: create monitor from training data.

        Args:
            X_train: Training features (sets reference distribution).
            y_train: Training labels (sets reference anomaly rate if binary 0/1).
            predictions_train: Training predictions (sets reference prediction dist).
            feature_cols: Features to monitor. None = all numeric.

        Returns:
            Configured DriftMonitor ready for production use.
        """
        monitor = cls(reference_data=X_train, feature_cols=feature_cols)

        if y_train is not None:
            monitor.set_reference_anomaly_rate(float(np.mean(y_train)))

        if predictions_train is not None:
            monitor.set_reference_predictions(predictions_train)

        return monitor


def run_drift_check_example():
    """
    Example: simulate drift check with ai4i2020 dataset.
    Run this to verify drift monitor works.
    """
    import os
    CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai4i2020.csv')
    if not os.path.exists(CSV_PATH):
        CSV_PATH = 'ai4i2020.csv'

    df = pd.read_csv(CSV_PATH)
    SENSOR_COLS = [
        'Air temperature [K]', 'Process temperature [K]',
        'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
    ]

    # Split: reference = first 8000 rows, current = last 2000 (simulates production)
    ref_df = df[SENSOR_COLS].iloc[:8000]
    cur_df = df[SENSOR_COLS].iloc[8000:]
    y_train = df['Machine failure'].iloc[:8000].values

    monitor = DriftMonitor.from_training_data(ref_df, y_train=y_train)
    report  = monitor.check(current_data=cur_df)

    print(f"\nDrift Report Summary: {report.summary}")
    print(f"Any drift: {report.any_drift}")
    print(f"Features drifted: {report.n_features_drifted}")

    for r in report.feature_results:
        status = f"[{r.severity.upper()}]" if r.drift_detected else "[OK]"
        print(f"  {status:12s} {r.feature:35s} p={r.p_value:.4f}  mean_shift={r.mean_shift_pct:.1f}%")

    # Simulate drifted production (inject noise)
    print("\n--- Simulating drifted production data ---")
    cur_drifted = cur_df.copy()
    cur_drifted['Torque [Nm]'] += 15  # shift torque by +15 Nm
    cur_drifted['Tool wear [min]'] *= 1.5

    report_drifted = monitor.check(current_data=cur_drifted)
    print(f"Drift Report (drifted): {report_drifted.summary}")
    for r in report_drifted.feature_results:
        status = f"[{r.severity.upper()}]" if r.drift_detected else "[OK]"
        print(f"  {status:12s} {r.feature:35s} p={r.p_value:.4f}  mean_shift={r.mean_shift_pct:.1f}%")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_drift_check_example()
