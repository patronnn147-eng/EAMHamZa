# C10 — Reusable "Why?" Everywhere Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach a plain-language "Why?" explanation (no ML jargon) to four AI surfaces — next-best-action, daily briefing, anomaly flag, machine health — via one reusable drawer fed by a shared contract, with an optional cached-LLM "explain in plain words" button.

**Architecture:** Pure per-surface producers emit a shared `WhyPayload`; one `WhyDrawer` renders any payload offline; an optional `POST /api/v1/why/explain` (cached LLM, never-raises fallback) phrases it. A reused backend threshold helper exposes `sensor_status` (°C + targets) on unified-health as the single source of truth.

**Tech Stack:** FastAPI + SQLAlchemy + Groq (`core.groq_client`), pytest (`tests/backend/*.test.py`); React 19 + TS + Tailwind, vitest pure-function tests (no RTL — logic lives in tested pure functions, components are thin).

---

## Conventions (follow exactly)
- Backend routers in `app/backend/modules/**` exposing `router: APIRouter` are auto-included. LLM via `from core.groq_client import get_groq_client` → `groq.chat(messages=[...])` → `resp["choices"][0]["message"]["content"]`.
- Reuse the cache pattern from `app/backend/modules/shared/services/dashboard_briefing.py` (in-memory dict, hash key, stale prune, never-raises).
- Backend tests: `tests/backend/<name>.test.py`, run `python -m pytest tests/backend/<name>.test.py -v` (conftest adds `app/backend` to path → import `from modules...` / `from services...`).
- Frontend pure tests: `*.test.ts` next to source, run `cd app/frontend && npx vitest run <path>`. No `@testing-library/react`.
- App theme: `bg-slate-800`/`border-slate-700`, white headings, `text-blue-300`, emerald/amber/red status. Icons `lucide-react`. Drawer = `@/components/ui/sheet`. Toasts = `sonner` (`toast`). Custom REST: `(client.apiCall as any).invoke({ url, method })` from `@/lib/api`.
- Reuse existing threshold logic in `app/backend/services/ai_prompts.py`: `_SENSOR_THRESHOLDS`, `_resolve_threshold_category`, `_sensor_status`.

## File Structure
**Backend create:** `app/backend/modules/shared/routes/why.py`; tests `tests/backend/sensor_status.test.py`, `tests/backend/why_explain.test.py`.
**Backend modify:** `app/backend/services/ai_prompts.py` (+`build_sensor_status`); `app/backend/modules/ml/router.py` (attach `sensor_status`); `app/backend/modules/shared/routes/dashboard.py` (+`facts` on briefing response).
**Frontend create (under `app/frontend/src/modules/shared/explain/`):** `whyTypes.ts`, `plainLanguage.ts` (+test), `producers/buildHealthWhy.ts` (+test), `producers/buildAnomalyWhy.ts` (+test), `producers/buildNbaWhy.ts` (+test), `producers/buildBriefingWhy.ts` (+test), `WhyButton.tsx`, `WhyDrawer.tsx`.
**Frontend modify:** `NextBestActions.tsx`, `BriefingBar.tsx`, `MLIntelligenceTab.tsx` (health + anomaly wiring).

---

## Task 1: Backend — `build_sensor_status` (pure)

**Files:** Modify `app/backend/services/ai_prompts.py` · Test `tests/backend/sensor_status.test.py`

- [ ] **Step 1: Write the failing test** — `tests/backend/sensor_status.test.py`:

```python
from services.ai_prompts import build_sensor_status


def test_temp_sensor_converted_to_celsius_and_flagged():
    # pickplace process_temperature warn_hi=315K crit_hi=320K
    rows = build_sensor_status("pickplace", "PickPlace-1", {
        "process_temperature": 318.15,  # 45.0 C, between warn and crit -> ATTENTION
        "torque": 10,                    # below warn_hi 18 -> NORMAL
    })
    proc = next(r for r in rows if r["key"] == "process_temperature")
    assert proc["unit"] == "°C"
    assert proc["value"] == 45.0
    assert proc["target"] == 41.85  # 315 - 273.15
    assert proc["status"] == "ATTENTION"
    torque = next(r for r in rows if r["key"] == "torque")
    assert torque["status"] == "NORMAL"
    assert torque["unit"] == "Nm"


def test_missing_readings_are_skipped_and_never_raises():
    rows = build_sensor_status("", "", {"torque": None})
    assert rows == []


def test_critique_when_above_crit_hi():
    rows = build_sensor_status("pickplace", "x", {"process_temperature": 321 + 273.15 - 273.15 + 273.15})
    # 321C is far above; ensure CRITIQUE path works with a clearly-over value
    rows = build_sensor_status("pickplace", "x", {"process_temperature": 600.0})
    proc = next(r for r in rows if r["key"] == "process_temperature")
    assert proc["status"] == "CRITIQUE"
```

