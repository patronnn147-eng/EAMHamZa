---
phase: 03-ml-integration
plan: '01'
type: execute
wave: '1'
depends_on: []
files_modified:
  - app/backend/modules/ml/router.py
  - app/backend/modules/ml/ml_predictive.py
  - app/backend/modules/ml/models/
  - app/frontend/src/modules/shared/machines/components/PredictivePanel.tsx
autonomous: true
requirements:
  - ML-01
  - ML-02
user_setup: []

must_haves:
  truths:
    - ML prediction endpoint returns failure probability and RUL
    - Frontend displays predictive maintenance data
    - Trained models are loaded and functional
    - Risk level classification works
  artifacts:
    - path: app/backend/modules/ml/router.py
      provides: ML API endpoints
    - path: app/backend/modules/ml/ml_predictive.py
      provides: ML service with prediction logic
    - path: app/frontend/src/modules/shared/machines/components/PredictivePanel.tsx
      provides: Frontend ML prediction display
  key_links:
    - from: app/frontend/src/modules/shared/machines/components/PredictivePanel.tsx
      to: app/backend/modules/ml/router.py
      via: API call to /api/v1/ml/machines/{id}/prediction
      pattern: fetch.*ml/machines
---

<objective>
Verify ML Integration: predictive maintenance API, trained models, and frontend display are all working correctly.
</objective>

<context>
@.planning/phases/03-ml-integration/03-CONTEXT.md
@.planning/phases/03-ml-integration/03-RESEARCH.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify ML Prediction Endpoint</name>
  <files>app/backend/modules/ml/router.py, app/backend/modules/ml/ml_predictive.py</files>
  <action>
    Verify ML prediction functionality:
    1. Check /api/v1/ml/machines/{id}/prediction endpoint
    2. Verify response includes: failure_probability, risk_level, rul_days, predicted_failure_date
    3. Check ML service can load trained models
    4. Verify prediction logging to database
    
    Fix any issues found.
  </action>
  <verify>
    <automated>Test API endpoint:
    curl http://localhost:8000/api/v1/ml/machines/1/prediction
    (Should return prediction with probability, RUL, risk level)</automated>
  </verify>
  <done>ML prediction endpoint returns correct data structure</done>
</task>

<task type="auto">
  <name>Task 2: Verify Frontend Predictive Panel</name>
  <files>app/frontend/src/modules/shared/machines/components/PredictivePanel.tsx</files>
  <action>
    Verify frontend display:
    1. Check PredictivePanel.tsx calls correct API endpoint
    2. Verify it displays failure probability, risk level, RUL
    3. Check loading and error states
    4. Ensure integration with machine detail page
    
    Fix any issues found.
  </action>
  <verify>
    <automated>npm run build --prefix app/frontend (check for errors)</automated>
  </verify>
  <done>Frontend displays ML predictions correctly</done>
</task>

<task type="auto">
  <name>Task 3: Verify Trained Models</name>
  <files>app/backend/modules/ml/models/</files>
  <action>
    Verify trained models:
    1. Check all .pkl model files exist
    2. Verify models can be loaded by ML service
    3. Check model predictions are reasonable
    
    Document model capabilities.
  </action>
  <verify>
    <automated>ls -la app/backend/modules/ml/models/*.pkl</automated>
  </verify>
  <done>Trained models exist and are loadable</done>
</task>

</tasks>

<verification>
- ML endpoint returns correct data
- Frontend displays predictions
- Models are functional
- End-to-end flow works
</verification>

<success_criteria>
- ML prediction API works
- Frontend displays predictions
- Models are loaded
- Risk levels are calculated
</success_criteria>

<output>
After completion, create `.planning/phases/03-ml-integration/03-01-SUMMARY.md`
</output>
