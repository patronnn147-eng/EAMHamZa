# B1 Dashboard Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the four existing dashboards in place with an AI daily briefing, a next-best-action feed, loading skeletons, drill-through links, persisted filters, and delta badges — via shared reusable components.

**Architecture:** A new auto-discovered backend router `GET /api/v1/dashboard/briefing` builds a role-scoped facts snapshot (reusing the chat-bridge pattern), hashes the material facts, serves from an in-memory daily cache, calls Groq only on a cache miss, and falls back to a rule-based template if the LLM is down (never raises). The frontend adds pure scoring/serialization functions (unit-tested with vitest) plus thin presentational components mounted in all four dashboards.

**Tech Stack:** FastAPI + SQLAlchemy async, Groq client (`core.groq_client`), pytest (`tests/backend/*.test.py`); React 19 + TypeScript + Tailwind, vitest (pure-function tests — repo has no React Testing Library, so components are verified manually and all logic is extracted into tested pure functions).

---

## Conventions discovered (follow these exactly)

- Backend routers in `app/backend/modules/**` exposing a module-level `router: APIRouter` are **auto-included** by `include_routers_from_package(app, "modules")` in `app/backend/main.py`. No manual registration needed (but we also add it to `modules/shared/routes/__init__.py` for clarity).
- Auth dependency: `from core.auth import get_current_user`; role = `current_user.role.value`, id = `current_user.id`.
- DB dependency: `from core.database import get_db` → `AsyncSession`.
- LLM: `from core.groq_client import get_groq_client`; `get_groq_client().chat(messages=[{role, content}, ...])` returns `{"choices":[{"message":{"content": str}}]}`.
- Backend tests live in `tests/backend/<name>.test.py`, run with `pytest`. `conftest.py` puts `app/backend` on `sys.path`, so import as `from modules...` / `from core...`.
- Frontend pure-logic tests live next to source as `*.test.ts`, run with `pnpm test` (`vitest run`). Pattern reference: `app/frontend/src/components/inventory/partitionRecommendedParts.test.ts`.
- Frontend custom REST call: `import { client } from '@/lib/api'` then `await (client.apiCall as any).invoke({ url, method: 'GET' })`.
- App theme: `bg-slate-800` cards, `border-slate-700`, white headings, `text-blue-300/400`, emerald/orange/red status. Icons from `lucide-react`. Links via `react-router-dom` `Link`. Toasts via `sonner` (`toast`).

---

## File Structure

**Backend (create):**
- `app/backend/modules/shared/services/dashboard_briefing.py` — facts builder, hashing, template, in-memory cache, pure orchestrator.
- `app/backend/modules/shared/routes/dashboard.py` — `GET /api/v1/dashboard/briefing` endpoint.
- `tests/backend/dashboard_briefing.test.py` — unit tests for the pure logic.

**Backend (modify):**
- `app/backend/modules/shared/routes/__init__.py` — add `dashboard` import.

**Frontend (create) under `app/frontend/src/modules/shared/dashboard/`:**
- `rankNextBestActions.ts` + `rankNextBestActions.test.ts` — pure scoring.
- `computeDelta.ts` + `computeDelta.test.ts` — pure delta calc.
- `dashboardFilters.ts` + `dashboardFilters.test.ts` — pure load/save/serialize.
- `BriefingBar.tsx` — AI briefing strip (thin).
- `NextBestActions.tsx` — ranked feed (thin; uses `rankNextBestActions`).
- `DashboardSkeleton.tsx` — skeleton blocks.
- `DeltaBadge.tsx` — badge (thin; uses `computeDelta`).
- `DashboardFilters.tsx` — filter bar (thin; uses `dashboardFilters`).

**Frontend (modify):**
- `app/frontend/src/modules/shared/Dashboard.tsx` — wire all components in.
- `app/frontend/src/modules/cheftech/CheftechDashboard.tsx`
- `app/frontend/src/modules/chetop/ChetopDashboard.tsx`
- `app/frontend/src/modules/technicien/TechnicianDashboard.tsx`

---

## Task 1: Backend — briefing facts + hash + template + orchestrator (pure logic)

**Files:**
- Create: `app/backend/modules/shared/services/dashboard_briefing.py`
- Test: `tests/backend/dashboard_briefing.test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/dashboard_briefing.test.py`:

