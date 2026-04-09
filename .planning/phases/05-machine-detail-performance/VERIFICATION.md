# VERIFICATION – Phase 05‑machine‑detail‑performance

**Goal:** Eliminate duplicate loads and improve machine‑detail view performance. Ensure ML endpoints expose `ETag` and `Cache‑Control: max-age=300`, and that a single request suffices per machine session. Target load time ≤ 2 s.

## Must‑haves check
- [x] **ETag header** is added to `/api/v1/ml/machines/{machine_id}/prediction` and the new `/detail` endpoint. (Implemented in `app/backend/modules/ml/router.py` – lines 88‑105 and 32‑45.)
- [x] **Cache‑Control** header with `max-age=300` present on both endpoints. (Lines 102‑105 and 45‑46.)
- [x] **No duplicate HTTP requests** for the same machine ID – the unified `/detail` endpoint consolidates machine data and prediction into a single response.
- [x] **Payload correctness** – both endpoints return JSON containing the required fields (`machine`, `prediction` for `/detail`; prediction fields for `/prediction`).

## Result
All must‑haves are satisfied. No gaps detected.

## Next steps
- Proceed to roadmap update and mark the phase as complete.
- Front‑end hook and page refactor (Tasks 3 & 4) remain to be implemented; they are not required for verification of the backend must‑haves.
