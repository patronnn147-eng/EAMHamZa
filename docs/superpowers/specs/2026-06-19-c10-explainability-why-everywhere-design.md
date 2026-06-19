# C10 — Reusable "Why?" Everywhere (Explainability+) — Design Spec

Date: 2026-06-19
Status: Approved (pending written-spec review)
Source: `presentation/blueprint/EAM_FEATURE_BLUEPRINT.md` → Part C10
Sequence: Part C build order, item 1 of 8 (C10 → C9 → C8 → C4 → C5 → C3 → C6 → C7)

## 1. Goal

Attach a plain-language **"Why?"** explanation to every AI output — next-best-action, daily briefing, anomaly flag, and machine health verdict — through one reusable drawer fed by a shared contract. Hybrid generation: deterministic structured reasons shown immediately, plus an optional cached-LLM "Explain in plain words" button.

**Hard requirement — plain language for non-technical users.** The default view contains **no** ML jargon: no SHAP, ensemble, DST, RUL, weights, Kelvin, or P-codes (TWF/HDF/…). Operator language only. Confidence shown as words (Low/Medium/High), temperatures in °C, numbers only when they add meaning ("7°C above safe").

## 2. Current State

- `ExplainabilityDrawer.tsx` — P7 parts-only, role-aware, plain-language (4 sections). **Stays as-is** (no regression). `WhyDrawer` is its generic sibling.
- `SHAPExplanations.tsx` — charts SHAP factors (factor/impact/intensity); unified-health returns these when `include_shap=True`.
- Backend `build_ml_context` already classifies each sensor NORMAL/ATTENTION/CRITIQUE per machine category and converts K→°C — the single source we reuse for `sensor_status`.
- `rankNextBestActions.ts` (from B1) computes a `score` but discards the breakdown — we expose it.
- `/briefing` (from B1) returns `{text, generated_at, source}` — we add `facts`.

## 3. Shared Contract

`app/frontend/src/modules/shared/explain/whyTypes.ts`:

```ts
export type WhyTone = 'critical' | 'warning' | 'normal' | 'info';
export interface WhyReason { label: string; detail?: string; tone?: WhyTone }
export interface WhyConfidence { level: 'Faible' | 'Moyenne' | 'Élevée'; note: string }
export interface WhyPayload {
  title: string;                 // plain headline, e.g. "Risque de panne sous 7 jours"
  summary: string;               // one plain sentence
  reasons: WhyReason[];          // plain bullet reasons, no jargon
  confidence?: WhyConfidence;    // words, not %
  counterfactual?: WhyReason[];  // health only: "what would make it healthy"
  source: string;                // plain provenance line
  llmContext?: Record<string, unknown>; // structured facts sent to /why/explain
}
```

## 4. Plain-Language Layer (mandatory)

`app/frontend/src/modules/shared/explain/plainLanguage.ts` — pure, unit-tested:
- `SENSOR_LABEL`: `process_temperature → "température du procédé"`, `tool_wear → "usure de l'outil"`, etc.
- `FAILURE_LABEL`: `TWF → "usure de l'outil"`, `HDF → "surchauffe"`, … (reuse the map already in `ExplainabilityDrawer`).
- `kToC(k): number` — Kelvin→°C, rounded.
- `confidenceWords(agreement): WhyConfidence` — maps model agreement to Faible/Moyenne/Élevée + a plain note ("les vérifications sont d'accord").
- Producers MUST route every machine signal through these helpers. No raw sensor keys, codes, weights, or Kelvin reach a `WhyPayload`.

## 5. Producers (pure, unit-tested) — `shared/explain/producers/`

