# Phase 02: ML Model Singleton - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor ML model loading to use singleton pattern - load .pkl file once at module initialization instead of on every API request.
</domain>

<decisions>
## Implementation Decisions

### Singleton Pattern
- Module-level `_MODEL` variable initialized to None
- `get_model()` function returns cached model or loads on first call
- File path: `os.path.join(os.path.dirname(__file__), "basic_machine_model.pkl")`

### Fallback Behavior
- If model file not found, `get_model()` returns None
- Calling code must handle gracefully by adding `"model_unavailable": true` to response

### API Response Shape (MUST NOT CHANGE)
```json
{
  "machine_id": int,
  "machine_name": str,
  "rul_days": float,
  "risk_level": str,  // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  "failure_probability": float,
  "predicted_failure_date": str  // ISO datetime
}
```

When model unavailable, add: `"model_unavailable": true`

### Claude's Discretion
- Keep existing prediction logic (RUL calculation, risk levels)
- Maintain same error handling patterns
- Performance verification: second call faster than first

</decisions>

<specifics>
## Specific Requirements

1. At TOP of ml_predictive.py (module level):
   - Add: `import joblib`, `import os`
   - Add: `_MODEL = None`
   - Add: `_MODEL_PATH = os.path.join(os.path.dirname(__file__), "basic_machine_model.pkl")`
   - Add: `get_model()` function with lazy loading

2. Replace every `joblib.load(...)` inside functions with `get_model()`

3. Add `"model_unavailable": true` when get_model() returns None

4. No changes to API response shape

5. Restart backend, call endpoint twice - second call should be faster

</specifics>

<deferred>
## Deferred Ideas

(None - stayed within optimization scope)

</deferred>

---

*Phase: 02-ml-singleton*
*Context gathered: 2026-04-03*