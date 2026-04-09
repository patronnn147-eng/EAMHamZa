# ⚙️ Comprehensive PDCA Action Plan: ML Predictive Maintenance Integration

## 1. Introduction & Strategic Context
**Context:** Sagemcom's EAM (Enterprise Asset Management) system currently operates primarily on a **Reactive** and **Preventive (time-based)** maintenance strategy. While effective, this leads to unnecessary maintenance on healthy machines and unexpected breakdowns on stressed machines.
**Objective:** The integration of 6 Machine Learning (ML) models aims to shift the paradigm to **Predictive Maintenance**. This PDCA (Plan-Do-Check-Act) plan is the formal framework to deploy these models into the production environment, evaluate their real-world efficacy, and continuously refine them without disrupting daily operations.

---

## 2. PLAN (Planifier): Strategy, Scope & Baseline

The *Plan* phase defines exactly what we are testing, who is involved, and how we will objectively measure success. We cannot deploy ML to the entire factory on day one; we must define a controlled, measurable pilot.

### 2.1 Scope of the Pilot Deployment
*   **Target Functional Zone:** "Zone SMT" (Surface-Mount Technology). *Why?* Because SMT machines provide high-frequency, reliable sensor data (temperature, RPM, torque) and are bottlenecks in the production line. A failure here stops the entire factory.
*   **Duration:** 8 Weeks Total.
    *   *Phase 1: Shadow Mode (Weeks 1-3).* Models run in the backend but UI is hidden.
    *   *Phase 2: Active Mode (Weeks 4-8).* UI is revealed to pilot users.
*   **Target Personas:** 
    *   **2 Maintenance Managers (ChefOp):** Will use the system to assign work orders.
    *   **4 Senior Technicians:** Will execute the ML-suggested work orders and provide qualitative feedback.

### 2.2 Technical Integration Architecture (The "How")
*   **Data Ingestion:** Live telemetry (Air Temp, Process Temp, RPM, Torque, Tool Wear) is continuously fed into the PostgreSQL database `Machines` table.
*   **Inference Engine:** The FastAPI backend (`ml_predictive.py`) loads the `.pkl` models (Random Forest, XGBoost, Isolation Forest) into memory. It runs predictions every 5 minutes on live data.
*   **Data Flow:** The React frontend polls the backend. If `Failure Risk (P1)` > 70%, the machine row in the `PredictivePanel` turns **Red**, and an alert is generated.

### 2.3 Detailed Key Performance Indicators (KPIs)
To declare the pilot a success, we must hit these quantitative targets:
1.  **Downtime Reduction:** Reduce unexpected machine downtime in the SMT zone by **15%**. (Measured against the historical baseline of the previous 3 months).
2.  **Precision of P1 (Failure Risk):** Of all the machines flagged as "CRITICAL" by the model, at least **80%** must have a legitimate, verifiable issue when inspected by a technician (True Positives).
3.  **Accuracy of P2 (Root Cause):** The model's prediction of Failure Type (e.g., TWF, HDF) must match the technician's post-repair report at least **75%** of the time.
4.  **Backend Latency:** The addition of ML inference must not add more than **250ms** to the API response time.

---

## 3. DO (Déployer / Faire): Execution of the Pilot

The *Do* phase is the systematic rollout of the plan. It requires both technical deployment and human change-management.

### 3.1 Phase 1: Shadow Mode Execution (Weeks 1-3)
*What it is:* The models are live, but the users can't see them.
*   **Task 1:** Deploy the updated FastAPI container with the ML models to the staging server.
*   **Task 2:** Create a hidden database table `ml_shadow_logs`. Every time the backend calculates a prediction, save it here with a timestamp. 
*   **Task 3:** At the end of week 3, the Development Team compares the `ml_shadow_logs` against the actual `Ordres_intervention` created manually by the ChefOp. Did the ML predict the breakdowns that actually happened that week?

