"""
Verification script for P3 RUL Estimation.
Tests the MachineLearningService integration.
"""
import sys
import os
import numpy as np

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'app', 'backend'))

from modules.ml.ml_predictive import MachineLearningService

# Mock Machine object
class MockMachine:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    id = 1
    nom = "Test Machine"

def test_rul_prediction():
    print("--- Testing P3 RUL Prediction ---")
    
    # High wear machine
    machine_bad = MockMachine(
        air_temperature=305.0,
        process_temperature=315.0,
        rotational_speed=1300,
        torque=65.0,
        tool_wear=240
    )
    
    # Healthy machine
    machine_good = MockMachine(
        air_temperature=298.0,
        process_temperature=308.0,
        rotational_speed=1550,
        torque=35.0,
        tool_wear=10
    )
    
    rul_bad = MachineLearningService._predict_model_rul(machine_bad)
    rul_good = MachineLearningService._predict_model_rul(machine_good)
    
    if rul_bad is None or rul_good is None:
        print("[FAIL] Model returned None. Check if P3 model is loaded correctly.")
        return

    print(f"High Wear Machine RUL: {rul_bad:.1f} cycles")
    print(f"Healthy Machine RUL  : {rul_good:.1f} cycles")
    
    if rul_bad < rul_good:
        print("[OK] Verification Successful: Model logic is correctly integrated.")
    else:
        print("[FAIL] High wear machine should have lower RUL than healthy machine.")

if __name__ == "__main__":
    try:
        test_rul_prediction()
    except Exception as e:
        print(f"[ERROR] Verification Failed: {e}")