```python
from modules.shared.services.dashboard_briefing import (
    compute_facts, facts_hash, render_template, make_briefing, _CACHE,
)


def _facts(urgent=2, overdue=1, degraded=("P-07",)):
    return compute_facts(
        urgent_wos=urgent,
        pending_wos=3,
        completed_week=5,
        overdue_pms=overdue,
        degraded_machines=list(degraded),
        active_alerts=1,
    )


def test_compute_facts_shape():
    f = _facts()
    assert f["urgent_wos"] == 2
    assert f["overdue_pms"] == 1
    assert f["degraded_machines"] == ["P-07"]


def test_hash_stable_and_sensitive():
    assert facts_hash(_facts()) == facts_hash(_facts())
    assert facts_hash(_facts(urgent=2)) != facts_hash(_facts(urgent=9))


def test_template_is_nonempty_and_mentions_counts():
    text = render_template(_facts())
    assert isinstance(text, str) and text.strip()
    assert "2" in text  # urgent count surfaces


def test_make_briefing_uses_llm_then_caches():
    _CACHE.clear()
    calls = {"n": 0}

    def fake_llm(facts):
        calls["n"] += 1
        return "Generated briefing."

    r1 = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                       today="2026-06-18", llm_call=fake_llm)
    assert r1["text"] == "Generated briefing."
    assert r1["source"] == "llm"

    r2 = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                       today="2026-06-18", llm_call=fake_llm)
    assert r2["source"] == "cache"
    assert calls["n"] == 1  # second call served from cache


def test_make_briefing_falls_back_to_template_and_does_not_cache():
    _CACHE.clear()

    def boom_llm(facts):
        raise RuntimeError("llm down")

    r = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                      today="2026-06-18", llm_call=boom_llm)
    assert r["source"] == "template"
    assert r["text"].strip()
    # template result is NOT cached → next call retries the LLM
    assert len(_CACHE) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/dashboard_briefing.test.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'modules.shared.services.dashboard_briefing'`

- [ ] **Step 3: Write minimal implementation**

Create `app/backend/modules/shared/services/dashboard_briefing.py`:

```python
"""
Dashboard AI briefing — role-scoped facts, daily in-memory cache, LLM phrasing
with a rule-based template fallback. Pure orchestration lives here; the route
wires DB + Groq into it.

Mirrors the platform safety property: never raises. LLM down -> template.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Callable, Dict, List

# In-memory cache: key -> {"text", "generated_at"}. Resets on restart (fine for
# a daily briefing). Matches the in-memory cache convention used elsewhere.
_CACHE: Dict[str, Dict[str, str]] = {}


def compute_facts(
    *,
    urgent_wos: int,
    pending_wos: int,
    completed_week: int,
    overdue_pms: int,
    degraded_machines: List[str],
    active_alerts: int,
) -> Dict:
    """Material facts that drive the briefing. Sync + pure → unit-testable."""
    return {
        "urgent_wos": int(urgent_wos),
        "pending_wos": int(pending_wos),
        "completed_week": int(completed_week),
        "overdue_pms": int(overdue_pms),
        "degraded_machines": list(degraded_machines),
        "active_alerts": int(active_alerts),
    }


def facts_hash(facts: Dict) -> str:
    """Stable hash over material facts only (sorted keys)."""
    blob = json.dumps(facts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cache_key(scope: str, scope_id: str, site: str, today: str, h: str) -> str:
    return f"{scope}|{scope_id}|{site}|{today}|{h}"


def render_template(facts: Dict) -> str:
    """Deterministic fallback text. No LLM. Always non-empty."""
    parts = []
    if facts["urgent_wos"]:
        parts.append(f"{facts['urgent_wos']} ordre(s) urgent(s) à traiter.")
    if facts["degraded_machines"]:
        names = ", ".join(facts["degraded_machines"][:3])
        parts.append(f"Machines à surveiller: {names}.")
    if facts["overdue_pms"]:
        parts.append(f"{facts['overdue_pms']} maintenance(s) préventive(s) en retard.")
    if facts["active_alerts"]:
        parts.append(f"{facts['active_alerts']} alerte(s) active(s).")
    if not parts:
        return "Tout est sous contrôle aujourd'hui. Aucune action urgente."
    return " ".join(parts)


def make_briefing(
    facts: Dict,
    *,
    scope: str,
    scope_id: str,
    site: str,
    today: str,
    llm_call: Callable[[Dict], str],
) -> Dict:
    """
    Cache-first orchestration. Returns {"text", "generated_at", "source"}.
    source ∈ {"cache","llm","template"}. Never raises.
    """
    key = cache_key(scope, scope_id, site, today, facts_hash(facts))

    hit = _CACHE.get(key)
    if hit:
        return {"text": hit["text"], "generated_at": hit["generated_at"], "source": "cache"}

    now = datetime.now(timezone.utc).isoformat()
    try:
        text = llm_call(facts)
        if not text or not text.strip():
            raise ValueError("empty LLM text")
        _CACHE[key] = {"text": text, "generated_at": now}
        return {"text": text, "generated_at": now, "source": "llm"}
    except Exception:
        # Do NOT cache the template — next load retries the LLM.
        return {"text": render_template(facts), "generated_at": now, "source": "template"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/dashboard_briefing.test.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/shared/services/dashboard_briefing.py tests/backend/dashboard_briefing.test.py
git commit -m "feat(dashboard): briefing facts, hash, template, cache orchestrator"
```

