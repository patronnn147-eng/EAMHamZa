# C9 — MLOps Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Model registry + pkl-sync detection, drift detection over `ml_prediction_logs`, and a guarded ADMIN-triggered retraining endpoint, surfaced on the ADMIN ML dashboard, plus a CI sync check.

**Architecture:** Three pure service cores (`model_registry`, `drift`, `retraining_advisor`) + two ADMIN endpoints on the existing ml router (reusing `RetrainingService` and `get_model_metrics`) + a CI script + a dashboard table.

**Tech Stack:** FastAPI/SQLAlchemy async, pytest (`tests/backend/*.test.py`); React 19 + TS, vitest. No new deps (PSI is hand-rolled, stdlib only).

## Conventions
- Backend tests `tests/backend/<n>.test.py`, run `python -m pytest tests/backend/<n>.test.py -v` (import `from modules...`).
- ADMIN guard pattern (from chat.py): `if not current_user.role or current_user.role.value != "ADMIN": raise HTTPException(status_code=403, detail="ADMIN role required.")`.
- ml router lives in `app/backend/modules/ml/router.py`, prefix `/api/v1/ml`, deps `get_db`, `get_current_user`, `Utilisateurs`; `get_model_metrics` already imported there.
- Model files in `app/backend/modules/ml/models/` and `app/ml-microservice/models/`.
- Frontend POST pattern: `fetch(`${API}/...`, {method,headers:{Authorization,Content-Type},body})`, `API=import.meta.env.VITE_API_BASE_URL||''`, token `localStorage.getItem('access_token')`.

## Files
Create: `modules/ml/services/model_registry.py`, `modules/ml/services/drift.py`, `modules/ml/services/retraining_advisor.py`, `app/backend/scripts/check_model_sync.py`, `app/frontend/src/modules/admin/ml/ModelHealthTable.tsx`; tests `tests/backend/model_registry.test.py`, `tests/backend/drift.test.py`, `tests/backend/retraining_advisor.test.py`.
Modify: `modules/ml/router.py` (2 endpoints + dir consts + drift-rows helper); `app/frontend/src/modules/admin/ml/MLDashboard.tsx` (mount table).

---

## Task 1: `model_registry.py` (pure)

**Files:** Create `app/backend/modules/ml/services/model_registry.py` · Test `tests/backend/model_registry.test.py`

- [ ] **Step 1: Failing test** — `tests/backend/model_registry.test.py`:
```python
import os
from modules.ml.services.model_registry import scan_models, check_sync, MODEL_CATALOG


def _write(d, name, data):
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(data)


def test_identical_files_match(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"same"); _write(b, fn, b"same")
    rows = scan_models(str(a), str(b))
    row = next(r for r in rows if r["filename"] == fn)
    assert row["in_backend"] and row["in_micro"] and row["hash_match"]
    assert check_sync(str(a), str(b)) == []


def test_hash_mismatch_flagged(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"one"); _write(b, fn, b"two")
    div = check_sync(str(a), str(b))
    assert {"filename": fn, "reason": "hash_mismatch"} in div


def test_missing_in_microservice(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    fn = MODEL_CATALOG[0]["filename"]
    _write(a, fn, b"x")
    div = check_sync(str(a), str(b))
    assert {"filename": fn, "reason": "missing_in_microservice"} in div
```

- [ ] **Step 2: Run → FAIL** (`python -m pytest tests/backend/model_registry.test.py -v`).

