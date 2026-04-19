"""
Feature Store
Extract and manage features for ML models
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureStore:
    """Extract and manage features for ML models."""
    
    # Feature ranges for validation
    RANGES = {
        'air_temperature': (250, 350),       # Kelvin
        'process_temperature': (250, 400),   # Kelvin
        'rotational_speed': (0, 10000),     # RPM
        'torque': (0, 1000),               # Nm
        'tool_wear': (0, 300),             # minutes
    }
    
    # Default values
    DEFAULTS = {
        'air_temperature': 298,
        'process_temperature': 308,
        'rotational_speed': 1500,
        'torque': 40,
        'tool_wear': 0,
    }
    
    @staticmethod
    def extract_5_features(telemetry: Dict) -> List[float]:
        """
        Extract 5 features: [air, process, rpm, torque, wear]
        
        Args:
            telemetry: Dict with sensor readings
        
        Returns:
            List of 5 features
        """
        return [
            float(telemetry.get('air_temperature', 298)),
            float(telemetry.get('process_temperature', 308)),
            int(telemetry.get('rotational_speed', 1500)),
            float(telemetry.get('torque', 40)),
            int(telemetry.get('tool_wear', 0))
        ]
    
    @staticmethod
    def extract_6_features(telemetry: Dict) -> List[float]:
        """
        Extract 6 features with temp_delta.
        
        Args:
            telemetry: Dict with sensor readings
        
        Returns:
            List of 6 features (5 + temp_delta)
        """
        features_5 = FeatureStore.extract_5_features(telemetry)
        temp_delta = features_5[1] - features_5[0]  # process - air
        return features_5 + [temp_delta]
    
    @staticmethod
    def validate_telemetry(telemetry: Dict) -> Dict:
        """
        Validate and sanitize telemetry input.
        
        Args:
            telemetry: Raw telemetry dict
        
        Returns:
            Validated telemetry with defaults filled
        """
        validated = {}
        
        for field, (min_val, max_val) in FeatureStore.RANGES.items():
            value = telemetry.get(field)
            
            if value is not None:
                # Check if in range
                if min_val <= value <= max_val:
                    validated[field] = value
                else:
                    logger.warning(
                        f"{field}={value} out of range [{min_val}, {max_val}], "
                        f"using default"
                    )
            # Use default if not present or out of range
            validated.setdefault(field, FeatureStore.DEFAULTS[field])
        
        return validated
    
    @staticmethod
    def validate_range(value: float, field: str) -> bool:
        """
        Check if a value is in valid range.
        
        Args:
            value: The value to check
            field: The field name
        
        Returns:
            True if valid, False otherwise
        """
        if field in FeatureStore.RANGES:
            min_val, max_val = FeatureStore.RANGES[field]
            return min_val <= value <= max_val
        return True  # Unknown field, allow
    
    @staticmethod
    def compute_derived(telemetry: Dict) -> Dict:
        """
        Compute derived features from raw telemetry.
        
        Args:
            telemetry: Validated telemetry dict
        
        Returns:
            Dict of derived features
        """
        air = float(telemetry.get('air_temperature', 298))
        process = float(telemetry.get('process_temperature', 308))
        rpm = int(telemetry.get('rotational_speed', 1500))
        torque = float(telemetry.get('torque', 40))
        wear = int(telemetry.get('tool_wear', 0))
        
        # Temperature difference
        temp_delta = process - air
        
        # Power calculation (simplified)
        power = rpm * torque
        
        # Wear rate (wear per RPM)
        wear_rate = wear / max(1, rpm)
        
        # Temperature ratio
        temp_ratio = process / air if air > 0 else 1.0
        
        return {
            "temp_delta": round(temp_delta, 2),
            "temp_ratio": round(temp_ratio, 4),
            "power": round(power, 2),
            "wear_rate": round(wear_rate, 4),
        }
    
    @staticmethod
    def get_feature_names() -> Dict[str, List[str]]:
        """
        Get feature names for each model.

        Returns:
            Dict mapping model to feature list
        """
        return {
            "p1_failure": ["air_temperature", "process_temperature",
                          "rotational_speed", "torque", "tool_wear"],
            "p2_failure_type": ["air_temperature", "process_temperature",
                               "rotational_speed", "torque", "tool_wear",
                               "temp_delta"],
            "p3_rul": ["air_temperature", "process_temperature",
                      "rotational_speed", "torque", "tool_wear"],
            "p4_anomaly": ["air_temperature", "process_temperature",
                          "rotational_speed", "torque", "tool_wear"],
            "p5_priority": ["air_temperature", "process_temperature",
                           "rotational_speed", "torque", "tool_wear",
                           "temp_delta"],
            "p6_schedule": ["air_temperature", "process_temperature",
                           "rotational_speed", "torque", "tool_wear",
                           "temp_delta"],
        }

    @staticmethod
    def extract_full_snapshot(
        telemetry: Dict,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Build a complete FeatureSnapshot dict from telemetry + optional context.

        Args:
            telemetry: Raw sensor readings dict (from machines table or API)
            context: Optional dict with keys:
                     machine_id, timestamp, days_since_maint,
                     open_work_orders, recent_interventions,
                     machine_status, tool_wear_delta, sequence_length

        Returns:
            FeatureSnapshot dict with all fields populated (defaults for missing)
        """
        validated = FeatureStore.validate_telemetry(telemetry)
        derived = FeatureStore.compute_derived(validated)
        ctx = context or {}

        air = float(validated.get('air_temperature', 298))
        process = float(validated.get('process_temperature', 308))
        rpm = int(validated.get('rotational_speed', 1500))
        torque = float(validated.get('torque', 40))
        wear = int(validated.get('tool_wear', 0))

        return {
            # Raw telemetry
            "air_temperature":      air,
            "process_temperature":  process,
            "rotational_speed":     rpm,
            "torque":               torque,
            "tool_wear":            wear,
            # Derived
            "temp_delta":           derived["temp_delta"],
            "rpm_torque":           round((rpm * torque) / 1000.0, 4),
            "wear_rate":            derived["wear_rate"],
            # Contextual (defaults for missing)
            "machine_id":           int(ctx.get("machine_id", -1)),
            "timestamp":            ctx.get("timestamp", ""),
            "days_since_maint":     int(ctx.get("days_since_maint", -1)),
            "open_work_orders":     int(ctx.get("open_work_orders", 0)),
            "recent_interventions": int(ctx.get("recent_interventions", 0)),
            "machine_status":       str(ctx.get("machine_status", "OPERATIONNELLE")),
            # Time-series context
            "sequence_length":      int(ctx.get("sequence_length", 0)),
            "tool_wear_delta":      float(ctx.get("tool_wear_delta", 0.0)),
        }

    @staticmethod
    def build_time_series_from_logs(
        machine_id: int,
        logs: List[Dict],
        n: int = 30,
    ) -> List[Dict]:
        """
        Build a time-ordered list of FeatureSnapshot dicts from prediction log entries.

        Args:
            machine_id: Machine ID to filter logs
            logs: List of ml_prediction_log dicts (already fetched from DB).
                  Each dict must have keys:
                  air_temperature, process_temperature, rotational_speed,
                  torque, tool_wear, created_at (ISO string), risk_level
            n: Maximum number of recent entries to return (default 30)

        Returns:
            List of FeatureSnapshot dicts, oldest first, max n entries.
            Empty list if no matching logs.
        """
        # Filter by machine_id (logs may be pre-filtered by caller)
        machine_logs = [
            log for log in logs
            if int(log.get("machine_id", -1)) == machine_id
        ]
        # Sort oldest-first by created_at
        machine_logs.sort(key=lambda l: str(l.get("created_at", "")))
        # Take last n entries
        machine_logs = machine_logs[-n:]

        snapshots = []
        prev_wear = None
        for log in machine_logs:
            telemetry = {
                "air_temperature":      log.get("air_temperature", 298),
                "process_temperature":  log.get("process_temperature", 308),
                "rotational_speed":     log.get("rotational_speed", 1500),
                "torque":               log.get("torque", 40),
                "tool_wear":            log.get("tool_wear", 0),
            }
            wear = int(log.get("tool_wear", 0))
            wear_delta = float(wear - prev_wear) if prev_wear is not None else 0.0
            prev_wear = wear

            context = {
                "machine_id":       machine_id,
                "timestamp":        str(log.get("created_at", "")),
                "sequence_length":  len(snapshots) + 1,
                "tool_wear_delta":  wear_delta,
            }
            snapshots.append(FeatureStore.extract_full_snapshot(telemetry, context))

        return snapshots