---

## Task 2: Backend — briefing endpoint (DB facts + Groq wiring)

**Files:**
- Create: `app/backend/modules/shared/routes/dashboard.py`
- Modify: `app/backend/modules/shared/routes/__init__.py`

- [ ] **Step 1: Write the endpoint**

Create `app/backend/modules/shared/routes/dashboard.py`:

```python
"""Dashboard command-center endpoints. Auto-discovered via main.py router scan."""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from core.groq_client import get_groq_client
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.ordres_travail import OrdresTravail

from modules.shared.services.dashboard_briefing import compute_facts, make_briefing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class BriefingResponse(BaseModel):
    text: str
    generated_at: str
    source: str


def _llm_call(facts: dict) -> str:
    """Phrase the facts in one short French paragraph. Raises on any failure."""
    prompt = (
        "Tu es l'assistant maintenance. Rédige UN court paragraphe (2-3 phrases, "
        "ton professionnel, en français) résumant l'état du jour à partir de ces faits. "
        "Pas de liste, pas de markdown.\n"
        f"Faits: {facts}"
    )
    groq = get_groq_client()
    resp = groq.chat(messages=[{"role": "user", "content": prompt}])
    return resp["choices"][0]["message"]["content"]


async def _gather_facts(role: str, user_id, db: AsyncSession) -> dict:
    """Build the role-scoped material facts. Best-effort; missing data → zeros."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    async def _count(stmt) -> int:
        try:
            res = await db.execute(stmt)
            return int(res.scalar_one() or 0)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"[dashboard] count failed: {e}")
            return 0

    base_wo = select(func.count()).select_from(OrdresTravail)
    if role == "TECHNICIEN" and user_id is not None:
        base_wo = base_wo.where(OrdresTravail.technicien_id == user_id)

    urgent = await _count(base_wo.where(
        OrdresTravail.priorite == "URGENTE", OrdresTravail.statut != "TERMINE"))
    pending = await _count(base_wo.where(OrdresTravail.statut == "EN_ATTENTE"))
    completed = await _count(base_wo.where(
        OrdresTravail.statut == "TERMINE", OrdresTravail.created_at >= week_ago))

    overdue = await _count(select(func.count()).select_from(Machines).where(
        Machines.date_prochaine_maintenance < now))

    degraded: List[str] = []
    try:
        res = await db.execute(
            select(Machines.nom).where(Machines.statut == "EN_PANNE").limit(3))
        degraded = [r[0] for r in res.all()]
    except Exception:
        degraded = []

    return compute_facts(
        urgent_wos=urgent, pending_wos=pending, completed_week=completed,
        overdue_pms=overdue, degraded_machines=degraded, active_alerts=0,
    )


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(
    site: str = Query(default="all"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Daily AI briefing. Role-scoped facts, cache-first, LLM on miss,
    template fallback when the LLM is unavailable. Never raises.
    """
    role = current_user.role.value if current_user.role else "TECHNICIEN"
    today = datetime.now(timezone.utc).date().isoformat()

    if role == "TECHNICIEN":
        scope, scope_id = "user", str(current_user.id)
    else:
        scope, scope_id = "role", role

    facts = await _gather_facts(role, current_user.id, db)
    result = make_briefing(
        facts, scope=scope, scope_id=scope_id, site=site,
        today=today, llm_call=_llm_call,
    )
    return BriefingResponse(**result)
```

> NOTE on model/field names: the codebase uses French entity/column names. Before running, confirm the actual class names and columns by grepping: `grep -rn "class Machines\|class OrdresTravail" app/backend/models/`. Adjust `OrdresTravail.technicien_id`, `OrdresTravail.priorite/statut/created_at`, `Machines.date_prochaine_maintenance/statut/nom` to match the real attribute names. The values `"URGENTE"`, `"TERMINE"`, `"EN_ATTENTE"`, `"EN_PANNE"` match those used in `shared/Dashboard.tsx` and `DashboardStatsCards.tsx`.

- [ ] **Step 2: Register in package `__init__`**

Modify `app/backend/modules/shared/routes/__init__.py` — add `dashboard` to the import list:

```python
# modules/shared/routes/__init__.py
from .intervention_workflow import router
from . import (
    planning,
    planning_ordres_travail,
    ordres_travail,
    ordres_intervention,
    machines,
    dashboard,
)
```