- [ ] **Step 2: Run — verify FAIL**

Run: `python -m pytest tests/backend/sensor_status.test.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_sensor_status'`.

- [ ] **Step 3: Implement** — append to `app/backend/services/ai_prompts.py` (after `_sensor_status`, reusing existing constants):

```python
# Plain labels + units per sensor (FR, operator-facing). Temps reported in °C.
_SENSOR_META = [
    ("air_temperature",     "Température air",     "°C",     True),
    ("process_temperature", "Température procédé", "°C",     True),
    ("rotational_speed",    "Vitesse rotation",    "tr/min", False),
    ("torque",              "Couple",              "Nm",     False),
    ("tool_wear",           "Usure outil",         "min",    False),
]


def build_sensor_status(machine_type: str, machine_name: str, readings: dict) -> list:
    """Per-sensor NORMAL/ATTENTION/CRITIQUE with display value + safe target.

    Temps converted K→°C. Single source of truth for the frontend 'Why?' panels.
    Never raises; sensors with no reading are omitted.
    """
    category = _resolve_threshold_category(machine_type or "", machine_name or "")
    thresholds = _SENSOR_THRESHOLDS[category]
    out = []
    for key, label, unit, is_temp in _SENSOR_META:
        v = readings.get(key)
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        th = thresholds[key]              # (warn_lo, warn_hi, crit_lo, crit_hi)
        status = _sensor_status(fv, th)
        warn_hi = th[1]
        if is_temp:
            value = round(fv - 273.15, 1)
            target = round(warn_hi - 273.15, 1) if warn_hi is not None else None
        else:
            value = round(fv, 1)
            target = warn_hi
        out.append({"key": key, "label": label, "value": value,
                    "unit": unit, "status": status, "target": target})
    return out
```

- [ ] **Step 4: Run — verify PASS** (`python -m pytest tests/backend/sensor_status.test.py -v`, 3 passed).

- [ ] **Step 5: Commit**
```bash
git add app/backend/services/ai_prompts.py tests/backend/sensor_status.test.py
git commit -m "feat(explain): build_sensor_status pure helper (C/target/status)"
```

---

## Task 2: Backend — attach `sensor_status` to unified-health

**Files:** Modify `app/backend/modules/ml/router.py`

- [ ] **Step 1: Locate the unified-health response dict** (the dict containing `"unified_health_score"`, `"is_anomaly"`, sensor readings). Confirm the sensor keys present on it:

Run: `grep -nE "air_temperature|process_temperature|rotational_speed|torque|tool_wear|machine_name|machine_type|\"sensor_status\"" app/backend/modules/ml/router.py`

- [ ] **Step 2: Import the helper** near the top of `router.py`:
```python
from services.ai_prompts import build_sensor_status
```

- [ ] **Step 3: Attach `sensor_status`** right before the unified-health `response` dict is returned. Use the sensor readings already on the response/prediction and the machine type/name. Example (adapt the source variables to the actual ones in scope — readings may be on `prediction` or `response`):
```python
        readings = {
            "air_temperature": response.get("air_temperature"),
            "process_temperature": response.get("process_temperature"),
            "rotational_speed": response.get("rotational_speed"),
            "torque": response.get("torque"),
            "tool_wear": response.get("tool_wear"),
        }
        response["sensor_status"] = build_sensor_status(
            response.get("machine_type") or "",
            response.get("machine_name") or "",
            readings,
        )
```
If `machine_type` is not on the response, fetch it the same way `chat_context.get_ml_snapshot` does (`select(Machines.type).where(Machines.id == machine_id)`), or pass `""` (the `_default` category still yields valid statuses).

- [ ] **Step 4: Smoke-verify** — start backend, call unified-health for a known machine, confirm the JSON now contains a `sensor_status` array with `{key,label,value,unit,status,target}`.

Run: `curl -s -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/ml/unified-health/<machine_id>" | python -c "import sys,json;print(json.load(sys.stdin).get('sensor_status'))"`
Expected: a non-empty list (or `[]` if no telemetry) — not an error.

- [ ] **Step 5: Commit**
```bash
git add app/backend/modules/ml/router.py
git commit -m "feat(explain): expose sensor_status on unified-health"
```

---

## Task 3: Backend — `POST /api/v1/why/explain` (cached LLM + fallback)

**Files:** Create `app/backend/modules/shared/routes/why.py` · Test `tests/backend/why_explain.test.py`

- [ ] **Step 1: Write the failing test** — `tests/backend/why_explain.test.py`:

