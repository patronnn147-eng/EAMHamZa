import joblib
import numpy as np
import argparse

# 1. Load the saved model
MODEL_PATH = 'basic_machine_model.pkl'
model = joblib.load(MODEL_PATH)

def predict_failure(air_temp, proc_temp, rpm, torque, tool_wear):
    # Prepare input in the same order as trained:
    # ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    input_data = np.array([[air_temp, proc_temp, rpm, torque, tool_wear]])
    
    prediction = model.predict(input_data)[0]
    probability = model.predict_proba(input_data)[0]
    
    status = "[FAILURE PREDICTED]" if prediction == 1 else "[MACHINE HEALTHY]"
    prob_failure = probability[1] * 100
    
    print("-" * 30)
    print(f"Prediction: {status}")
    print(f"Risk of Failure: {prob_failure:.2f}%")
    print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict Machine Failure")
    parser.add_argument("--air", type=float, help="Air Temp [K]", required=True)
    parser.add_argument("--process", type=float, help="Process Temp [K]", required=True)
    parser.add_argument("--rpm", type=float, help="Rotational Speed [rpm]", required=True)
    parser.add_argument("--torque", type=float, help="Torque [Nm]", required=True)
    parser.add_argument("--wear", type=float, help="Tool Wear [min]", required=True)
    
    args = parser.parse_args()
    
    predict_failure(args.air, args.process, args.rpm, args.torque, args.wear)
