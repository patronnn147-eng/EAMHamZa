# SESSION STATE — ML Features Brainstorm / P7 build

> Resume file. Read FIRST on new session. Caveman-compressed. Token-prudent.
> Full plan: `~/.claude/plans/so-in-this-task-vast-orbit.md`. Spec: `docs/superpowers/specs/2026-05-29-p7-parts-coordination-design.md`.

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

## NEXT ACTION
Write master spec. Then ask user to review it (gate) before writing-plans.