# Global feature store instance
feature_store = FeatureStore()


def extract_features(telemetry: Dict, model: str = "p1") -> List[float]:
    """
    Convenience function to extract features for a model.
    
    Args:
        telemetry: Sensor readings
        model: Model name (p1-p6)
    
    Returns:
        Feature list
    """
    if model in ["p2", "p5", "p6"]:
        return feature_store.extract_6_features(telemetry)
    return feature_store.extract_5_features(telemetry)


def validate_and_extract(telemetry: Dict, model: str = "p1") -> List[float]:
    """
    Validate telemetry and extract features.

    Args:
        telemetry: Raw sensor readings
        model: Model name

    Returns:
        Validated feature list
    """
    validated = feature_store.validate_telemetry(telemetry)
    return extract_features(validated, model)


if __name__ == "__main__":
    # Quick smoke test
    snap = FeatureStore.extract_full_snapshot(
        {"air_temperature": 300, "process_temperature": 310,
         "rotational_speed": 1500, "torque": 40, "tool_wear": 50},
        {"machine_id": 1, "days_since_maint": 30}
    )
    print("Snapshot keys:", list(snap.keys()))

    logs = [{"machine_id": 1, "air_temperature": 300, "process_temperature": 310,
             "rotational_speed": 1500, "torque": 40, "tool_wear": w,
             "created_at": f"2024-01-{i+1:02d}", "risk_level": "LOW"}
            for i, w in enumerate([0, 10, 20, 30, 40])]
    ts = FeatureStore.build_time_series_from_logs(1, logs)
    print(f"Time series length: {len(ts)}")
    if ts:
        print("First snapshot tool_wear:", ts[0]["tool_wear"])
        print("Last snapshot tool_wear_delta:", ts[-1]["tool_wear_delta"])