```python
import modules.shared.routes.why as why


def test_make_explanation_uses_llm_then_caches():
    why._CACHE.clear()
    calls = {"n": 0}

    def fake_llm(reasons):
        calls["n"] += 1
        return "Explication simple."

    r1 = why.make_explanation(["trop chaud", "usure élevée"], llm_call=fake_llm)
    assert r1["source"] == "llm" and r1["text"] == "Explication simple."
    r2 = why.make_explanation(["trop chaud", "usure élevée"], llm_call=fake_llm)
    assert r2["source"] == "cache"
    assert calls["n"] == 1


def test_make_explanation_falls_back_to_joined_reasons():
    why._CACHE.clear()

    def boom(reasons):
        raise RuntimeError("down")

    r = why.make_explanation(["trop chaud", "usure élevée"], llm_call=boom)
    assert r["source"] == "fallback"
    assert "trop chaud" in r["text"] and "usure élevée" in r["text"]


def test_empty_reasons_returns_safe_text():
    why._CACHE.clear()
    r = why.make_explanation([], llm_call=lambda x: "")
    assert r["text"].strip()
```

- [ ] **Step 2: Run — verify FAIL** (`python -m pytest tests/backend/why_explain.test.py -v` → ModuleNotFound / attr error).

- [ ] **Step 3: Implement** — `app/backend/modules/shared/routes/why.py`:

```python
"""Plain-language 'Why?' explanation endpoint. Cached LLM, never raises."""
import hashlib
import json
import logging
from typing import Callable, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from core.groq_client import get_groq_client
from models.utilisateurs import Utilisateurs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/why", tags=["why"])

_CACHE: dict = {}


def _key(reasons: List[str]) -> str:
    blob = json.dumps(reasons, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _llm(reasons: List[str]) -> str:
    prompt = (
        "Reformule ces points en UN paragraphe court, en français simple, "
        "pour un opérateur non technique. Aucun terme technique, pas de chiffres "
        "de modèle, pas de liste.\nPoints: " + " ; ".join(reasons)
    )
    resp = get_groq_client().chat(messages=[{"role": "user", "content": prompt}])
    return resp["choices"][0]["message"]["content"]


def make_explanation(reasons: List[str], *, llm_call: Callable[[List[str]], str]) -> dict:
    """Cache-first plain-language phrasing. Never raises."""
    safe = [r for r in (reasons or []) if r and r.strip()]
    if not safe:
        return {"text": "Aucune raison particulière à signaler.", "source": "fallback"}
    key = _key(safe)
    if key in _CACHE:
        return {"text": _CACHE[key], "source": "cache"}
    try:
        text = llm_call(safe)
        if not text or not text.strip():
            raise ValueError("empty")
        _CACHE[key] = text
        return {"text": text, "source": "llm"}
    except Exception:
        return {"text": ". ".join(safe) + ".", "source": "fallback"}


class WhyExplainRequest(BaseModel):
    reasons: List[str]


class WhyExplainResponse(BaseModel):
    text: str
    source: str


@router.post("/explain", response_model=WhyExplainResponse)
async def explain(
    body: WhyExplainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    return WhyExplainResponse(**make_explanation(body.reasons, llm_call=_llm))
```

- [ ] **Step 4: Run — verify PASS** (`python -m pytest tests/backend/why_explain.test.py -v`, 3 passed).

- [ ] **Step 5: Import-check the route**
Run: `cd app/backend && python -c "import sys;sys.path.insert(0,'.');import modules.shared.routes.why as w;print([r.path for r in w.router.routes])"`
Expected: `['/api/v1/why/explain']`.

- [ ] **Step 6: Commit**
```bash
git add app/backend/modules/shared/routes/why.py tests/backend/why_explain.test.py
git commit -m "feat(explain): POST /api/v1/why/explain (cached LLM, fallback to reasons)"
```

---

## Task 4: Backend — add `facts` to the briefing response

**Files:** Modify `app/backend/modules/shared/routes/dashboard.py`

- [ ] **Step 1: Add `facts` to the response model + return** in `dashboard.py`:
Change `BriefingResponse` to include facts, and return them from `get_briefing`:
```python
class BriefingResponse(BaseModel):
    text: str
    generated_at: str
    source: str
    facts: dict = {}
```
In `get_briefing`, after `facts = await _gather_facts(...)` and `result = make_briefing(...)`, return:
```python
    return BriefingResponse(**result, facts=facts)
```

- [ ] **Step 2: Verify briefing logic tests still pass** (facts field is additive; `make_briefing` unchanged):
Run: `python -m pytest tests/backend/dashboard_briefing.test.py -v`
Expected: 8 passed.

- [ ] **Step 3: Commit**
```bash
git add app/backend/modules/shared/routes/dashboard.py
git commit -m "feat(explain): include facts in briefing response for Why drawer"
```

---

## Task 5: Frontend — contract + plain-language helpers (pure)

**Files:** Create `app/frontend/src/modules/shared/explain/whyTypes.ts`, `plainLanguage.ts`, `plainLanguage.test.ts`