- `buildNbaWhy(action: RankedActionWithReasons): WhyPayload` — reasons from the score breakdown (urgency tier → "urgent", impact → "machine critique"). Requires extending `RankedAction` with a `reasons` breakdown (see §7).
- `buildBriefingWhy(facts: BriefingFacts): WhyPayload` — one plain reason per material fact.
- `buildAnomalyWhy(health: UnifiedHealth): WhyPayload` — lists sensors whose `sensor_status` is ATTENTION/CRITIQUE in plain words ("tourne trop chaud").
- `buildHealthWhy(health: UnifiedHealth): WhyPayload` — top SHAP factors → plain reasons; model agreement → `confidence`; each out-of-range sensor → `counterfactual` ("refroidir : 7°C au-dessus du seuil").

Each producer returns a minimal payload (`title` + `source`) when its data is missing — never throws.

## 6. Components — `shared/explain/`

- `WhyButton` — small trigger (`HelpCircle` icon, label "Pourquoi ?"); opens the drawer with a payload.
- `WhyDrawer` — reusable Sheet (app dark theme). Renders: title, summary, tone-colored reasons, confidence (words + simple bar), counterfactual block (if present), source line. Plus an **"Expliquer simplement"** button → `POST /api/v1/why/explain`. The drawer renders the full structured view with no network; the LLM button is additive. On LLM failure → toast, keep structured view.

## 7. Backend

### 7a. `sensor_status` on unified-health
Add to the unified-health response a compact array (reusing `build_ml_context` threshold logic — single source of truth):
```json
"sensor_status": [
  { "name": "process_temperature", "value_c": 41.9, "status": "CRITIQUE", "target_c": 35.0 }
]
```
`value_c`/`target_c` already in °C. Powers `buildAnomalyWhy` + `buildHealthWhy` counterfactuals without duplicating thresholds in the frontend.

### 7b. `POST /api/v1/why/explain`
`app/backend/modules/shared/routes/why.py` (auto-discovered).
- Body: `{ reasons: string[], context?: object }`.
- Returns `{ text, source }` where `source ∈ {cache, llm, fallback}`.
- Cache-first by a hash of `reasons` (reuse the `dashboard_briefing` cache pattern: in-memory, stale-prune). LLM prompt demands plain French, no jargon.
- **Never raises**: on LLM failure returns the reasons joined into a sentence (`source: fallback`), so the button always yields text. Mirrors the briefing safety property.

## 8. Wiring (4 surfaces)
- NBA rows (`NextBestActions.tsx`) → `WhyButton` per row, payload from `buildNbaWhy`.
- `BriefingBar.tsx` → `WhyButton`, payload from `buildBriefingWhy` (briefing response now carries `facts`).
- Anomaly card / alert (`MLIntelligenceTab.tsx`, `AlertsPanel`) → `WhyButton`, payload from `buildAnomalyWhy`.
- Health verdict (`MLIntelligenceTab.tsx`) → `WhyButton`, payload from `buildHealthWhy`.

## 9. Decisions
- **Role-agnostic** v1 — reasons are facts, identical for all roles. Existing role-aware P7 drawer untouched.
- Counterfactual only on the health producer.
- Briefing response gains `facts` (additive, non-breaking).
- `RankedAction` gains an optional `reasons` breakdown (additive; B1 tests stay green).

## 10. Error Handling
- Drawer renders structured reasons offline; LLM button failure → toast + structured view stays.
- Producers degrade to a minimal payload on missing data.
- `sensor_status` builder is best-effort; missing sensors omitted, never throws.

## 11. Testing
- Frontend (vitest, pure): `plainLanguage` helpers (no jargon leaks, K→°C), `buildNbaWhy`, `buildBriefingWhy`, `buildAnomalyWhy`, `buildHealthWhy` (assert no banned token — SHAP/ensemble/RUL/Kelvin/P-codes — appears in any output string).
- Backend (pytest): `sensor_status` builder (status + target per sensor), `/why/explain` cache hit + LLM-down fallback returns joined reasons and never raises.

## 12. Out of Scope (later increments)
- Technical-details toggle (raw SHAP numbers for power users).
- Role-aware Why content.
- Counterfactual on non-health surfaces.