- [ ] **Step 3: Implement**:
```python
"""Model registry + pkl-sync check across the two model directories."""
import hashlib
import os

MODEL_CATALOG = [
    {"key": "p1", "label": "Probabilité de panne",   "filename": "basic_machine_model.pkl"},
    {"key": "p2", "label": "Type de panne",          "filename": "ml_model_p2_failure_type.pkl"},
    {"key": "p3", "label": "Durée de vie restante",  "filename": "ml_model_p3_rul.pkl"},
    {"key": "p4", "label": "Détection d'anomalie",   "filename": "ml_model_p4_anomaly_v2.pkl"},
    {"key": "p5", "label": "Priorité",               "filename": "ml_model_p5_priority.pkl"},
    {"key": "p6", "label": "Planification",          "filename": "ml_model_p6_schedule.pkl"},
    {"key": "p7", "label": "Besoin en pièces",       "filename": "ml_model_p7_parts_demand.pkl"},
]


def _file_hash(path: str):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def scan_models(backend_dir: str, micro_dir: str) -> list:
    out = []
    for m in MODEL_CATALOG:
        bp = os.path.join(backend_dir, m["filename"])
        mp = os.path.join(micro_dir, m["filename"])
        bh, mh = _file_hash(bp), _file_hash(mp)
        out.append({
            **m,
            "in_backend": bh is not None,
            "in_micro": mh is not None,
            "hash_match": bh is not None and bh == mh,
            "size_backend": os.path.getsize(bp) if bh else None,
            "mtime_backend": os.path.getmtime(bp) if bh else None,
        })
    return out


def check_sync(backend_dir: str, micro_dir: str) -> list:
    div = []
    for m in MODEL_CATALOG:
        bp = os.path.join(backend_dir, m["filename"])
        mp = os.path.join(micro_dir, m["filename"])
        bh, mh = _file_hash(bp), _file_hash(mp)
        if bh is None and mh is None:
            continue
        if bh is None:
            div.append({"filename": m["filename"], "reason": "missing_in_backend"})
        elif mh is None:
            div.append({"filename": m["filename"], "reason": "missing_in_microservice"})
        elif bh != mh:
            div.append({"filename": m["filename"], "reason": "hash_mismatch"})
    return div
```

- [ ] **Step 4: Run → PASS** (3 tests).
- [ ] **Step 5: Commit**: `git add app/backend/modules/ml/services/model_registry.py tests/backend/model_registry.test.py && git commit -m "feat(mlops): model registry + pkl-sync check (pure)"`

---

## Task 2: `drift.py` (pure)

**Files:** Create `app/backend/modules/ml/services/drift.py` · Test `tests/backend/drift.test.py`

- [ ] **Step 1: Failing test**:
```python
import random
from modules.ml.services.drift import population_stability_index, compute_drift


def test_psi_zero_for_identical():
    xs = [float(i % 10) for i in range(200)]
    assert population_stability_index(xs, xs) < 0.01


def test_psi_large_for_shift():
    base = [random.gauss(0, 1) for _ in range(500)]
    shifted = [random.gauss(3, 1) for _ in range(500)]
    assert population_stability_index(base, shifted) > 0.25


def test_compute_drift_stable_vs_drifting():
    sensors = ("torque",)
    base = [{"torque": 40.0 + (i % 5)} for i in range(50)]
    same = [{"torque": 40.0 + (i % 5)} for i in range(50)]
    assert compute_drift(base, same, sensors)["verdict"] == "stable"
    shifted = [{"torque": 80.0 + (i % 5)} for i in range(50)]
    assert compute_drift(base, shifted, sensors)["verdict"] == "drifting"


def test_insufficient_data():
    assert compute_drift([], [], ("torque",))["verdict"] == "insufficient_data"
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement**:
```python
"""Drift detection over logged predictions — PSI + mean shift. Pure, stdlib only."""
import math

SENSORS = ("air_temperature", "process_temperature", "rotational_speed", "torque", "tool_wear")
_ORDER = {"stable": 0, "watch": 1, "drifting": 2}


def population_stability_index(baseline, recent, bins: int = 10) -> float:
    if not baseline or not recent:
        return 0.0
    lo, hi = min(baseline), max(baseline)
    if hi == lo:
        return 0.0
    width = (hi - lo) / bins

    def dist(xs):
        counts = [0] * bins
        for x in xs:
            idx = int((x - lo) / width)
            idx = 0 if idx < 0 else bins - 1 if idx >= bins else idx
            counts[idx] += 1
        n = len(xs)
        return [(c / n) or 1e-6 for c in counts]

    b, r = dist(baseline), dist(recent)
    return sum((r[i] - b[i]) * math.log(r[i] / b[i]) for i in range(bins))


def compute_drift(baseline_rows, recent_rows, sensors=SENSORS) -> dict:
    if len(baseline_rows) < 5 or len(recent_rows) < 5:
        return {"verdict": "insufficient_data", "sensors": {}}
    out, worst = {}, "stable"
    for s in sensors:
        b = [r[s] for r in baseline_rows if r.get(s) is not None]
        rc = [r[s] for r in recent_rows if r.get(s) is not None]
        if len(b) < 5 or len(rc) < 5:
            continue
        psi = population_stability_index(b, rc)
        bmean = sum(b) / len(b)
        rmean = sum(rc) / len(rc)
        shift = 0.0 if bmean == 0 else (rmean - bmean) / abs(bmean) * 100
        status = "drifting" if psi >= 0.25 else "watch" if psi >= 0.1 else "stable"
        out[s] = {"psi": round(psi, 3), "mean_shift_pct": round(shift, 1), "status": status}
        if _ORDER[status] > _ORDER[worst]:
            worst = status
    if not out:
        return {"verdict": "insufficient_data", "sensors": {}}
    return {"verdict": worst, "sensors": out}
