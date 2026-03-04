# Phase 3: ML Integration - Research

**Researched:** 2026-03-04
**Phase:** 03 - ML Integration

---

## What We Need to Know

### Current State
- ML prediction API exists: GET /api/v1/ml/machines/{machine_id}/prediction
- ML service class exists with calculate_rul() method
- Trained models exist (.pkl files)
- Frontend PredictivePanel.tsx calls the API

### What's Implemented
- Failure probability calculation
- Risk level classification (LOW/MEDIUM/HIGH/CRITICAL)
- Remaining Useful Life (RUL) estimation
- Prediction logging to database
- Frontend display of predictions

---

## Verification Focus

This phase is primarily about verifying:
1. ML endpoint returns correct predictions
2. Frontend displays predictions properly
3. Models are loaded and working
4. Integration between backend and frontend is complete

---

## Common Pitfalls

1. **Model not loading** - Check if .pkl files exist and are valid
2. **Missing features** - Model may need specific telemetry inputs
3. **API errors** - Check response format matches frontend expectations

---

*Research complete: 2026-03-04*