- [ ] **Step 1: Write the failing test** — `plainLanguage.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { sensorLabel, failureLabel, kToC, confidenceWords, NO_JARGON } from './plainLanguage';

describe('plainLanguage', () => {
  it('maps sensor keys to plain French', () => {
    expect(sensorLabel('process_temperature')).toBe('température du procédé');
    expect(sensorLabel('tool_wear')).toBe("usure de l'outil");
  });
  it('maps failure codes to plain words', () => {
    expect(failureLabel('TWF')).toBe("usure de l'outil");
    expect(failureLabel('HDF')).toBe('surchauffe');
  });
  it('converts Kelvin to Celsius rounded', () => {
    expect(kToC(318.15)).toBe(45);
  });
  it('turns model agreement into words (low conflict = high confidence)', () => {
    expect(confidenceWords(0.1).level).toBe('Élevée');
    expect(confidenceWords(0.5).level).toBe('Moyenne');
    expect(confidenceWords(0.9).level).toBe('Faible');
  });
  it('NO_JARGON matches banned terms', () => {
    expect(NO_JARGON.test('this uses SHAP')).toBe(true);
    expect(NO_JARGON.test('valeur en Kelvin')).toBe(true);
    expect(NO_JARGON.test('trop chaud')).toBe(false);
  });
});
```

- [ ] **Step 2: Run — verify FAIL** (`cd app/frontend && npx vitest run src/modules/shared/explain/plainLanguage`).

- [ ] **Step 3: Implement** — `whyTypes.ts`:
```ts
export type WhyTone = 'critical' | 'warning' | 'normal' | 'info';
export interface WhyReason { label: string; detail?: string; tone?: WhyTone }
export interface WhyConfidence { level: 'Faible' | 'Moyenne' | 'Élevée'; note: string }
export interface WhyPayload {
  title: string;
  summary: string;
  reasons: WhyReason[];
  confidence?: WhyConfidence;
  counterfactual?: WhyReason[];
  source: string;
  llmContext?: Record<string, unknown>;
}
```
`plainLanguage.ts`:
```ts
import type { WhyConfidence } from './whyTypes';

const SENSOR: Record<string, string> = {
  air_temperature: "température de l'air",
  process_temperature: 'température du procédé',
  rotational_speed: 'vitesse de rotation',
  torque: 'couple',
  tool_wear: "usure de l'outil",
};
const FAILURE: Record<string, string> = {
  TWF: "usure de l'outil",
  HDF: 'surchauffe',
  PWF: 'fluctuation de courant',
  OSF: 'surcharge',
  RNF: 'défaillance aléatoire',
};

export function sensorLabel(key: string): string {
  return SENSOR[key] ?? key.replace(/_/g, ' ');
}
export function failureLabel(code: string): string {
  return FAILURE[code] ?? code;
}
export function kToC(k: number): number {
  return Math.round((k - 273.15) * 10) / 10;
}
export function confidenceWords(conflictK: number): WhyConfidence {
  if (conflictK < 0.3) return { level: 'Élevée', note: 'toutes les vérifications sont d’accord' };
  if (conflictK < 0.7) return { level: 'Moyenne', note: 'la plupart des vérifications concordent' };
  return { level: 'Faible', note: 'les vérifications ne sont pas d’accord' };
}
// Banned ML jargon — producers' output must never match this.
export const NO_JARGON = /\b(SHAP|ensemble|DST|RUL|Kelvin|conflict|TWF|HDF|PWF|OSF|RNF)\b/i;
```

- [ ] **Step 4: Run — verify PASS** (5 tests).

- [ ] **Step 5: Commit**
```bash
git add app/frontend/src/modules/shared/explain/whyTypes.ts app/frontend/src/modules/shared/explain/plainLanguage.ts app/frontend/src/modules/shared/explain/plainLanguage.test.ts
git commit -m "feat(explain): Why contract + plain-language helpers (pure)"
```

---

## Task 6: Frontend — health + anomaly producers (pure)

**Files:** Create `producers/buildHealthWhy.ts` (+test), `producers/buildAnomalyWhy.ts` (+test)