- [ ] **Step 3: Verify model/field names, then start the backend and hit the endpoint**

Run: `grep -rn "class Machines\|class OrdresTravail" app/backend/models/`
Fix any mismatched attribute names in `dashboard.py`.

Run: `make up` (or the project's backend start), then with a valid token:
`curl -s -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/dashboard/briefing"`
Expected: JSON `{"text": "...", "generated_at": "...", "source": "llm" | "template"}` (HTTP 200). A second call within the day returns `"source": "cache"`.

- [ ] **Step 4: Commit**

```bash
git add app/backend/modules/shared/routes/dashboard.py app/backend/modules/shared/routes/__init__.py
git commit -m "feat(dashboard): GET /api/v1/dashboard/briefing endpoint"
```

---

## Task 3: Frontend — next-best-action scoring (pure)

**Files:**
- Create: `app/frontend/src/modules/shared/dashboard/rankNextBestActions.ts`
- Test: `app/frontend/src/modules/shared/dashboard/rankNextBestActions.test.ts`

- [ ] **Step 1: Write the failing test**

Create `rankNextBestActions.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { rankNextBestActions, NbaInput } from './rankNextBestActions';

const base: NbaInput = {
  role: 'CHEFTECH',
  userId: 1,
  workOrders: [
    { id: 10, priorite: 'URGENTE', statut: 'EN_ATTENTE', technicien_id: 2 },
    { id: 11, priorite: 'MOYENNE', statut: 'EN_ATTENTE', technicien_id: 1 },
  ],
  overduePMs: [{ machine_id: 5, nom: 'Press P-1' }],
  alerts: [{ type: 'ANOMALY', severity: 'CRITICAL', machine_id: 7 }],
};

describe('rankNextBestActions', () => {
  it('puts a critical alert above an urgent WO above an overdue PM', () => {
    const out = rankNextBestActions(base);
    expect(out.map((a) => a.severity)).toEqual(['critical', 'high', 'medium']);
  });

  it('caps output at 5', () => {
    const many: NbaInput = {
      ...base,
      workOrders: Array.from({ length: 9 }, (_, i) => ({
        id: i, priorite: 'URGENTE', statut: 'EN_ATTENTE', technicien_id: 1,
      })),
    };
    expect(rankNextBestActions(many).length).toBe(5);
  });

  it('for a technician keeps only their own assigned items', () => {
    const out = rankNextBestActions({ ...base, role: 'TECHNICIEN' });
    // urgent WO #10 is assigned to tech 2 → excluded; WO #11 is tech 1 → kept
    const woKeys = out.filter((a) => a.key.startsWith('wo-')).map((a) => a.key);
    expect(woKeys).toEqual(['wo-11']);
  });

  it('builds a drill-through href per action', () => {
    const out = rankNextBestActions(base);
    const alert = out.find((a) => a.severity === 'critical')!;
    expect(alert.href).toContain('/machines/7');
  });

  it('returns empty for empty input', () => {
    expect(rankNextBestActions({ role: 'ADMIN', workOrders: [], overduePMs: [], alerts: [] }))
      .toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/frontend && pnpm test -- rankNextBestActions`
Expected: FAIL — cannot find module `./rankNextBestActions`.

- [ ] **Step 3: Write minimal implementation**

Create `rankNextBestActions.ts`:

```ts
export interface NbaWorkOrder {
  id: number;
  priorite: string;
  statut: string;
  technicien_id?: number | null;
  machine_id?: number | null;
}
export interface NbaPM { machine_id: number; nom: string }
export interface NbaAlert { type: string; severity?: string; machine_id?: number | null }

export interface NbaInput {
  role: string;
  userId?: number;
  workOrders: NbaWorkOrder[];
  overduePMs: NbaPM[];
  alerts: NbaAlert[];
  machineCriticality?: Record<number, number>;
}

export interface RankedAction {
  key: string;
  label: string;
  severity: 'critical' | 'high' | 'medium';
  href: string;
  score: number;
}

const URGENCY = { criticalAlert: 100, urgentWo: 70, overduePm: 40 };

export function rankNextBestActions(input: NbaInput): RankedAction[] {
  const isTech = input.role === 'TECHNICIEN';
  const crit = input.machineCriticality ?? {};
  const impact = (machineId?: number | null) =>
    (machineId != null && crit[machineId]) ? crit[machineId] : 1;

  const actions: RankedAction[] = [];

  for (const a of input.alerts) {
    if ((a.severity ?? '').toUpperCase() !== 'CRITICAL') continue;
    if (isTech) continue; // techs act on their WOs, managers triage alerts
    actions.push({
      key: `alert-${a.machine_id ?? 'x'}`,
      label: `Alerte critique${a.machine_id ? ` — machine ${a.machine_id}` : ''}`,
      severity: 'critical',
      href: a.machine_id != null ? `/machines/${a.machine_id}` : '/machines',
      score: URGENCY.criticalAlert * impact(a.machine_id),
    });
  }

  for (const wo of input.workOrders) {
    if (wo.priorite !== 'URGENTE' || wo.statut === 'TERMINE') continue;
    if (isTech && wo.technicien_id !== input.userId) continue;
    actions.push({
      key: `wo-${wo.id}`,
      label: `Ordre urgent #${wo.id}`,
      severity: 'high',
      href: `/work-orders?id=${wo.id}`,
      score: URGENCY.urgentWo * impact(wo.machine_id),
    });
  }

  for (const pm of input.overduePMs) {
    actions.push({
      key: `pm-${pm.machine_id}`,
      label: `Maintenance en retard — ${pm.nom}`,
      severity: 'medium',
      href: `/planning?machine=${pm.machine_id}`,
      score: URGENCY.overduePm * impact(pm.machine_id),
    });
  }

  return actions.sort((a, b) => b.score - a.score).slice(0, 5);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/frontend && pnpm test -- rankNextBestActions`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/shared/dashboard/rankNextBestActions.ts app/frontend/src/modules/shared/dashboard/rankNextBestActions.test.ts
git commit -m "feat(dashboard): next-best-action scoring (pure)"
```

