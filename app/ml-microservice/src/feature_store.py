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
        'rotational_speed': (0, 3000),      # RPM
        'torque': (0, 100),                 # Nm
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