- [ ] **Step 1: Write the failing tests** — `producers/buildHealthWhy.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { buildHealthWhy, UnifiedHealthLike } from './buildHealthWhy';
import { NO_JARGON } from '../plainLanguage';

const health: UnifiedHealthLike = {
  dst_verdict: 'Critical',
  conflict_factor_K: 0.1,
  is_anomaly: true,
  sensor_status: [
    { key: 'process_temperature', label: 'Température procédé', value: 45, unit: '°C', status: 'CRITIQUE', target: 35 },
    { key: 'torque', label: 'Couple', value: 10, unit: 'Nm', status: 'NORMAL', target: 18 },
  ],
  explanations: [{ factor: 'process_temperature', impact: 0.31, intensity: 'high' }],
};

describe('buildHealthWhy', () => {
  it('produces a plain payload with confidence and counterfactual', () => {
    const p = buildHealthWhy(health);
    expect(p.title).toBeTruthy();
    expect(p.confidence?.level).toBe('Élevée');
    expect(p.counterfactual && p.counterfactual.length).toBeGreaterThan(0);
  });
  it('counterfactual targets the out-of-range sensor', () => {
    const p = buildHealthWhy(health);
    const cf = p.counterfactual!.map((r) => r.label).join(' ');
    expect(cf.toLowerCase()).toContain('procédé');
  });
  it('never leaks ML jargon', () => {
    const p = buildHealthWhy(health);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('degrades to a minimal payload with no data', () => {
    const p = buildHealthWhy({});
    expect(p.title).toBeTruthy();
    expect(p.reasons).toEqual([]);
  });
});
```
`producers/buildAnomalyWhy.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { buildAnomalyWhy } from './buildAnomalyWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildAnomalyWhy', () => {
  it('lists abnormal sensors in plain words, no jargon', () => {
    const p = buildAnomalyWhy({
      is_anomaly: true,
      sensor_status: [
        { key: 'process_temperature', label: 'Température procédé', value: 45, unit: '°C', status: 'CRITIQUE', target: 35 },
        { key: 'torque', label: 'Couple', value: 10, unit: 'Nm', status: 'NORMAL', target: 18 },
      ],
    });
    expect(p.reasons.length).toBe(1);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('reassures when nothing is abnormal', () => {
    const p = buildAnomalyWhy({ is_anomaly: false, sensor_status: [] });
    expect(p.summary).toBeTruthy();
    expect(p.reasons).toEqual([]);
  });
});
```

- [ ] **Step 2: Run — verify FAIL.**

