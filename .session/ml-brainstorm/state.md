# SESSION STATE — ML Features Brainstorm / P7 build

> Resume file. Read FIRST on new session. Caveman-compressed. Token-prudent.
> Full plan: `~/.claude/plans/so-in-this-task-vast-orbit.md`. Spec: `docs/superpowers/specs/2026-05-29-p7-parts-coordination-design.md`. Impl plan: `docs/superpowers/plans/2026-05-29-p7-parts-coordination.md`.

## ⏭ RESUME NEXT SESSION — START HERE
1. Re-activate modes: caveman(full), brainstorming-done(skip), subagent-driven-development for exec. Comm to user = plain non-technical/sales (no ML jargon). Token-prudent.
2. Read this whole file + impl plan. Branch = `clean_Phase_1`.
3. Last done: P7.1 core module + load_p7 (committed). NEXT TASK = **T5: train P7 model** (see "NEXT ACTION" below).
4. User chose to STOP after foundation (2026-05-29). User will pick training approach next session (had options: pause / write-train-code-only / full-train / fallback-first — UNRESOLVED, ask again).
5. Apply skills at exec: senior-ml-engineer, senior-data-scientist, database-designer, tdd-guide. Use cheap models for mechanical tasks.
6. git log to confirm commits: 59b06b1 spec, 162ba31 plan, c47d359 core, c356962 loader, 6a1f0f5 state.

## Active modes/skills (keep on)
caveman(full) + caveman-stats + cavecrew(delegate) + brainstorming + using-superpowers + engineering-skills + engineering-advanced-skills + subagent-driven-development(exec).
**User comm pref: NON-TECHNICAL / sales-person language. No ML jargon to user. Code/commits normal.**

## Goal
New ML capability program P7→P10. Build P7 FIRST, all 6 sub-phases at once.
P7 = Predictive Parts COORDINATION System (not just model).

## Decisions (locked)
- Q1 new predictive capability. Q2 all 4 (spare-parts/energy/quality/cascade). Q3 program+deep P7.
- P7 model = survival-driven (RUL+failure-type → P(fail≤horizon)×learned failure_type→parts map) + Croston/SBA consumable fallback + deterministic fallback if pkl missing.
- Q6 = build ALL 6 phases now.
- Auto-creation = HUMAN-IN-LOOP only (drafts, never silent).
- Persistence: extend `ml_prediction_log` w/ `p7_parts_demand` JSON col (NO new pred table).
- Timeline = DERIVED from existing timestamps (no new table). Readiness score = on-demand v1.
- Horizon 30d. Alerts reuse `alertes.py`. New alert type = PARTS_SHORTAGE.

