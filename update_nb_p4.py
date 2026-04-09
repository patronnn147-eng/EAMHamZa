import json
import os

notebook_path = 'ml_prediction.ipynb'

if not os.path.exists(notebook_path):
    print(f"Error: {notebook_path} not found")
    exit(1)

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 1. Update Intro Cell
for cell in nb['cells']:
    if cell.get('id') == 'intro':
        cell['source'] = [
            "# 🛠️ EAM Predictive Maintenance Dashboard\n",
            "\n",
            "Welcome to the consolidated testing environment for the ML Pipeline. This notebook allows you to:\n",
            "1. **P1 (Failure Prediction)**: Predict the overall probability of a machine failure.\n",
            "2. **P2 (Failure Type)**: Classify the specific root cause (TWF, HDF, PWF, OSF, RNF).\n",
            "3. **P3 (RUL Estimation)**: Estimate the Remaining Useful Life (RUL) in cycles.\n",
            "4. **P4 (Anomaly Detection)**: Detect unusual machine behavior using unsupervised learning.\n",
            "5. **P5 (Work Order Priority)**: Predict the urgency of the maintenance action.\n",
            "\n",
            "---"
        ]

# 2. Update Loading Cell
for cell in nb['cells']:
    if cell.get('id') == 'loading_code':
        cell['source'] = [
            "# --- Paths ---\n",
            "BASE_PATH = \".\"\n",
            "MODELS_DIR = \"app/backend/modules/ml/models\"\n",
            "CSV_PATH = \"ai4i2020.csv\"\n",
            "\n",
            "# --- Load Dataset ---\n",
            "df = pd.read_csv(CSV_PATH)\n",
            "print(f\"📊 Dataset loaded: {df.shape[0]} rows\")\n",
            "\n",
            "# --- Load Models ---\n",
            "try:\n",
            "    model_p1 = joblib.load(os.path.join(MODELS_DIR, \"basic_machine_model.pkl\"))\n",
            "    print(\"✅ P1 Model Loaded (Failure Prediction)\")\n",
            "    \n",
            "    data_p2 = joblib.load(os.path.join(MODELS_DIR, \"ml_model_p2_failure_type.pkl\"))\n",
            "    model_p2 = data_p2['model']\n",
            "    p2_labels = data_p2['labels']\n",
            "    print(\"✅ P2 Model Loaded (Failure Type)\")\n",
            "    \n",
            "    model_p3 = joblib.load(os.path.join(MODELS_DIR, \"ml_model_p3_rul.pkl\"))\n",
            "    print(\"✅ P3 Model Loaded (RUL Estimation)\")\n",
            "\n",
            "    model_p4 = joblib.load(os.path.join(MODELS_DIR, \"ml_model_p4_anomaly.pkl\"))\n",
            "    print(\"✅ P4 Model Loaded (Anomaly Detection)\")\n",
            "\n",
            "    data_p5 = joblib.load(os.path.join(MODELS_DIR, \"ml_model_p5_priority.pkl\"))\n",
            "    model_p5 = data_p5['model']\n",
            "    p5_labels = data_p5['labels']\n",
            "    print(\"✅ P5 Model Loaded (Work Order Priority)\")\n",
            "except Exception as e:\n",
            "    print(f\"❌ Error loading models: {e}\")"
        ]

# 3. Update Dashboard Cell
for cell in nb['cells']:
    if cell.get('id') == 'dashboard_code':
        cell['source'] = [
            "def run_ml_diagnostics(air_temp, process_temp, rpm, torque, wear):\n",
            "    # 1. Prepare Inputs\n",
            "    # P1/P3/P4/P5 use: [air, process, rpm, torque, wear]\n",
            "    # P2 uses: [air, process, rpm, torque, wear, temp_delta]\n",
            "    temp_delta = process_temp - air_temp\n",
            "    input_p1345 = np.array([[air_temp, process_temp, rpm, torque, wear]])\n",
            "    input_p2 = np.array([[air_temp, process_temp, rpm, torque, wear, temp_delta]])\n",
            "\n",
            "    # 2. Run Predictions\n",
            "    prob_fail = model_p1.predict_proba(input_p1345)[0, 1] * 100\n",
            "    predicted_rul = model_p3.predict(input_p1345)[0]\n",
            "    p2_preds = model_p2.predict(input_p2)[0]\n",
            "    p2_probs = [est.predict_proba(input_p2)[0, 1] * 100 for est in model_p2.estimators_]\n",
            "    \n",
            "    # P4 Detection (Anomaly)\n",
            "    is_anomaly_val = model_p4.predict(input_p1345)[0]\n",
            "    anomaly_score = model_p4.decision_function(input_p1345)[0]\n",
            "    \n",
            "    # P5 Prediction (Priority)\n",
            "    priority_idx = model_p5.predict(input_p1345)[0]\n",
            "    priority_label = p5_labels[priority_idx]\n",
            "\n",
            "    # 3. Print Professional Report\n",
            "    print(\"=\"*50)\n",
            "    print(\"🚀 MACHINE HEALTH DIAGNOSTIC REPORT\")\n",
            "    print(\"=\"*50)\n",
            "    print(f\"INPUTS: Temp Ratio: {temp_delta:.1f}K | RPM: {rpm} | Torque: {torque}Nm | Wear: {wear}min\")\n",
            "    print(\"-\"*50)\n",
            "    \n",
            "    # P1 Result\n",
            "    status_p1 = \"⚠️  DANGER\" if prob_fail > 50 else \"✅ HEALTHY\"\n",
            "    print(f\"[P1] FAILURE RISK         : {prob_fail:>6.1f}% -> {status_p1}\")\n",
            "    \n",
            "    # P3 Result\n",
            "    print(f\"[P3] EST. REMAINING LIFE  : {predicted_rul:>6.1f} cycles\")\n",
            "\n",
            "    # P4 Result\n",
            "    anom_status = \"🚨 ANOMALY DETECTED\" if is_anomaly_val == -1 else \"✅ NORMAL BEHAVIOR\"\n",
            "    print(f\"[P4] ANOMALY STATUS       : {anom_status} (Score: {anomaly_score:.4f})\")\n",
            "    \n",
            "    # P5 Result\n",
            "    print(f\"[P5] WO PRIORITY         :    {priority_label.upper()}\")\n",
            "    \n",
            "    # P2 Result\n",
            "    print(\"-\"*50)\n",
            "    print(\"[P2] ROOT CAUSE ANALYSIS:\")\n",
            "    for label, detected, p2_prob in zip(p2_labels, p2_preds, p2_probs):\n",
            "        mark = \"[X]\" if detected == 1 else \"[ ]\"\n",
            "        print(f\"    {mark} {label:3s}: {p2_prob:>5.1f}% confidence\")\n",
            "    print(\"=\"*50)\n",
            "\n",
            "# --- TEST CASE: Stressed Machine ---\n",
            "run_ml_diagnostics(air_temp=302.5, process_temp=312.0, rpm=1350, torque=62.0, wear=235)\n",
            "\n",
            "# --- TEST CASE: Healthy Machine ---\n",
            "run_ml_diagnostics(air_temp=298.0, process_temp=308.0, rpm=1550, torque=38.0, wear=15)\n",
            "\n",
            "# --- TEST CASE: Anomaly (Extreme RPM) ---\n",
            "run_ml_diagnostics(air_temp=300.0, process_temp=310.0, rpm=3000, torque=80.0, wear=250)"
        ]

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully.")
