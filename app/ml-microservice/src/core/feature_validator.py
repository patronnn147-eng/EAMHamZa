"""
Feature Validator
Validates and extracts features from raw sensor telemetry dicts.
Moved from feature_store.py — same logic, clearer name.
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureValidator:
    """Validate sensor readings and extract feature vectors."""

    RANGES = {
        'air_temperature':     (0, 2000),
        'process_temperature': (0, 5000),
        'rotational_speed':    (0, 10000),
        'torque':              (0, 1000),
        'tool_wear':           (0, 300),
    }

    DEFAULTS = {
        'air_temperature':     298,
        'process_temperature': 308,
        'rotational_speed':    1500,
        'torque':              40,
        'tool_wear':           0,
    }

    @classmethod
    def validate(cls, telemetry: Dict) -> None:
        """Raise ValueError if any sensor reading is outside allowed range."""
        for field, (lo, hi) in cls.RANGES.items():
            if field in telemetry:
                val = float(telemetry[field])
                if not (lo <= val <= hi):
                    raise ValueError(
                        f"{field}={val} out of range [{lo}, {hi}]"
                    )

    @staticmethod
    def extract_5_features(telemetry: Dict) -> List[float]:
        return [
            float(telemetry.get('air_temperature', 298)),
            float(telemetry.get('process_temperature', 308)),
            int(telemetry.get('rotational_speed', 1500)),
            float(telemetry.get('torque', 40)),
            int(telemetry.get('tool_wear', 0)),
        ]

    @staticmethod
    def extract_full_snapshot(telemetry: Dict, context: Optional[Dict] = None) -> Dict:
        """Delegate to existing FeatureStore logic — copied verbatim to preserve behavior."""
        from ..feature_store import FeatureStore
        return FeatureStore.extract_full_snapshot(telemetry, context)

    @staticmethod
    def build_time_series_from_logs(machine_id: int, logs: list) -> list:
        from ..feature_store import FeatureStore
        return FeatureStore.build_time_series_from_logs(machine_id, logs)


# Module-level instance — backward compatible with existing imports
feature_validator = FeatureValidator()
