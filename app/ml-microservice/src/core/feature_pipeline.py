from dataclasses import dataclass
from typing import List


@dataclass
class SensorReading:
    air_temp: float
    process_temp: float
    rpm: float
    torque: float
    tool_wear: float


class FeaturePipeline:
    @staticmethod
    def build_5(r: SensorReading) -> List[float]:
        """5 raw sensor features. Used by P3 and P4."""
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear]

    @staticmethod
    def build_7(r: SensorReading) -> List[float]:
        """7 features: 5 raw + temp_delta + rpm_torque. Used by P1, P2, P5, P6."""
        temp_delta = r.process_temp - r.air_temp
        rpm_torque = (r.rpm * r.torque) / 1000.0
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear,
                temp_delta, rpm_torque]