- [ ] **Step 3: Implement** — `producers/buildHealthWhy.ts`:
```ts
import type { WhyPayload, WhyReason, WhyTone } from '../whyTypes';
import { confidenceWords } from '../plainLanguage';

export interface SensorStatus {
  key: string; label: string; value: number; unit: string;
  status: 'NORMAL' | 'ATTENTION' | 'CRITIQUE'; target: number | null;
}
export interface UnifiedHealthLike {
  dst_verdict?: string;
  conflict_factor_K?: number;
  is_anomaly?: boolean;
  sensor_status?: SensorStatus[];
  explanations?: { factor: string; impact: number; intensity: string }[];
}

const VERDICT_TITLE: Record<string, string> = {
  Critical: 'Risque de panne élevé',
  Degrading: 'État qui se dégrade',
  Healthy: 'Machine en bon état',
};
const toneOf = (s: string): WhyTone =>
  s === 'CRITIQUE' ? 'critical' : s === 'ATTENTION' ? 'warning' : 'normal';

export function buildHealthWhy(health: UnifiedHealthLike): WhyPayload {
  const sensors = health.sensor_status ?? [];
  const abnormal = sensors.filter((s) => s.status !== 'NORMAL');
  const title = VERDICT_TITLE[health.dst_verdict ?? ''] ?? 'État de la machine';

  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} ${s.value > (s.target ?? Infinity) ? 'trop élevé' : 'hors de la plage sûre'}`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: toneOf(s.status),
  }));

  const counterfactual: WhyReason[] = abnormal
    .filter((s) => s.target != null)
    .map((s) => ({
      label: `Ramener ${s.label.toLowerCase()} sous ${s.target} ${s.unit}`,
      detail: `actuellement ${s.value} ${s.unit}`,
      tone: 'normal',
    }));

  const confidence = health.conflict_factor_K != null
    ? confidenceWords(health.conflict_factor_K) : undefined;

  const summary = abnormal.length
    ? `Principale raison : ${abnormal[0].label.toLowerCase()} hors de la plage sûre.`
    : 'Aucun signal préoccupant pour le moment.';

  return {
    title, summary, reasons,
    confidence,
    counterfactual: counterfactual.length ? counterfactual : undefined,
    source: 'Basé sur les dernières mesures des capteurs et l’historique de pannes.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
```
`producers/buildAnomalyWhy.ts`:
```ts
import type { WhyPayload, WhyReason } from '../whyTypes';
import type { UnifiedHealthLike } from './buildHealthWhy';

export function buildAnomalyWhy(health: UnifiedHealthLike): WhyPayload {
  const abnormal = (health.sensor_status ?? []).filter((s) => s.status !== 'NORMAL');
  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} se comporte de façon inhabituelle`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: s.status === 'CRITIQUE' ? 'critical' : 'warning',
  }));
  return {
    title: health.is_anomaly ? 'Comportement inhabituel détecté' : 'Comportement normal',
    summary: reasons.length
      ? 'Un ou plusieurs capteurs s’écartent de leur fonctionnement habituel.'
      : 'Les capteurs fonctionnent comme d’habitude.',
    reasons,
    source: 'Comparé au fonctionnement habituel de ce type de machine.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
```

- [ ] **Step 4: Run — verify PASS** (both test files).

- [ ] **Step 5: Commit**
```bash
git add app/frontend/src/modules/shared/explain/producers/buildHealthWhy.ts app/frontend/src/modules/shared/explain/producers/buildHealthWhy.test.ts app/frontend/src/modules/shared/explain/producers/buildAnomalyWhy.ts app/frontend/src/modules/shared/explain/producers/buildAnomalyWhy.test.ts
git commit -m "feat(explain): health + anomaly Why producers (pure, plain language)"
```

---

## Task 7: Frontend — NBA + briefing producers (pure)

**Files:** Create `producers/buildNbaWhy.ts` (+test), `producers/buildBriefingWhy.ts` (+test)

- [ ] **Step 1: Write the failing tests** — `producers/buildNbaWhy.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { buildNbaWhy } from './buildNbaWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildNbaWhy', () => {
  it('explains a critical action in plain words', () => {
    const p = buildNbaWhy({ key: 'alert-7', label: 'Alerte critique — machine 7', severity: 'critical', href: '/machines/7', score: 100 });
    expect(p.title).toBeTruthy();
    expect(p.reasons.length).toBeGreaterThan(0);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
});
```
`producers/buildBriefingWhy.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { buildBriefingWhy } from './buildBriefingWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildBriefingWhy', () => {
  it('turns facts into plain reasons', () => {
    const p = buildBriefingWhy({ urgent_wos: 2, overdue_pms: 1, degraded_machines: ['P-07'], active_alerts: 0 });
    const labels = p.reasons.map((r) => r.label).join(' ');
    expect(labels).toMatch(/urgent/i);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('reassures with no facts', () => {
    const p = buildBriefingWhy({ urgent_wos: 0, overdue_pms: 0, degraded_machines: [], active_alerts: 0 });
    expect(p.reasons).toEqual([]);
  });
});
```

- [ ] **Step 2: Run — verify FAIL.**

- [ ] **Step 3: Implement** — `producers/buildNbaWhy.ts`:
```ts
import type { WhyPayload } from '../whyTypes';
import type { RankedAction } from '../../dashboard/rankNextBestActions';

const WHY: Record<string, string> = {
  critical: 'Risque immédiat — à traiter en priorité.',
  high: 'Urgent — à planifier aujourd’hui.',
  medium: 'À prévoir bientôt pour éviter un arrêt.',
};

export function buildNbaWhy(action: RankedAction): WhyPayload {
  return {
    title: 'Pourquoi cette action ?',
    summary: WHY[action.severity] ?? 'Action recommandée.',
    reasons: [
      { label: action.label, tone: action.severity === 'critical' ? 'critical' : action.severity === 'high' ? 'warning' : 'normal' },
      { label: WHY[action.severity] ?? 'Recommandé', tone: 'info' },
    ],
    source: 'Classé par urgence et impact sur la production.',
    llmContext: { reasons: [action.label, WHY[action.severity] ?? ''] },
  };
}
```
`producers/buildBriefingWhy.ts`:
```ts
import type { WhyPayload, WhyReason } from '../whyTypes';

export interface BriefingFacts {
  urgent_wos: number;
  overdue_pms: number;
  degraded_machines: string[];
  active_alerts: number;
}

export function buildBriefingWhy(facts: BriefingFacts): WhyPayload {
  const reasons: WhyReason[] = [];
  if (facts.urgent_wos) reasons.push({ label: `${facts.urgent_wos} intervention(s) urgente(s)`, tone: 'critical' });
  if (facts.degraded_machines?.length) reasons.push({ label: `Machines à surveiller : ${facts.degraded_machines.slice(0, 3).join(', ')}`, tone: 'warning' });
  if (facts.overdue_pms) reasons.push({ label: `${facts.overdue_pms} entretien(s) en retard`, tone: 'warning' });
  if (facts.active_alerts) reasons.push({ label: `${facts.active_alerts} alerte(s) en cours`, tone: 'warning' });
  return {
    title: 'Pourquoi ce résumé ?',
    summary: reasons.length ? 'Voici ce qui demande votre attention aujourd’hui.' : 'Rien d’urgent aujourd’hui.',
    reasons,
    source: 'Résumé des interventions, entretiens et alertes du jour.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
```

- [ ] **Step 4: Run — verify PASS** (both files).

- [ ] **Step 5: Commit**
```bash
git add app/frontend/src/modules/shared/explain/producers/buildNbaWhy.ts app/frontend/src/modules/shared/explain/producers/buildNbaWhy.test.ts app/frontend/src/modules/shared/explain/producers/buildBriefingWhy.ts app/frontend/src/modules/shared/explain/producers/buildBriefingWhy.test.ts
git commit -m "feat(explain): NBA + briefing Why producers (pure, plain language)"
```

---

## Task 8: Frontend — WhyButton + WhyDrawer components

**Files:** Create `WhyButton.tsx`, `WhyDrawer.tsx`

- [ ] **Step 1: `WhyDrawer.tsx`** (thin; renders any payload + optional LLM call):
```tsx
import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { client } from '@/lib/api';
import type { WhyPayload, WhyTone } from './whyTypes';

const TONE: Record<WhyTone, string> = {
  critical: 'border-l-red-500', warning: 'border-l-amber-500',
  normal: 'border-l-blue-500', info: 'border-l-slate-500',
};

export function WhyDrawer({ open, onOpenChange, payload }:
  { open: boolean; onOpenChange: (o: boolean) => void; payload: WhyPayload | null }) {
  const [plain, setPlain] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!payload) return null;

  const explain = async () => {
    setBusy(true);
    try {
      const reasons = (payload.llmContext?.reasons as string[]) ?? payload.reasons.map((r) => r.label);
      const res: any = await (client.apiCall as any).invoke({
        url: '/api/v1/why/explain', method: 'POST', data: { reasons },
      });
      const data = res?.data ?? res;
      setPlain(data?.text ?? null);
    } catch {
      toast.error('Explication indisponible pour le moment.');
    } finally { setBusy(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="bg-slate-900 border-slate-700 text-slate-100 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-white">{payload.title}</SheetTitle>
          <SheetDescription className="text-blue-300">{payload.summary}</SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-2">
          {payload.reasons.map((r, i) => (
            <div key={i} className={`bg-slate-800 border border-slate-700 border-l-[3px] ${TONE[r.tone ?? 'info']} rounded-md px-3 py-2`}>
              <p className="text-sm text-slate-100">{r.label}</p>
              {r.detail && <p className="text-xs text-blue-300">{r.detail}</p>}
            </div>
          ))}
        </div>

        {payload.confidence && (
          <div className="mt-4 text-sm text-slate-200">
            Confiance : <span className="font-medium">{payload.confidence.level}</span>
            <span className="text-blue-300"> — {payload.confidence.note}</span>
          </div>
        )}

        {payload.counterfactual && (
          <div className="mt-4">
            <p className="text-xs font-medium text-emerald-400 mb-2">Pour revenir à la normale</p>
            <div className="space-y-2">
              {payload.counterfactual.map((r, i) => (
                <div key={i} className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100">{r.label}</div>
              ))}
            </div>
          </div>
        )}

        <button onClick={explain} disabled={busy}
          className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-blue-300 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 hover:bg-slate-700/60 disabled:opacity-50">
          <Sparkles className="h-4 w-4" /> {busy ? 'Explication…' : 'Expliquer simplement'}
        </button>
        {plain && <p className="mt-3 text-sm text-blue-100 leading-relaxed">{plain}</p>}

        <p className="mt-5 pt-3 border-t border-slate-800 text-[11px] text-slate-500">{payload.source}</p>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: `WhyButton.tsx`**:
```tsx
import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { WhyDrawer } from './WhyDrawer';
import type { WhyPayload } from './whyTypes';

export function WhyButton({ payload, className = '' }: { payload: WhyPayload; className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
        className={`inline-flex items-center gap-1 text-[11px] text-blue-300 hover:text-blue-200 ${className}`}>
        <HelpCircle className="h-3.5 w-3.5" /> Pourquoi ?
      </button>
      <WhyDrawer open={open} onOpenChange={setOpen} payload={payload} />
    </>
  );
}
```

- [ ] **Step 3: Type-check**
Run: `cd app/frontend && npx tsc --noEmit 2>&1 | grep "shared/explain" || echo clean`
Expected: `clean`.

- [ ] **Step 4: Commit**
```bash
git add app/frontend/src/modules/shared/explain/WhyButton.tsx app/frontend/src/modules/shared/explain/WhyDrawer.tsx
git commit -m "feat(explain): reusable WhyButton + WhyDrawer (offline + optional LLM)"
```

---

## Task 9: Frontend — wire the 4 surfaces

**Files:** Modify `NextBestActions.tsx`, `BriefingBar.tsx`, `MLIntelligenceTab.tsx`

- [ ] **Step 1: NBA rows** — in `app/frontend/src/modules/shared/dashboard/NextBestActions.tsx`, import and add a `WhyButton` to each action row:
```tsx
import { WhyButton } from '@/modules/shared/explain/WhyButton';
import { buildNbaWhy } from '@/modules/shared/explain/producers/buildNbaWhy';
```
Inside the row (after the label span, before `ChevronRight`):
```tsx
<WhyButton payload={buildNbaWhy(a)} className="mr-1" />
```

- [ ] **Step 2: Briefing** — in `app/frontend/src/modules/shared/dashboard/BriefingBar.tsx`, capture `facts` from the response and render a `WhyButton`:
```tsx
import { WhyButton } from '@/modules/shared/explain/WhyButton';
import { buildBriefingWhy } from '@/modules/shared/explain/producers/buildBriefingWhy';
```
Add `const [facts, setFacts] = useState<any>(null);`, set it from `data?.facts` alongside `setText`, and after the briefing `<p>` render:
```tsx
{facts && <div className="mt-2"><WhyButton payload={buildBriefingWhy(facts)} /></div>}
```

- [ ] **Step 3: Health + anomaly** — in `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx`, locate the health verdict block and the anomaly ("Behavioral Anomaly") card. Confirm the unified-health object variable name first:
Run: `grep -nE "unified|health|sensor_status|anomaly|dst_verdict|Behavioral|Anomal" app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx | head -30`
Then import and add a `WhyButton` to each:
```tsx
import { WhyButton } from '@/modules/shared/explain/WhyButton';
import { buildHealthWhy } from '@/modules/shared/explain/producers/buildHealthWhy';
import { buildAnomalyWhy } from '@/modules/shared/explain/producers/buildAnomalyWhy';
```
Health verdict area: `<WhyButton payload={buildHealthWhy(<healthObj>)} />`
Anomaly card: `<WhyButton payload={buildAnomalyWhy(<healthObj>)} />`
(`<healthObj>` = the unified-health response object already in scope; it now carries `sensor_status`, `dst_verdict`, `conflict_factor_K`, `is_anomaly`, `explanations`.)

- [ ] **Step 4: Type-check + lint**
Run: `cd app/frontend && npx tsc --noEmit 2>&1 | grep -E "explain|NextBestActions|BriefingBar|MLIntelligenceTab" || echo clean`
Expected: `clean`.

- [ ] **Step 5: Manual smoke** — open the dashboard (NBA + briefing "Pourquoi ?" drawers) and a machine ML tab (health + anomaly "Pourquoi ?"). Confirm: structured plain-language reasons show with no network; "Expliquer simplement" returns a paragraph (or a toast if backend/LLM down); zero ML jargon visible.

- [ ] **Step 6: Commit**
```bash
git add app/frontend/src/modules/shared/dashboard/NextBestActions.tsx app/frontend/src/modules/shared/dashboard/BriefingBar.tsx app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx
git commit -m "feat(explain): wire Why? into NBA, briefing, health, anomaly"
```

---

## Task 10: Full verification

- [ ] **Step 1: Backend tests**
Run: `python -m pytest tests/backend/sensor_status.test.py tests/backend/why_explain.test.py tests/backend/dashboard_briefing.test.py -v`
Expected: all PASS.

- [ ] **Step 2: Frontend tests**
Run: `cd app/frontend && npx vitest run`
Expected: existing suite + plainLanguage, buildHealthWhy, buildAnomalyWhy, buildNbaWhy, buildBriefingWhy all PASS; **no banned-jargon test fails**.

- [ ] **Step 3: Type-check whole frontend**
Run: `cd app/frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"`
Expected: `0`.

- [ ] **Step 4: Commit any cleanup**
```bash
git commit -am "chore(explain): C10 Why-everywhere verification pass" || echo "nothing to commit"
```

---

## Self-Review (completed)
- **Spec coverage:** contract+plain layer → Task 5; sensor_status backend → Tasks 1-2; /why/explain hybrid+fallback → Task 3; briefing facts → Task 4; 4 producers → Tasks 6-7; drawer+button → Task 8; wiring 4 surfaces → Task 9; tests → Task 10. Plain-language rule enforced by `NO_JARGON` assertions in every producer test. Out-of-scope items (technical toggle, role-aware, counterfactual elsewhere) correctly excluded.
- **Placeholder scan:** none — full code per step; the two `<healthObj>`/source-variable notes are explicit verify-then-bind instructions, not gaps.
- **Type consistency:** `WhyPayload`/`WhyReason`/`WhyConfidence` defined Task 5, consumed unchanged Tasks 6-9; `SensorStatus`/`UnifiedHealthLike` defined in `buildHealthWhy` and reused by `buildAnomalyWhy`; `RankedAction` imported from B1 unchanged (buildNbaWhy derives reasons from existing fields — B1 stays green); backend `make_explanation`/`_CACHE`/`build_sensor_status` names consistent across tasks.
- **Simplification vs spec:** spec floated extending `RankedAction` with a `reasons` breakdown; plan derives NBA reasons from existing `severity`/`label` instead — keeps B1 untouched. Noted intentionally.
```