---

## Task 4: Frontend — delta calculation (pure)

**Files:**
- Create: `app/frontend/src/modules/shared/dashboard/computeDelta.ts`
- Test: `app/frontend/src/modules/shared/dashboard/computeDelta.test.ts`

- [ ] **Step 1: Write the failing test**

Create `computeDelta.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { computeDelta } from './computeDelta';

describe('computeDelta', () => {
  it('reports an increase', () => {
    expect(computeDelta(5, 3)).toEqual({ direction: 'up', amount: 2, label: '▲ 2' });
  });
  it('reports a decrease', () => {
    expect(computeDelta(3, 5)).toEqual({ direction: 'down', amount: 2, label: '▼ 2' });
  });
  it('reports no change', () => {
    expect(computeDelta(4, 4)).toEqual({ direction: 'flat', amount: 0, label: '–' });
  });
  it('treats a missing previous as flat', () => {
    expect(computeDelta(4, undefined)).toEqual({ direction: 'flat', amount: 0, label: '–' });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/frontend && pnpm test -- computeDelta`
Expected: FAIL — cannot find module `./computeDelta`.

- [ ] **Step 3: Write minimal implementation**

Create `computeDelta.ts`:

```ts
export interface Delta {
  direction: 'up' | 'down' | 'flat';
  amount: number;
  label: string;
}

export function computeDelta(current: number, previous?: number): Delta {
  if (previous === undefined || previous === null || current === previous) {
    return { direction: 'flat', amount: 0, label: '–' };
  }
  const diff = current - previous;
  const amount = Math.abs(Math.round(diff));
  return diff > 0
    ? { direction: 'up', amount, label: `▲ ${amount}` }
    : { direction: 'down', amount, label: `▼ ${amount}` };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/frontend && pnpm test -- computeDelta`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/shared/dashboard/computeDelta.ts app/frontend/src/modules/shared/dashboard/computeDelta.test.ts
git commit -m "feat(dashboard): delta calculation (pure)"
```

---

## Task 5: Frontend — filter persistence (pure)

**Files:**
- Create: `app/frontend/src/modules/shared/dashboard/dashboardFilters.ts`
- Test: `app/frontend/src/modules/shared/dashboard/dashboardFilters.test.ts`

- [ ] **Step 1: Write the failing test**

Create `dashboardFilters.test.ts`:

```ts
import { describe, expect, it, beforeEach } from 'vitest';
import { loadFilters, saveFilters, DEFAULT_FILTERS, DashboardFilterState } from './dashboardFilters';

beforeEach(() => localStorage.clear());