```

- [ ] **Step 4: Run → PASS** (4 tests).
- [ ] **Step 5: Commit**: `git add app/backend/modules/ml/services/drift.py tests/backend/drift.test.py && git commit -m "feat(mlops): PSI drift detection (pure)"`

---

## Task 3: `retraining_advisor.py` (pure)

**Files:** Create `app/backend/modules/ml/services/retraining_advisor.py` · Test `tests/backend/retraining_advisor.test.py`

- [ ] **Step 1: Failing test**:
```python
from modules.ml.services.retraining_advisor import recommend_retraining


def test_recommends_on_enough_data():
    r = recommend_retraining(60, "stable", min_points=50)
    assert r["recommended"] and r["reasons"]


def test_recommends_on_drift():
    r = recommend_retraining(0, "drifting")
    assert r["recommended"]


def test_no_recommendation_when_quiet():
    r = recommend_retraining(3, "stable")
    assert not r["recommended"] and r["reasons"] == []
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement**:
```python
"""Deterministic guarded-retraining recommendation."""


def recommend_retraining(new_data_points: int, drift_verdict: str, min_points: int = 50) -> dict:
    reasons = []
    if new_data_points >= min_points:
        reasons.append(f"{new_data_points} nouvelles données disponibles")
    if drift_verdict == "drifting":
        reasons.append("dérive détectée dans les capteurs")
    return {"recommended": bool(reasons), "reasons": reasons}
```

- [ ] **Step 4: Run → PASS** (3 tests).
- [ ] **Step 5: Commit**: `git add app/backend/modules/ml/services/retraining_advisor.py tests/backend/retraining_advisor.test.py && git commit -m "feat(mlops): guarded retraining advisor (pure)"`

---

## Task 4: endpoints on the ml router

**Files:** Modify `app/backend/modules/ml/router.py`

- [ ] **Step 1: Confirm the prediction-log model class name**
Run: `grep -nE "class .*:" app/backend/models/ml_prediction_log.py`
Use that class (referred to below as `MlPredictionLog`) — adjust the import to the real name.

- [ ] **Step 2: Add imports + dir constants** near the top of `router.py` (after existing imports):
```python
from pathlib import Path
from models.ml_prediction_log import MlPredictionLog  # adjust to real class name

_BACKEND_MODELS = str(Path(__file__).parent / "models")
_MICRO_MODELS = str(Path(__file__).resolve().parents[3] / "ml-microservice" / "models")
```

- [ ] **Step 3: Add a drift-rows helper + the two endpoints** at the end of `router.py`:
```python
from datetime import datetime, timezone, timedelta
from modules.ml.services.model_registry import scan_models, check_sync
from modules.ml.services.drift import compute_drift, SENSORS
from modules.ml.services.retraining_advisor import recommend_retraining
from modules.ml.services.ml_retraining import RetrainingService


async def _drift_rows(db: AsyncSession, start, end):
    cols = [getattr(MlPredictionLog, s) for s in SENSORS]
    stmt = select(*cols).where(
        MlPredictionLog.created_at >= start, MlPredictionLog.created_at < end
    ).limit(2000)
    res = await db.execute(stmt)
    return [dict(zip(SENSORS, row)) for row in res.all()]


def _require_admin(current_user: Utilisateurs):
    if not current_user.role or current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required.")


@router.get("/model-health")
async def model_health(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    _require_admin(current_user)
    models = scan_models(_BACKEND_MODELS, _MICRO_MODELS)
    divergences = check_sync(_BACKEND_MODELS, _MICRO_MODELS)
    now = datetime.now(timezone.utc)
    try:
        baseline = await _drift_rows(db, now - timedelta(days=60), now - timedelta(days=30))
        recent = await _drift_rows(db, now - timedelta(days=14), now)
        drift = compute_drift(baseline, recent)
    except Exception:
        drift = {"verdict": "insufficient_data", "sensors": {}}
    try:
        metrics = await get_model_metrics()
    except Exception:
        metrics = {"success": False}
    try:
        stats = await RetrainingService.get_retraining_stats(db)
        ndp = int(stats.get("new_data_points", 0))
    except Exception:
        ndp = 0
    retrain = recommend_retraining(ndp, drift["verdict"])
    return {"models": models, "divergences": divergences,
            "metrics": metrics, "drift": drift, "retrain": retrain}


class RetrainRequest(BaseModel):
    model_type: str = "all"


@router.post("/retrain")
async def retrain(
    body: RetrainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    _require_admin(current_user)
    return await RetrainingService.run_retraining_pipeline(db, body.model_type)
```
Note: `select`, `BaseModel`, `HTTPException`, `AsyncSession`, `Depends`, `get_db`, `get_current_user`, `Utilisateurs`, `get_model_metrics` are already imported in router.py — do not re-import. Place module-level `from ... import` lines with the other top imports if the linter prefers, but function-local is fine to avoid circulars.

