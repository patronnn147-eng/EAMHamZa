"""
Drift Detector
Statistical drift detection for production ML
"""
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect data drift using statistical methods."""
    
    def __init__(self, window_size: int = 1000):
        """
        Args:
            window_size: Number of samples to keep for baseline
        """
        self.window_size = window_size
        self.baseline: deque = deque(maxlen=window_size)
        self.current: deque = deque(maxlen=window_size)
        self.baseline_stats: Dict = {}
    
    def add_baseline(self, features: List[float]):
        """Add features to baseline window."""
        self.baseline.append(features)
        self._update_stats()
    
    def add_current(self, features: List[float]):
        """Add features to current window."""
        self.current.append(features)
    
    def _update_stats(self):
        """Update baseline statistics."""
        if len(self.baseline) >= 100:
            arr = np.array(self.baseline)
            self.baseline_stats = {
                'mean': np.mean(arr, axis=0).tolist(),
                'std': np.std(arr, axis=0).tolist(),
                'min': np.min(arr, axis=0).tolist(),
                'max': np.max(arr, axis=0).tolist(),
                'count': len(self.baseline)
            }
    
    def detect_drift(self) -> Dict:
        """Detect drift using statistical tests."""
        if len(self.baseline) < 100 or len(self.current) < 100:
            return {
                "drift_detected": False, 
                "reason": "insufficient_data",
                "baseline_count": len(self.baseline),
                "current_count": len(self.current)
            }
        
        baseline_arr = np.array(self.baseline)
        current_arr = np.array(self.current)
        
        # Per-feature drift detection
        drift_scores = []
        for i in range(baseline_arr.shape[1]):
            baseline_col = baseline_arr[:, i]
            current_col = current_arr[:, i]
            
            # Calculate drift score (simple difference)
            baseline_mean = np.mean(baseline_col)
            current_mean = np.mean(current_col)
            baseline_std = max(np.std(baseline_col), 0.001)
            
            # Normalized difference
            drift_score = abs(current_mean - baseline_mean) / baseline_std
            
            drift_scores.append({
                'feature_index': i,
                'baseline_mean': float(baseline_mean),
                'current_mean': float(current_mean),
                'drift_score': float(drift_score),
                'drift': drift_score > 2.0  # Threshold
            })
        
        # Overall drift
        drift_detected = any(s['drift'] for s in drift_scores)
        avg_drift = np.mean([s['drift_score'] for s in drift_scores])
        
        return {
            "drift_detected": drift_detected,
            "avg_drift_score": float(avg_drift),
            "feature_scores": drift_scores,
            "baseline_count": len(self.baseline),
            "current_count": len(self.current),
            "threshold": 2.0
        }
    
    def get_status(self) -> Dict:
        """Get detector status."""
        return {
            "baseline_count": len(self.baseline),
            "current_count": len(self.current),
            "has_baseline": len(self.baseline) >= 100,
            "baseline_stats": self.baseline_stats
        }
    
    def reset_current(self):
        """Reset current window."""
        self.current.clear()


# Global drift detector
drift_detector = DriftDetector()


def check_drift(features: List[float]) -> Dict:
    """Check for drift with new features."""
    drift_detector.add_current(features)
    return drift_detector.detect_drift()


def update_baseline(features: List[float]):
    """Update baseline with new features."""
    drift_detector.add_baseline(features)


def get_drift_status() -> Dict:
    """Get drift detector status."""
    return drift_detector.get_status()