## Reuse map (exploration-confirmed)
- Roles: TECHNICIEN/CHEFTECH/CHETOP/ADMIN. Guards: auth.py:82 require_role; FE ProtectedRoute/RoleBasedRedirect. Per-role dashboards exist.
- Deterministic skeleton: `app/backend/modules/ml/services/demand_forecast.py` (endpoint /api/v1/ml/inventory/demand-forecast).
- Data: pieces/stock/mouvement_stock/consumed_pieces/required_pieces/piece_machine/ordres_intervention(actual_failure_type).
- Label src: consumed_pieces ⋈ ordres_intervention.actual_failure_type.
- Loader: `app/ml-microservice/src/core/model_loader.py` load_p1..p6 lru_cache → add load_p7.
- Inference: `app/ml-microservice/src/predictions.py`. Routes: `app/ml-microservice/src/router.py` /predict/*.
- Backend ML: `app/backend/modules/ml/router.py` unified-health (:79-223).
- Alerts: `models/alertes.py` + FE AlertsPanel.tsx, ChefTechAlertWorkflow.tsx.
- WO/itv: ordres_travail, ordres_intervention. Approve+reserve: InventoryReservationService (admin_itv.py:102-160).
- Feedback: ml_prediction_log.py + actual_failure_type/ml_prediction_matched/retrained + consumed_pieces + ml_retraining.py. FE CompleteWorkOrderModal.tsx step3.
- Card pattern: MLIntelligenceTab.tsx (glass+Space Grotesk mono); PartsReadinessCard:164-230.
- Models sync rule: pkl in BOTH app/backend/modules/ml/models/ AND app/ml-microservice/models/.

## 6 phases
- P7.1 ML engine: notebook→pkl, load_p7, predict_parts_demand(machine_id,rul,ft_probs,horizon=30), /predict/parts-demand, predict-all+batch, unified-health parts_demand block, 1 "Parts Demand" card. Det fallback.
- P7.2 Alert routing: PARTS_SHORTAGE alert type; shortfall→alert by role (reuse AlertsPanel).
- P7.3 Role UX + plain lang + explainability drawer (why/what-if/who-acts). Admin=procurement queue; CHEFTECH=convert→itv/WO; CHETOP=biz risk; TECHNICIEN=prep checklist.
- P7.4 Auto-draft (guarded): shortfall→draft procurement+WO+reservation linked to pred; human approves.
- P7.5 Readiness Score tile + derived timeline + KPIs (prevented downtime/avoided rush/readiness rate/adoption).
- P7.6 Feedback closure: pred logged + consumed_pieces actual → compare → P7 retrain queue (extend ml_retraining.py).

## Output contract
parts_demand:{horizon_days, source:"p7_model"|"deterministic_fallback", items:[{piece_id,reference,name,expected_qty,on_hand,min_stock,shortfall,urgency_score,recommended_order_qty,driver}]}

## PROGRESS (update every step)
- [x] Brainstorm done, plan approved.
- [x] Session state file created (this).
- [x] Master spec written → docs/superpowers/specs/2026-05-29-p7-parts-coordination-design.md (committed 59b06b1)
- [x] Spec self-review (passed, no fixes)
- [x] User review gate (spec) — GREEN-LIT
- [x] writing-plans → impl plan: docs/superpowers/plans/2026-05-29-p7-parts-coordination.md (27 tasks)
- [ ] subagent-driven-development → execute P7.1..P7.6 ← NEXT (start Task 1)
- [ ] P7.1 brain | [ ] P7.2 alerts | [ ] P7.3 UX | [ ] P7.4 drafts | [ ] P7.5 score/timeline | [ ] P7.6 feedback
- [ ] E2E verify

## RESOLVED AT EXECUTION (corrections to plan — authoritative)
- Real loader = `app/ml-microservice/src/core/model_loader.py` (lru_cache, config.models_dir, _load/_extract helpers, startup_check). `src/model_loader.py` = legacy dup, IGNORE. (CLAUDE.md stale.) → load_p7 goes in src/core/.
- Import convention (root conftest.py aliases hyphen dir): `from app.ml_microservice.src.core.model_loader import ...` and `from app.ml_microservice.src.p7_parts_demand import ...`. NEVER `from src....`.
- Test locations (repo-root): ml-microservice units → `tests/unit/core/`; backend → `tests/backend/`; integration → `tests/integration/`. Plan's `app/ml-microservice/tests/` is WRONG.
- Existing loader pkl dict pattern: saved as dict {'model':..., ...}; `_extract(data,key)` pulls it. Mirror for p7.
- run tests from repo root: `pytest tests/unit/core/test_p7_parts_demand.py -v` (root conftest auto-loads).
- Execution batching (token-prudent): P7.1 Tasks1-4 = ONE dispatch (single file p7_parts_demand.py, TDD). Tasks 5-9 separate.

## EXEC PROGRESS (subagent-driven)
- [x] P7.1-core (T1-4 bundled: p7_parts_demand.py) — commit c47d359, 10 tests pass, verified
- [x] T6 load_p7 — commit c356962, 13 tests pass, verified
- [~] T5 notebook written (p7_parts_demand.ipynb) — AWAITING user to run in Docker Jupyter | [ ] T7 predict_parts_demand | [ ] T8 routes+unified-health | [ ] T9 card

### More exec corrections
- db_ml_training/ EXISTS but NO consumed_pieces.csv / required_pieces.csv / mouvement_stock rows. Task5 label source → ordres_intervention.parts_replaced text parsed to build failure_part_map. consumable_params={} (no mouvement_stock data).
- load_p7 returns WHOLE dict (pkl = {failure_part_map, consumable_params, parts_catalog, meta}); do NOT _extract. Add to get_all_models_status + startup_check (model_loader.py:78-97).
- T5 notebook written: app/ml-microservice/ml_research/p7_parts_demand.ipynb (7 code cells). User chosen Docker Jupyter.
- pieces/stock/mouvement_stock CSVs are ALL EMPTY. Only ordres_intervention has data (4000 rows, 1000 per FT).
- Graduate gate: P7 F1 > naive top-5-popularity baseline.
- [ ] P7.2 (T10-12) | [ ] P7.3 (T13-17) | [ ] P7.4 (T18-20) | [ ] P7.5 (T21-24) | [ ] P7.6 (T25-27) | [ ] E2E

## NEXT ACTION (resume here)
USER MUST RUN T5 notebook:
  1. `docker compose -f docker-compose.notebooks.yml up --build`
  2. Open http://localhost:8888
  3. Navigate to `app/ml-microservice/ml_research/p7_parts_demand.ipynb`
  4. Run All Cells — verify "GRADUATE: YES ✓" and "pkl verified"
  5. Confirm pkl saved to both model dirs
Then continue in code: T7 predict_parts_demand (loads pkl, falls back if None) → T8 routes+unified-health → T9 card → P7.1 GATE.
After P7.1: P7.2 alerts → P7.3 UX → P7.4 drafts → P7.5 score/timeline → P7.6 feedback → E2E.

## DONE THIS SESSION
brainstorm→spec(59b06b1)→plan(162ba31)→persistence+memory. Code: P7.1-core(c47d359), load_p7(c356962). Loader fully ready. p7_parts_demand.py pure module tested (10), loader tested (13).
T5: p7_parts_demand.ipynb notebook written (2026-05-29 session 2). User to run in Docker Jupyter.