- [ ] **Step 4: Import-check**
Run: `cd app/backend && python -c "import sys;sys.path.insert(0,'.'); import modules.ml.router as r; print(sorted(p.path for p in r.router.routes if 'model-health' in p.path or '/retrain' in p.path))"`
Expected: `['/api/v1/ml/model-health', '/api/v1/ml/retrain']` (prefix may differ — confirm the ml router prefix; paths must contain `model-health` and `retrain`).

- [ ] **Step 5: Commit**: `git add app/backend/modules/ml/router.py && git commit -m "feat(mlops): ADMIN model-health + guarded retrain endpoints"`

---

## Task 5: CI sync script

**Files:** Create `app/backend/scripts/check_model_sync.py`

- [ ] **Step 1: Implement**:
```python
"""CI gate: fail if the two model dirs diverge. Exit 1 on divergence, else 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/backend
from modules.ml.services.model_registry import check_sync

BACKEND = Path(__file__).resolve().parents[1] / "modules" / "ml" / "models"
MICRO = Path(__file__).resolve().parents[2] / "ml-microservice" / "models"

div = check_sync(str(BACKEND), str(MICRO))
if div:
    print("Model sync divergences:")
    for d in div:
        print(f"  {d['filename']}: {d['reason']}")
    sys.exit(1)
print("Models in sync.")
sys.exit(0)
```

- [ ] **Step 2: Run it** (documents current state; expected to report the known divergence, exit 1):
Run: `cd C:/Users/Admin/Downloads/EAM/EAMSagemCom && python app/backend/scripts/check_model_sync.py`
Expected: lists divergences (e.g. `ml_model_p3_rul.pkl` / `feature_pipeline_v3.pkl` not relevant — only catalog files; if a catalog file diverges it prints), exit code 1 OR "Models in sync." if all catalog files match. Either way it runs without traceback.

- [ ] **Step 3: Commit**: `git add app/backend/scripts/check_model_sync.py && git commit -m "feat(mlops): CI script — fail build on model dir divergence"`

---

## Task 6: frontend model-health table

**Files:** Create `app/frontend/src/modules/admin/ml/ModelHealthTable.tsx` · Modify `app/frontend/src/modules/admin/ml/MLDashboard.tsx`