describe('dashboardFilters', () => {
  it('returns defaults when nothing is stored', () => {
    expect(loadFilters('u1')).toEqual(DEFAULT_FILTERS);
  });

  it('round-trips a saved value per user', () => {
    const f: DashboardFilterState = { range: '30d', site: 'tunis-1' };
    saveFilters('u1', f);
    expect(loadFilters('u1')).toEqual(f);
    expect(loadFilters('u2')).toEqual(DEFAULT_FILTERS); // scoped per user
  });

  it('falls back to defaults on corrupt storage', () => {
    localStorage.setItem('eam.dashboard.filters.u1', '{not json');
    expect(loadFilters('u1')).toEqual(DEFAULT_FILTERS);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/frontend && pnpm test -- dashboardFilters`
Expected: FAIL — cannot find module `./dashboardFilters`.

- [ ] **Step 3: Write minimal implementation**

Create `dashboardFilters.ts`:

```ts
export interface DashboardFilterState {
  range: '7d' | '30d' | '90d';
  site: string;
}

export const DEFAULT_FILTERS: DashboardFilterState = { range: '7d', site: 'all' };

const keyFor = (userId: string) => `eam.dashboard.filters.${userId}`;

export function loadFilters(userId: string): DashboardFilterState {
  try {
    const raw = localStorage.getItem(keyFor(userId));
    if (!raw) return DEFAULT_FILTERS;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.range !== 'string' || typeof parsed.site !== 'string') {
      return DEFAULT_FILTERS;
    }
    return { range: parsed.range, site: parsed.site };
  } catch {
    return DEFAULT_FILTERS;
  }
}

export function saveFilters(userId: string, state: DashboardFilterState): void {
  try {
    localStorage.setItem(keyFor(userId), JSON.stringify(state));
  } catch {
    /* storage full / unavailable — non-fatal */
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/frontend && pnpm test -- dashboardFilters`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/shared/dashboard/dashboardFilters.ts app/frontend/src/modules/shared/dashboard/dashboardFilters.test.ts
git commit -m "feat(dashboard): per-user filter persistence (pure)"
```

---

## Task 6: Frontend — presentational components (thin, manual-verified)

> Repo has no React Testing Library, so these thin components carry no logic worth unit-testing (logic is in Tasks 3–5). Verify visually in the running app.

**Files:**
- Create: `app/frontend/src/modules/shared/dashboard/DashboardSkeleton.tsx`
- Create: `app/frontend/src/modules/shared/dashboard/DeltaBadge.tsx`
- Create: `app/frontend/src/modules/shared/dashboard/NextBestActions.tsx`
- Create: `app/frontend/src/modules/shared/dashboard/BriefingBar.tsx`
- Create: `app/frontend/src/modules/shared/dashboard/DashboardFilters.tsx`

- [ ] **Step 1: DashboardSkeleton.tsx**

```tsx
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-slate-800 animate-pulse" />
        ))}
      </div>
      <div className="h-40 rounded-lg bg-slate-800 animate-pulse" />
    </div>
  );
}
```

- [ ] **Step 2: DeltaBadge.tsx**

```tsx
import { computeDelta } from './computeDelta';

export function DeltaBadge({ current, previous }: { current: number; previous?: number }) {
  const d = computeDelta(current, previous);
  const color =
    d.direction === 'up' ? 'text-emerald-400'
    : d.direction === 'down' ? 'text-red-400'
    : 'text-blue-300';
  return <span className={`text-[11px] ${color}`}>{d.label} vs hier</span>;
}
```

- [ ] **Step 3: NextBestActions.tsx**

```tsx
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { rankNextBestActions, NbaInput } from './rankNextBestActions';

const SEV: Record<string, string> = {
  critical: 'border-red-500 bg-red-900/40 text-red-200',
  high: 'border-amber-500 bg-amber-900/40 text-amber-200',
  medium: 'border-blue-500 bg-blue-900/40 text-blue-200',
};

export function NextBestActions(props: NbaInput) {
  const actions = rankNextBestActions(props);
  if (actions.length === 0) {
    return <p className="text-sm text-blue-300 py-2">Aucune action prioritaire. Tout est à jour.</p>;
  }
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-blue-300">Actions prioritaires</p>
      {actions.map((a) => {
        const border = a.severity === 'critical' ? 'border-l-red-500'
          : a.severity === 'high' ? 'border-l-amber-500' : 'border-l-blue-500';
        return (
          <Link key={a.key} to={a.href}
            className={`flex items-center gap-3 rounded-md border border-slate-700 border-l-[3px] ${border} bg-slate-800 px-3 py-2 hover:bg-slate-700/60`}>
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${SEV[a.severity]}`}>
              {a.severity === 'critical' ? 'Critique' : a.severity === 'high' ? 'Urgent' : 'À faire'}
            </span>
            <span className="text-sm text-slate-100 flex-1">{a.label}</span>
            <ChevronRight className="h-4 w-4 text-slate-500" />
          </Link>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: BriefingBar.tsx**

```tsx
import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { client } from '@/lib/api';

export function BriefingBar({ site = 'all' }: { site?: string }) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res: any = await (client.apiCall as any).invoke({
          url: `/api/v1/dashboard/briefing?site=${encodeURIComponent(site)}`,
          method: 'GET',
        });
        const data = res?.data ?? res;
        if (alive) setText(data?.text ?? null);
      } catch {
        if (alive) setText(null); // bar simply hides on failure
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [site]);

  if (loading) return <div className="h-16 rounded-lg bg-slate-800 animate-pulse mb-4" />;
  if (!text) return null;

  return (
    <div className="flex gap-3 items-start rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 mb-4">
      <Sparkles className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
      <p className="text-sm text-blue-100 leading-relaxed">
        <span className="font-medium text-white">Briefing du jour. </span>{text}
      </p>
    </div>
  );
}
```

- [ ] **Step 5: DashboardFilters.tsx**

```tsx
import { DashboardFilterState } from './dashboardFilters';

const RANGES: DashboardFilterState['range'][] = ['7d', '30d', '90d'];
const LABEL: Record<string, string> = { '7d': '7 jours', '30d': '30 jours', '90d': '90 jours' };

export function DashboardFilters({
  value, onChange,
}: { value: DashboardFilterState; onChange: (v: DashboardFilterState) => void }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {RANGES.map((r) => (
        <button key={r} onClick={() => onChange({ ...value, range: r })}
          className={`text-xs px-3 py-1.5 rounded-md ${
            value.range === r ? 'bg-blue-600 text-white' : 'bg-slate-800 text-blue-300'}`}>
          {LABEL[r]}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Type-check + commit**

Run: `cd app/frontend && pnpm lint`
Expected: no errors in `modules/shared/dashboard/`.

```bash
git add app/frontend/src/modules/shared/dashboard/
git commit -m "feat(dashboard): briefing, NBA, skeleton, delta, filter components"
```

---

## Task 7: Wire components into shared/Dashboard.tsx

**Files:**
- Modify: `app/frontend/src/modules/shared/Dashboard.tsx`

- [ ] **Step 1: Add imports** (top of file, after existing imports)

```tsx
import { Link } from 'react-router-dom';
import { BriefingBar } from './dashboard/BriefingBar';
import { NextBestActions } from './dashboard/NextBestActions';
import { DashboardSkeleton } from './dashboard/DashboardSkeleton';
import { DeltaBadge } from './dashboard/DeltaBadge';
import { DashboardFilters } from './dashboard/DashboardFilters';
import { loadFilters, saveFilters, DashboardFilterState } from './dashboard/dashboardFilters';
```

- [ ] **Step 2: Replace the spinner loading block** (lines ~108-114) with the skeleton:

```tsx
  if (loading) {
    return <DashboardSkeleton />;
  }
```

- [ ] **Step 3: Add filter state** (near the other `useState` calls). Read the current user id from `localStorage` (the app stores `user`):

```tsx
  const userId = (() => {
    try { return String(JSON.parse(localStorage.getItem('user') || '{}').id ?? 'anon'); }
    catch { return 'anon'; }
  })();
  const [filters, setFilters] = useState<DashboardFilterState>(() => loadFilters(userId));
  const updateFilters = (f: DashboardFilterState) => { setFilters(f); saveFilters(userId, f); };
```

- [ ] **Step 4: Insert briefing, filters, and NBA into the JSX** — right after the header `<div>` block (after the `<p>Overview…</p>` closing `</div>`, before `{/* Metrics Grid */}`):

```tsx
      <DashboardFilters value={filters} onChange={updateFilters} />
      <BriefingBar site={filters.site} />
      <NextBestActions
        role={(JSON.parse(localStorage.getItem('user') || '{}').role) || 'ADMIN'}
        userId={Number(userId) || undefined}
        workOrders={recentWorkOrders.map((wo) => ({
          id: wo.id, priorite: wo.priorite, statut: wo.statut,
          technicien_id: (wo as any).technicien_id, machine_id: (wo as any).machine_id,
        }))}
        overduePMs={upcomingMaintenance.map((m) => ({ machine_id: m.id, nom: m.nom }))}
        alerts={[]}
      />
```

> The current page only fetches 5 recent WOs and upcoming maintenance; that is an acceptable candidate set for v1. Alerts are passed empty here (the shared page does not fetch them); role dashboards that already load alerts pass them through in Task 8.

- [ ] **Step 5: Add a delta badge + drill-through to the "Urgent Work Orders" card** as the reference example. Wrap that `<Card>` in a `Link` and add the badge under the number:

```tsx
        <Link to="/work-orders?priority=URGENTE">
          <Card className="cursor-pointer hover:bg-slate-700/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Urgent Work Orders</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{metrics.urgentWorkOrders}</div>
              <DeltaBadge current={metrics.urgentWorkOrders} previous={metrics.urgentWorkOrders} />
            </CardContent>
          </Card>
        </Link>
```

> `previous` is wired to the same value as a safe placeholder until a yesterday-snapshot source exists; it renders "–". When a prior-day metric is available, pass it here. Apply the same Link + DeltaBadge pattern to the other metric cards.

- [ ] **Step 6: Verify in the running app**

Run: `make up` (if not running), open the dashboard.
Expected: skeleton flashes on load, briefing bar appears (or hides cleanly if backend/LLM down), next-best-action list shows urgent items, urgent-WO card is clickable and routes to the filtered work-orders list, delta badge renders.

- [ ] **Step 7: Lint + commit**

Run: `cd app/frontend && pnpm lint`

```bash
git add app/frontend/src/modules/shared/Dashboard.tsx
git commit -m "feat(dashboard): wire briefing, NBA, skeleton, filters, drill-through into shared dashboard"
```

---

## Task 8: Wire into the three role dashboards

**Files:**
- Modify: `app/frontend/src/modules/cheftech/CheftechDashboard.tsx`
- Modify: `app/frontend/src/modules/chetop/ChetopDashboard.tsx`
- Modify: `app/frontend/src/modules/technicien/TechnicianDashboard.tsx`

For each file, repeat the minimal wiring (the components are shared):

- [ ] **Step 1: Import the shared components**

```tsx
import { BriefingBar } from '@/modules/shared/dashboard/BriefingBar';
import { NextBestActions } from '@/modules/shared/dashboard/NextBestActions';
import { DashboardSkeleton } from '@/modules/shared/dashboard/DashboardSkeleton';
```

- [ ] **Step 2: Replace each dashboard's spinner/loading return with `<DashboardSkeleton />`.**

- [ ] **Step 3: Mount `<BriefingBar />` at the top of the dashboard body, and `<NextBestActions ... />` below it**, mapping that dashboard's already-loaded work orders / alerts / overdue machines into the `NbaInput` shape. For `TechnicianDashboard`, pass `role="TECHNICIEN"` and `userId={currentUserId}` so the feed scopes to the technician's own assignments. Pass any alerts the page already fetches into the `alerts` prop.

> Each role dashboard already fetches its own data (stats, work orders, machines). Reuse those arrays — do not add new fetches. Where a field name differs, map it into the `NbaWorkOrder` / `NbaPM` / `NbaAlert` shapes from `rankNextBestActions.ts`.

- [ ] **Step 4: Verify each role dashboard in the running app** — log in as each role; confirm briefing + NBA render with role-appropriate content and the skeleton shows on load.

- [ ] **Step 5: Lint + commit**

Run: `cd app/frontend && pnpm lint`

```bash
git add app/frontend/src/modules/cheftech/CheftechDashboard.tsx app/frontend/src/modules/chetop/ChetopDashboard.tsx app/frontend/src/modules/technicien/TechnicianDashboard.tsx
git commit -m "feat(dashboard): wire briefing + next-best-action into role dashboards"
```

---

## Task 9: Full verification pass

- [ ] **Step 1: Backend tests**

Run: `pytest tests/backend/dashboard_briefing.test.py -v`
Expected: PASS.

- [ ] **Step 2: Frontend tests**

Run: `cd app/frontend && pnpm test`
Expected: existing suite + `rankNextBestActions`, `computeDelta`, `dashboardFilters` all PASS.

- [ ] **Step 3: Manual smoke (all four dashboards, each role)**

Confirm: skeleton on load; briefing shows (and degrades to nothing if LLM down — backend still 200 with `source:"template"`); NBA ordering correct; drill-through links land on the right filtered pages; filter buttons persist across reload; delta badges render.

- [ ] **Step 4: Final commit (if any cleanup)**

```bash
git commit -am "chore(dashboard): B1 command-center upgrade verification pass"
```

---

## Self-Review (completed)

- **Spec coverage:** briefing (hybrid cached, per-role/per-user, template fallback) → Tasks 1–2; next-best-action client-side scoring → Task 3; skeletons → Task 6/7/8; delta badges → Tasks 4,7; persisted filters → Tasks 5,7; drill-through → Task 7; app theme reuse → Task 6; all-four-dashboards → Tasks 7–8; testing → Task 9. Deferred items (wallboard, export) correctly excluded.
- **Placeholder scan:** none — every code step contains full code; the two intentional notes (model field-name verification, `previous` delta placeholder) are explicit instructions, not gaps.
- **Type consistency:** `NbaInput`/`RankedAction` defined in Task 3 and consumed unchanged in Tasks 6–8; `DashboardFilterState`/`loadFilters`/`saveFilters` consistent across Tasks 5–7; `compute_facts`/`facts_hash`/`make_briefing`/`render_template`/`_CACHE` consistent across Tasks 1–2.
- **Known follow-ups (out of scope):** real "yesterday" metric source for delta badges; alerts fetch on the shared dashboard; wallboard + export.