### 3.2 Phase 2: Active Pilot Execution (Weeks 4-8)
*What it is:* The UI is activated for the pilot users. The human workflow changes.
*   **Task 1 (Training):** Hold a 1-hour workshop with the ChefOp and Technicians. Explain what "Anomaly Score" (P4) and "RUL" (P3) technically mean. Show them the new dashboard.
*   **Task 2 (Workflow - ChefOp):** The ChefOp is instructed to start their morning by looking at the ML Dashboard. They must manually create an `Ordre_intervention` for any machine where the ML suggests a "CRITICAL" priority (Model P5).
*   **Task 3 (Workflow - Technician):** When a technician closes a work order on the React frontend, they will see a new dropdown: *"Actual Failure Type"*. They **must** fill this out, selecting TWF, HDF, PWF, OSF, or RNF. This is critical for validating Model P2.

---

## 4. CHECK (Contrôler / Vérifier): Data Analysis & Audit

The *Check* phase occurs at the end of the 8-week pilot. We extract the data and rigorously evaluate it against our KPIs from the *Plan* phase.

### 4.1 Quantitative Audit (The Hard Data)
*   **Audit P1 (Failure Prediction):** Calculate the confusion matrix. 
    *   *False Positives:* How many times did the ML scream "DANGER", but the technician arrived and found the machine perfectly fine? If this is high, technicians will lose trust in the system ("Alert Fatigue").
    *   *False Negatives:* How many machines broke down unexpectedly that the ML said were "Healthy"? We must analyze the telemetry leading up to that crash to see why the model missed it.
*   **Audit P3 (RUL - Remaining Useful Life):** Calculate the Mean Absolute Error (MAE) between the *Predicted Days to Failure* and the *Actual Days to Failure*. 
*   **Audit P6 (Scheduling):** Did scheduling maintenance on the exact day suggested by P6 result in zero production interruption? 

### 4.2 Qualitative Audit (The Human Element)
*   **Technician Debrief:** Conduct a structured interview with the 4 pilot technicians.
    *   *Question:* "Did the P5 Work Order Priority accurately reflect the urgency of the situation?"
    *   *Question:* "Were there any UI elements on the Predictive Panel that were confusing?"

---

## 5. ACT (Agir / Ajuster): Continuous Improvement

The *Act* phase closes the loop. We do not just look at the results; we use them to modify the system. This marks the end of one cycle and the beginning of the next.

### 5.1 Scenario A: The Models Underperformed (Data Drift or Bias)
If False Positives are > 20% or False Negatives are high:
*   **Action 1 (Data Collection):** Extract the new telemetry data and the technician-verified root causes from the past 8 weeks.
*   **Action 2 (Retraining):** Feed this new, highly-accurate data back into `ml_train_p1.py` and `ml_train_p2.py`. Re-tune the Random Forest hyperparameters (e.g., increase max_depth, adjust class weights to penalize false positives).
*   **Action 3 (UI Adjustment):** If technicians found the UI confusing, redesign the React components to simplify the data (e.g., change numerical scores to simple "Traffic Light" colors).
*   *Next Step:* Start a new PDCA cycle (Plan a shorter Phase 2 Pilot to test the newly trained models).

### 5.2 Scenario B: The Pilot Was Highly Successful (KPIs Met or Exceeded)
If the models accurately predicted failures and downtime was reduced by 15%:
*   **Action 1 (Standardization):** Deploy the ML Predictive Dashboard to the production server for ALL zones (Assemblage, Test, Injection) and ALL users.
*   **Action 2 (Process Automation):** Upgrade the backend architecture. If the P1 model detects a Failure Risk > 90% and P4 detects an Anomaly, the FastAPI backend will now *automatically* generate an `Ordre_intervention` in the PostgreSQL database, assigning it the status "Pending Validation". This removes the ChefOp as the bottleneck.
*   **Action 3 (Documentation):** Update the official Sagemcom ISO 9001 Maintenance Procedures manual to formally include ML Dashboard monitoring as a required daily task for managers.

---
*Prepared by: EAM Development Team*  
*Version: Final*
