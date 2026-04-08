# Phase 03: In-Memory TTL Cache - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a lightweight in-memory TTL cache for ML prediction results to avoid expensive recomputation on every request.
</domain>

<decisions>
## Implementation Decisions

### Cache Implementation
- Module-level `_prediction_cache: dict[int, tuple[Any, datetime]] = {}`
- `CACHE_TTL_MINUTES = 5` - cache expires after 5 minutes
- `get_cached_prediction(machine_id)` - returns cached result if valid
- `set_cached_prediction(machine_id, result)` - stores result with timestamp

### Integration
- In `calculate_rul` function: check cache first, compute if miss, store result
- Pure in-memory Python - NO Redis or external services
- Cache key is machine_id

### API Response
- Add `Cache-Control: max-age=300` header to response using JSONResponse
- DO NOT change response shape or endpoint URL

### Claude's Discretion
- Keep existing error handling
- Cache only the final prediction result, not intermediate computations
- Cache invalidation: automatic via TTL (no manual invalidation needed)

</decisions>

<specifics>
## Specific Requirements

1. At TOP of ml_predictive.py (with other module-level vars):
   ```python
   from datetime import datetime, timedelta
   from typing import Any, Optional

   _prediction_cache: dict[int, tuple[Any, datetime]] = {}
   CACHE_TTL_MINUTES = 5

   def get_cached_prediction(machine_id: int) -> Optional[dict]:
       if machine_id in _prediction_cache:
           result, timestamp = _prediction_cache[machine_id]
           if datetime.utcnow() - timestamp < timedelta(minutes=CACHE_TTL_MINUTES):
               return result
           del _prediction_cache[machine_id]
       return None

   def set_cached_prediction(machine_id: int, result: dict) -> None:
       _prediction_cache[machine_id] = (result, datetime.utcnow())
   ```

2. In calculate_rul function:
   ```python
   cached = get_cached_prediction(machine_id)
   if cached:
       return cached
   # ... existing computation ...
   set_cached_prediction(machine_id, result)
   return result
   ```

3. In router.py for prediction endpoint:
   ```python
   from fastapi.responses import JSONResponse
   return JSONResponse(content=result, headers={"Cache-Control": "max-age=300"})
   ```

4. No changes to response shape or endpoint URL

</specifics>

<deferred>
## Deferred Ideas

(None - stayed within optimization scope)

</deferred>

---

*Phase: 03-cache*
*Context gathered: 2026-04-03*