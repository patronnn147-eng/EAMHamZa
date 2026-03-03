"""
Verification Script for P5 Priority Prediction
Tests the integration of P5 model into MachineLearningService.
"""
import sys
import os

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

def test_p5_scenarios():
    print("="*60)
    print("VERIFYING P5 PRIORITY INTEGRATION")
    print("="*60)

    scenarios = [
        {"name": "HEALTHY", "air": 298.0, "process": 308.0, "rpm": 1550, "torque": 38.0, "wear": 10},
        {"name": "STRESSED", "air": 302.0, "process": 311.0, "rpm": 1400, "torque": 55.0, "wear": 180},
        {"name": "CRITICAL", "air": 304.0, "process": 313.0, "rpm": 1300, "torque": 65.0, "wear": 245},
    ]

    for sc in scenarios:
        machine = MockMachine(sc['air'], sc['process'], sc['rpm'], sc['torque'], sc['wear'])
        # Call calculate_rul which now includes priority
        result = MachineLearningService.calculate_rul(machine, [])
        
        print(f"Scenario: {sc['name']}")
        print(f" -> Failure Prob: {result['failure_probability']}%")
        print(f" -> Risk Level:   {result['risk_level']}")
        print(f" -> WO Priority:  {result['predicted_priority']}")
        print("-" * 30)

if __name__ == "__main__":
    test_p5_scenarios()
