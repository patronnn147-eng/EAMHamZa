"""
Verification Script for P4 Anomaly Detection
Tests the integration of P4 model into MachineLearningService.
"""
import sys
import os
import numpy as np

# Add app/backend to path to import models and services
sys.path.append(os.path.join(os.getcwd(), 'app', 'backend'))

from modules.ml.ml_predictive import MachineLearningService

class MockMachine:
    def __init__(self, air, process, rpm, torque, wear):
        self.id = 1
        self.nom = "Test Machine"
        self.air_temperature = air
        self.process_temperature = process
        self.rotational_speed = rpm
        self.torque = torque
        self.tool_wear = wear

def test_p4_scenarios():
    print("="*60)
    print("VERIFYING P4 ANOMALY INTEGRATION")
    print("="*60)

    scenarios = [
        {"name": "NORMAL",   "air": 298.0, "process": 308.0, "rpm": 1500, "torque": 40.0, "wear": 10},
        {"name": "OUTLIER",  "air": 305.0, "process": 315.0, "rpm": 3000, "torque": 80.0, "wear": 250},
        {"name": "EXTREME",  "air": 310.0, "process": 320.0, "rpm": 100,  "torque": 90.0, "wear": 300},
    ]

    for sc in scenarios:
        machine = MockMachine(sc['air'], sc['process'], sc['rpm'], sc['torque'], sc['wear'])
        result = MachineLearningService.calculate_rul(machine, [])
        
        print(f"Scenario: {sc['name']}")
        print(f" -> Telemetry:   RPM={sc['rpm']}, Torque={sc['torque']}, Wear={sc['wear']}")
        print(f" -> Is Anomaly:  {result['is_anomaly']}")
        print(f" -> Anom Score:  {result['anomaly_score']}")
        print("-" * 30)

if __name__ == "__main__":
    test_p4_scenarios()