- [ ] **Step 1: Create `ModelHealthTable.tsx`**:
```tsx
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface ModelRow { key: string; label: string; in_backend: boolean; in_micro: boolean; hash_match: boolean; mtime_backend: number | null }
interface Health { models: ModelRow[]; divergences: { filename: string; reason: string }[]; drift: { verdict: string }; retrain: { recommended: boolean; reasons: string[] } }

function ago(mtime: number | null): string {
  if (!mtime) return '—';
  const d = Math.floor((Date.now() / 1000 - mtime) / 86400);
  return d <= 0 ? "aujourd'hui" : `il y a ${d} j`;
}

export function ModelHealthTable() {
  const [h, setH] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await fetch(`${API}/api/v1/ml/model-health`, { headers: { Authorization: `Bearer ${token()}` } });
      if (r.ok) setH(await r.json());
    } catch { /* leave null */ }
  };
  useEffect(() => { load(); }, []);

  const retrain = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/ml/retrain`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
        body: JSON.stringify({ model_type: 'all' }),
      });
      const j = await r.json();
      toast.success(j?.message ?? 'Réentraînement lancé.');
      load();
    } catch { toast.error('Réentraînement indisponible.'); }
    finally { setBusy(false); }
  };

  if (!h) return <div className="h-32 rounded-lg bg-slate-800 animate-pulse" />;

  return (
    <div className="space-y-3">
      {h.divergences.length > 0 && (
        <div className="flex gap-2 items-center rounded-lg bg-red-950 border border-red-800 px-4 py-2 text-sm text-red-200">
          <AlertTriangle className="h-4 w-4" /> {h.divergences.length} modèle(s) désynchronisé(s) entre les deux dossiers.
        </div>
      )}
      <div className="rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 text-blue-300 text-xs">
            <tr><th className="text-left px-3 py-2">Modèle</th><th className="text-left px-3 py-2">Synchro</th><th className="text-left px-3 py-2">Dernier entraînement</th></tr>
          </thead>
          <tbody>
            {h.models.map((m) => (
              <tr key={m.key} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-100">{m.label}</td>
                <td className="px-3 py-2">
                  {m.in_backend && m.in_micro && m.hash_match
                    ? <span className="text-emerald-400 inline-flex items-center gap-1"><CheckCircle className="h-3.5 w-3.5" /> à jour</span>
                    : <span className="text-red-400 inline-flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5" /> {!m.in_micro ? 'manquant côté service' : !m.in_backend ? 'manquant côté moteur' : 'diffère'}</span>}
                </td>
                <td className="px-3 py-2 text-blue-300">{ago(m.mtime_backend)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3">
        {h.retrain.recommended && <span className="text-xs text-amber-400">Réentraînement recommandé : {h.retrain.reasons.join(', ')}</span>}
        <button onClick={() => { if (confirm('Lancer le réentraînement des modèles ?')) retrain(); }} disabled={busy}
          className="ml-auto inline-flex items-center gap-2 text-xs font-medium text-blue-200 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 hover:bg-slate-700/60 disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} /> Réentraîner
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Mount in `MLDashboard.tsx`** — add `import { ModelHealthTable } from './ModelHealthTable';` and render `<ModelHealthTable />` near the top of the dashboard body (after the page header). Confirm the insertion compiles.

- [ ] **Step 3: Type-check**
Run: `cd app/frontend && npx tsc --noEmit 2>&1 | grep -E "ModelHealthTable|MLDashboard" || echo clean`
Expected: `clean`.

- [ ] **Step 4: Commit**: `git add app/frontend/src/modules/admin/ml/ModelHealthTable.tsx app/frontend/src/modules/admin/ml/MLDashboard.tsx && git commit -m "feat(mlops): ADMIN model-health table + guarded retrain button"`

---

## Task 7: verification

- [ ] **Step 1: Backend** — `python -m pytest tests/backend/model_registry.test.py tests/backend/drift.test.py tests/backend/retraining_advisor.test.py -v` → all PASS.
- [ ] **Step 2: Router import** — `cd app/backend && python -c "import sys;sys.path.insert(0,'.'); import modules.ml.router"` → no error.
- [ ] **Step 3: CI script runs** — `python app/backend/scripts/check_model_sync.py` (exit 0 or 1, no traceback).
- [ ] **Step 4: Frontend** — `cd app/frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"` → `0`; `npx vitest run` → existing suite still green.
- [ ] **Step 5: Manual smoke** — login ADMIN, open ML dashboard, confirm model-health table + divergence banner; non-admin gets 403 on `/model-health`.

## Self-Review (completed)
- **Coverage:** registry+sync → T1; drift → T2; advisor → T3; endpoints (model-health + guarded retrain) → T4; CI → T5; dashboard → T6; tests → T7. Guarded retraining (ADMIN-only, reuse `run_retraining_pipeline`) honored — no auto path. Out-of-scope (MLflow, cron) excluded.
- **Placeholders:** none — full code per step; the `MlPredictionLog` class-name and ml-router-prefix verifications are explicit confirm steps.
- **Consistency:** `SENSORS` defined in `drift.py` and imported by the router; `check_sync`/`scan_models` signatures stable across T1/T4/T5; `recommend_retraining(new_data_points, drift_verdict, min_points)` stable T3↔T4; endpoint JSON keys (`models/divergences/drift/retrain`) match the frontend `Health` interface in T6.
