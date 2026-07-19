# EAM SagemCom — P1–P7 ML Model Engineering Roadmap

**Date:** 2026-07-19
**Ground truth source:** `app/ml-microservice/ml_research/retrain_pipeline_debug_log.ipynb` (executed this session) + direct code verification of `predictions.py`, `ml_retraining.py`, `seed_ml_data_all.py`, `p7_parts_demand.py`, `model_registry.py`, `p7_feedback.py`, `maintenances_planifiees.py`, `services/inventory/stock.py`.
**Produced by:** main thread synthesis + 4 specialized subagents (Data Engineering, Feature/Validation/XAI, ML Research/Model Training, MLOps) — see "Agent Responsibility Map" at the end.

## How to read this document

Every model gets the same 9-part breakdown the requester asked for. Read the **Master Roadmap** section last — it sequences all of the per-model work into 7 phases with dependencies and effort estimates. The single most important finding, repeated per-model below because it changes what "improvement" even means for that model:

> **P1, P2 (partially), and P5's high accuracy numbers are not real.** Their training labels are deterministic formulas of `tool_wear`, a feature the models also read as input. This is target leakage / label tautology, not a weak-model problem. No feature engineering, no algorithm swap, and no amount of synthetic data volume fixes this — only real, technician-confirmed outcome data that is *not* computable from a single sensor reading can fix it. This is stated explicitly per-model below rather than glossed over.

---

## P1 — Failure Probability

### 1. Current Problem
`app/backend/seed_ml_data_all.py` defines `failure_prob = min(95, (tool_wear-100)/130*95)` — a deterministic linear formula of `tool_wear`, which is feature #5 of the 7 features `XGBClassifier` reads directly (`[air_temp, process_temp, rpm, torque, tool_wear, temp_delta, rpm_torque]`). The model scores ~99% ROC-AUC even after group-holdout validation (one whole `machine_id` excluded from training). That survival is the diagnostic tell: every synthetic machine obeys the identical formula, so holding one out doesn't test anything new — it's target leakage / formula echo, **caused by the label**, not by data volume, features, validation methodology, or the algorithm.

### 2. Target State
A calibrated probability that a machine fails unplanned within a defined horizon (7/14/30 days), good enough that "this week's top-N risk machines" is a list a planner actually trusts and inspects. Success = ranking quality (precision at top-decile) + calibration (Brier score, reliability curve) against real outcomes — not raw AUC.

### 3. Required Dataset Improvements
Not fixable by more synthetic rows/machines/time — every synthetic sample will keep satisfying the same formula. Requires a new `failure_events` table: `machine_id`, `failure_timestamp`, `confirmed_by_technician: bool`, built from real corrective work orders, independent of any single sensor reading. New telemetry to make the eventual real model worth having: vibration (RMS + kurtosis), motor current draw, ambient temp/humidity, operating mode/shift, load profile, time-since-last-overhaul. Minimum viable: 1,000+ real labeled snapshots around 150–300 confirmed real failures, 6–12 months collection. **Synthetic data role going forward: quarantine, tag `data_source='synthetic_formula'`, exclude from accuracy reporting, usable only for pipeline/schema testing — never as pretraining, since pretraining on a tautology anchors the model toward the wrong decision boundary.**

### 4. Feature Engineering Improvements
Rate-of-change/rolling-stat/wear-derivative features are *derivatives of the leaked feature* — expect them to keep AUC at ~99% or push it higher, not reveal the leak; do not interpret any lift from these as real learning. Contextual features (ambient conditions, shift, operator, machine age/duty-cycle) are the ones that would matter for a real model, precisely because they're independent of `tool_wear` — but against the current label they'll show near-zero SHAP importance, so building them now has no measurable payoff. **Recommendation: build the contextual/rate-of-change pipeline now as reusable infrastructure, but treat it as prepared-and-shelved until the label is fixed.**

### 5. Model Improvements
Keep `XGBClassifier` — the algorithm is not the bottleneck, no architecture change fixes a label formula. Once real labels exist: add probability calibration (isotonic/Platt) and consider monotonic constraints on `tool_wear` for interpretability.

### 6. Validation Improvements
**The diagnostic that proves the tautology, cheap and should run before anything else:** feature-ablation test — retrain P1 with `tool_wear` (and its derived formula) removed, reusing the existing `_eval_accuracy_gate`/`_retrain_one_model` harness in `ml_retraining.py`. AUC collapsing to ~50% (chance) proves total tautology; collapsing only to 60–70% proves partial real signal in the other 6 features. Supporting check: raw correlation between target and `tool_wear` alone (should be ≈1.0). Evolve single-machine holdout into **leave-one-machine-out CV (LOMO-CV)**, reporting mean±std of AUC/F1 across folds — this also separates "every fold scores ~99%" (systematic leakage) from "scores vary wildly by fold" (small-sample noise), which look identical from a single fold. Add calibration curve + Brier score (P1's output is shown to technicians as a percentage). Once real labels exist, prioritize AUC-PR over ROC-AUC (real failure will be rare).

### 7. Retraining Strategy
**Never automatically, no cadence until the label-source issue is resolved.** Scheduling retraining on a broken tautological label just produces a false sense of freshness. Trigger: none — this is a labeling fix, not a retraining-ops problem. Batch only (XGBClassifier has no online-learning path here), but moot until the label changes.

### 8. Expected Impact
No modeling change moves this number in a meaningful direction — today's ~99% measures arithmetic reproduction, not failure prediction. **80–90% is not achievable and cannot be approached by any modeling change.** Once real technician-confirmed labels exist (not computable from any single input feature), a realistic target is 70–80% ROC-AUC with meaningful top-decile precision lift; 80–90% would need years of accumulated real failure history and is optimistic even then. Key risk: shipping "99%" trains planners to trust a definitionally fake number — worse than shipping nothing.

### 9. Implementation Priority
**High** — not because it's easy to fix (it isn't, without new data), but because it's actively misleading stakeholders today. Immediate action (low-cost, this sprint): run the ablation-test diagnostic and correct the dashboard/reporting so P1 is never shown as an "accuracy" figure again until real labels exist.

---

## P2 — Failure Type

### 1. Current Problem
`MultiOutputClassifier(XGBClassifier)`, same 7 features. Labels are thresholded on `tool_wear` bands in seed data (>=190 TWF, >=155/>=100/>=60 other types) — same tautology family as P1 for those classes, compounded by a genuine, separate problem: ~240 synthetic rows across ~5 classes, severe class imbalance (RNF F1=0%, TWF F1=11% in the group-holdout debug run). Real result ~69% F1 macro, correctly gated off (`min_f1 >= 0.70`). **Two distinct causes: label tautology (majority classes) AND real data starvation (minority classes) — they need two different fixes, not one.**

### 2. Target State
Predict failure mode (TWF/HDF/PWF/OSF/RNF/none) accurately enough that a planner pre-stages the right part/skillset before the technician arrives. Success = macro-F1 balanced across classes with particular attention to recall on rare-but-costly modes (RNF, TWF).

### 3. Required Dataset Improvements
New structured `failure_type` enum populated by the technician at work-order closure (root-cause coding taxonomy), replacing the current free-text field in `ordres_intervention`. New telemetry: motor current/power signature (HDF), torque spike/rolling-max/derivative history (OSF), vibration signature (TWF vs OSF discrimination), power-cycle/startup-shutdown event timestamps (RNF, defined as wear-uncorrelated — only discoverable via event timestamps that don't exist today). Target 50–100 real confirmed events per class minimum (250–500 total, 750–1,500 preferred), 12–24 months, potentially accelerated by targeted maintenance campaigns on high-wear machines. **Synthetic role: usable only as SMOTE-style augmentation for minority classes once real seed examples exist to anchor the distribution — not from the current threshold-based generator.**

### 4. Feature Engineering Improvements
`tool_wear × torque` interaction targets OSF's real mechanism (torque×wear product) but will also partially echo the P1-family tautology — build it, but label resulting OSF SHAP explanations as leak-adjacent, not a validated win. Rolling `temp_delta` stats + RPM rolling minimum (HDF signature) and power rolling volatility off `rpm_torque` (PWF signature) are genuinely additive — these target trend, not instantaneous magnitude, and aren't derived from `tool_wear`. What actually moves RNF=0%/TWF=11% is very likely not features at all — with ~240 rows across 5 classes, minority classes may have zero occurrences in a given LOMO fold; class-weighted training or BorderlineSMOTE (applied after the group split, never across it) addresses this directly.

### 5. Model Improvements
Keep `MultiOutputClassifier(XGBClassifier)` — not the bottleneck; more capacity on 240 imbalanced rows overfits harder, doesn't generalize better. Concrete levers: class-weighted loss / per-class `scale_pos_weight`, threshold tuning per class via precision-recall curves (lower the cutoff for high-miss-cost classes like RNF instead of a fixed 0.5).

### 6. Validation Improvements
Per-class ablation test (not just P1's monolithic one) — if OSF's F1 collapses on ablation while HDF's doesn't, that tells you which classes are tautological vs. real. Explicitly check class presence per LOMO fold before scoring — F1=0% because a class never appeared in a fold is a different failure mode than F1=0% because the model is bad at a class it saw; conflating these is exactly what makes RNF=0%/TWF=11% hard to interpret today. Keep macro-F1 as the headline gate (0.70) but also gate on worst-class recall — a model can pass 0.70 macro-F1 while a rare class sits at 0% recall, which is what's happening now. Add AUC-PR per class.

### 7. Retraining Strategy
Manual-trigger, event-driven — retrain when a meaningful batch of new technician-confirmed failure-type labels accumulates (a "N new labels since last train" counter, sharing logic with the accept-gate), not on a fixed calendar; weekly/monthly retrains on ~240 near-static rows waste compute for no gain. Batch only. Keep the existing `min_f1 >= 0.70` gate exactly as-is — it's correctly blocking bad deploys today.

### 8. Expected Impact
Resampling + per-class threshold tuning on the *same* data could realistically move macro-F1 from ~69% to ~72–76% (genuine, achievable near-term gain, but doesn't escape the underlying tautology for majority classes). **80–90% F1 macro is not realistic** until (1) the tool_wear-band label leakage shared with P1 is broken by real failure-mode-at-repair data, and (2) rare-class support grows into the hundreds via real fleet history. Dependency: ride the same real-label pipeline built for P1 fix — same root cause, same seed generator.

### 9. Implementation Priority
**Medium** — correctly gated off today (no user-facing harm), but data-starved. Prioritize the low-cost resampling/threshold-tuning lever now (days, not months) while the real-label pipeline (shared with P1) is being built.

---

## P3 — RUL (Remaining Useful Life)

### 1. Current Problem
`XGBRegressor`, same 7 features. **The one model with a proven real signal.** After switching validation from random row-shuffle (which let the model see interpolated points from the same machine's trajectory in both train and val — memorization) to group-holdout (one whole `machine_id` excluded, forcing genuine extrapolation), R² dropped from a fake 96% to a real 67%. Root cause of the *original* 96%: validation methodology (row-shuffle), now fixed. Current 67% ceiling is a genuine data/feature limitation, not a bug.

### 2. Target State
A genuine time-to-event estimate with a defensible confidence interval ("42 days remaining, 90% CI [28, 61]") a planner schedules a maintenance window against with real confidence. Success = C-index sustained >0.62 (already cleared per project record) trending toward 0.70+, MAE within 15% of baseline (already cleared), plus calibrated prediction intervals.

### 3. Required Dataset Improvements
Real run-to-failure (or partial-lifecycle + censoring) sequences from at minimum 15–20 real machines — directly extends the group-holdout test beyond a handful of synthetic machines; highest-leverage single investment in this roadmap since the architecture is already proven. New telemetry: vibration RMS/kurtosis *trend* (biggest current gap — bearing degradation is a trend signal, invisible in the 5 raw sensors today), motor current draw trend, time-since-last-overhaul (currently no such prior exists at all despite being one of the strongest classical RUL priors), ambient temp/humidity, load profile/duty cycle. **Synthetic role: keep as augmentation for rare/fast-degradation edge cases, capped at ≤20–30% of any training batch once real data is the majority — justified specifically because P3, unlike P1/P5, has already demonstrated the architecture generalizes on real structure.**

### 4. Feature Engineering Improvements
Wear velocity (Δtool_wear/Δcycle) and acceleration — RUL is fundamentally about *rate* of degradation; two machines at identical instantaneous wear but different velocities have different true RUL, and this signal doesn't exist in the current snapshot-only 7 features. Rolling mean/std/min/max of process_temp/torque/RPM over 5/10/20 cycles. Cycles-since-last-maintenance if joinable to maintenance-event timestamps (likely one of the highest-value single additions). Per-machine baseline deviation (z-score vs. that machine's own historical mean/std, computed causally/past-only to avoid leaking across the group-holdout boundary). Machine age/duty-cycle category. Caution: with few machines, an expanded feature set risks overfitting train folds even though group-holdout catches machine-level overfitting — re-run SHAP importance after each addition and prune what doesn't earn its keep.

### 5. Model Improvements
**The one model where a technique change is justified** — not because XGBoost is deficient, but because RUL is fundamentally a time-to-event problem with censoring (machines still running past the observation cutoff are right-censored, not "labeled zero"), which plain regression doesn't model. Two-track: (1) near-term, low-risk — keep `XGBRegressor` in production, add quantile/pinball-loss regression for prediction intervals instead of a bare point estimate; (2) medium-term — Cox Proportional Hazards or Weibull AFT on the same 5 raw sensors, explicitly handling right-censoring. The project's existing "P3 LSTM Hybrid" research track (C-index-gated, MAE=14.95, C-index=0.620, machines 70–79 held out) is the correct long-term direction but currently graduates on the same synthetic wear curve as everything else, so its added complexity isn't yet earning its keep over the XGBoost baseline — treat Cox/Weibull as the near-term statistical upgrade, LSTM/TFT as the long-term one once real sequential data exists.

### 6. Validation Improvements
This is the validation success story worth institutionalizing: row-shuffle → whole-machine holdout was the fix. Evolve to **LOMO-CV** (hold out each machine once, mean±std of R²/MAE across folds) given the small machine count — the correct generalization of k-fold here (row-based k-fold would silently reintroduce the original leak). Verified in code: `_eval_accuracy_gate` already applies `score >= min_r2` with `_MIN_REGRESSOR_R2 = 0.40` — sitting ~27 points below the demonstrated real 0.67, meaning today it would only catch a catastrophic regression, not enforce a meaningful bar. Recommend raising it once LOMO-CV variance is measured (e.g. `mean − 1.5×std`). Add quantile coverage monitoring (P3 feeds P7's decay curve — a point estimate alone understates what's knowable; add prediction intervals and monitor whether 80%/95% intervals actually contain the true RUL at the nominal rate).

### 7. Retraining Strategy
**This is the model worth an actual scheduled cadence.** Propose monthly batch retraining, OR triggered whenever a full holdout-eligible machine's lifecycle newly closes out (more meaningful than raw row count, since P3's methodology depends on group-holdout by machine). Batch only — group-holdout is inherently a batch-time procedure. Because it's the trustworthy model, it should be first in line for the new regressor accept-gate (Phase 1) — nothing today stops a bad P3 retrain from silently overwriting a good one.

### 8. Expected Impact
Near-term (quantile regression + Cox/Weibull layered on existing data): C-index could realistically move from 0.62 to 0.65–0.68. **80–90% (as C-index) is plausible medium-term, but not soon and not without real data** — crossing 0.75–0.85+ requires dozens to low-hundreds of complete real failure events with sensor history leading up to them, not ~10 synthetic machines on a hardcoded wear curve. Risk: because P3 already earned trust through honest validation, any shared-pipeline refactor while fixing P1/P2 leakage must re-run P3's group-holdout gate before merging, so it isn't silently regressed.

### 9. Implementation Priority
**High** — best ROI in the entire roadmap: real signal already proven, clear technique upgrade path (quantile/Cox), and it's the one model where more real data has a direct, provable payoff instead of an uncertain one.

---

## P4 — Behavioral Anomaly

### 1. Current Problem
IsolationForest (30%) + Z-score (20%) + Cluster deviation (10%) + Autoencoder (40%, **disabled** — TensorFlow not installed in the ml-microservice runtime, weights renormalize across the 3 active components), 5 raw sensor features only, no engineered features at all. Unsupervised — no labeled anomaly ground truth exists anywhere in the app, so there is currently no accuracy metric, real or fake (expected for unsupervised design, not a bug — but there's zero feedback loop). **Confirmed separately this session: a live infra bug** — `model_registry.py` reads/reports on `ml_model_p4_anomaly_v2.pkl` while `ml_retraining.py`'s retrain path writes to `ml_model_p4_anomaly.pkl` (v1) — two different files, silently diverged. Retraining P4 today does not update the file the app actually scores against.

### 2. Target State
Flag genuinely anomalous behavior early enough that staff open an investigation rather than tune it out as noise. Since it's unsupervised, success cannot be "accuracy" — it must be operational: how often a flag precedes a real work order within N days (proxy precision), how often real work orders happen with no prior flag (proxy recall).

### 3. Required Dataset Improvements
Training stays unsupervised on raw sensor streams — do not convert P4 to a supervised classifier. What's needed is a separate **evaluation** dataset: an `anomaly_events` log capturing, for every flag (score >0.5), a technician adjudication (`machine_id`, `flagged_at`, `ensemble_score`, `sensor_snapshot`, `technician_verdict`: confirmed/false-positive/benign-transient, `root_cause_if_found`). New telemetry: vibration (biggest gap — the ensemble can't see bearing/mechanical anomaly signatures on the current 5 sensors at all), motor current draw, ambient temp/humidity (to distinguish genuine anomalies from environmental drift), operating mode/shift (so startup/shutdown transients aren't flagged as anomalies). Target: 100–200 technician-adjudicated flag events over 3–6 months of live shadow-mode operation. **Synthetic role: not usable for evaluation ground truth (no way to synthesize "was this real") — synthetic sensor-spike injection is useful only as a sanity-check of raw detection sensitivity, kept strictly separate from the real-world precision estimate.**

### 4. Feature Engineering Improvements
Current gap: instantaneous snapshots only — blind to slow drift that never leaves the "normal" range momentarily (e.g. torque creeping 0.5%/cycle for 200 cycles looks fine reading-by-reading but is a real trend anomaly). Add rolling mean/std (10-cycle window) and rate-of-change of the same 5 sensors, fed into the IF/Z-score components — converts a point-anomaly detector into one that also catches trend anomalies. **Highest-value single change:** replace the pooled `training_stats` (global mean/std from `ai4i2020.csv`) with a **per-machine baseline** for Z-score/Mahalanobis — a machine that naturally runs hotter/faster than the population currently looks anomalous relative to the pooled baseline even when behaving normally for itself; touches only `training_stats`, not `weights`/`thresholds`, low risk. Explicit limit: none of this creates ground truth — only the proxy-label backtest (below) can assess whether it actually helped.

### 5. Model Improvements
Ensemble structure isn't obviously the bottleneck — the real gap is zero feedback loop, so the 30/20/10/40 weighting and 0.5 threshold are fixed by design intuition, never calibrated against outcomes. Sequenced fix: (1) immediate, deployment not modeling — re-enable the Autoencoder (install TensorFlow) so the shipped ensemble matches the validated design instead of a silently-renormalized 3-component version; (2) once outcome tracking exists — move to a contamination-calibrated ensemble (tune IF's contamination param and the 0.5 threshold against observed flag-precedes-workorder rate), and/or a semi-supervised approach (Deep SVDD, or weak-labeling sensor windows preceding *confirmed* real failures once P1's real-label pipeline exists).

### 6. Validation Improvements
No ground truth means no leakage in the traditional sense, and no split fixes anything. What's actionable: a **proxy-label backtest** — join P4's flagged cycles against real operational outcomes (an intervention or logged failure within N cycles, sourced from `ordres_intervention`/`intervention_workflow.py`) and compute precision/recall@k retrospectively. Not a train/test split — a backtest against outcomes, structurally identical to what's proposed for P7. Track as a KPI even without formal gating — it's the only feedback signal this model gets without a dedicated labeling initiative. Interim metrics: anomaly-flag rate per machine over time (a sudden jump is itself alertable, independent of ground truth) and score-distribution stability (KS-test/PSI vs. `training_stats` baseline) to catch silent drift.

### 7. Retraining Strategy
Manual-trigger only, and **do not schedule until the v1/v2 file-path bug is fixed** — a scheduled retrain today would give a false sense of freshness identical in shape to P1's problem, caused by an infra bug instead of a labeling bug. Once fixed: infrequent, manual-only, triggered by observed drift in the training population's sensor distributions (compare current sensor mean/std against the baked-in `training_stats`) rather than a calendar, since there's no accuracy metric to validate a retrain against — treat retrains as higher-risk, human-reviewed events. Batch only (IsolationForest has no incremental variant in scikit-learn). Any retrain trigger should also re-verify the weight-renormalization logic against the frozen 30/20/10/40 (AE-off) split so a retrain can't silently change the blend.

### 8. Expected Impact
No accuracy number is honest today — quoting one would be fabricated (expected for unsupervised, but means **80–90% is a meaningless target right now**). What's achievable immediately: restoring the Autoencoder (TensorFlow install) puts the shipped ensemble back to its validated design — a real, low-risk fix independent of any accuracy claim. To ever quote precision/recall, minimum required signal: outcome-tracking loop (technician-confirmed issue within N days of a flag) accumulated over ~100+ flagged events.

### 9. Implementation Priority
**High** for the infra fixes (v1/v2 mismatch + TensorFlow install — both cheap, both currently silently broken), **Medium** for the evaluation-loop buildout (real payoff, but calendar-bound not effort-bound).

---

## P5 — Priority

### 1. Current Problem
`RandomForestClassifier`, same 7 features. Priority label derived from the same `tool_wear` threshold family as P1, just a softer relationship — same tautology, diluted. Compounded by a small-sample problem: result swung 81%→88% between two retrain runs on only a 60-row holdout — that swing is sampling noise, not model improvement, and should never be reported as progress.

### 2. Target State
Rank work orders so real urgency actually rises to the top of a planner's queue. Success = decision-quality — does P5's ranking beat simple heuristics ("oldest ticket first," "highest wear first") against what planners would/did actually prioritize — not classification accuracy in isolation.

### 3. Required Dataset Improvements
**Not data-volume-fixable for the same structural reason as P1** — more synthetic rows from the same threshold rule adds no real signal, and pretraining on this label would actively bias the model toward the tautology. Priority is fundamentally a business/operational decision, not a sensor-derived quantity: real labels require capturing actual dispatcher/technician priority assignments at triage time, informed by factors the current formula can't see — production-line criticality, spare-parts availability at triage, number of concurrently open competing work orders, SLA/business urgency tags, safety-flag overrides. New structured `priority_assigned` field captured at real dispatch time. Target: 300–500 real dispatcher-assigned decisions minimum across 3–4 tiers — the current 60-row holdout is roughly an order of magnitude too small, exactly what the 81%→88% swing demonstrates. **Synthetic role: discard entirely going forward, including as pretraining.**

### 4. Feature Engineering Improvements
No tool_wear-derived feature (velocity, rolling stats, acceleration) fixes this — it can only sharpen or blur the same leak. The 81%→88% swing is a separate small-sample-variance problem, not primarily feature/leakage — a single 60-row fold has enough sampling noise to explain a 7-point swing on its own; adding features won't stabilize it, only more folds will reveal whether the range is real. Honest recommendation: no feature engineering currently — the rolling-stat/interaction features proposed for P1/P3 only become relevant once priority ground truth is redefined off real dispatcher/work-order urgency.

### 5. Model Improvements
Keep `RandomForestClassifier` — not the bottleneck, same reasoning as P1. The only defensible near-term change is measurement hygiene: report accuracy as mean±std over repeated (e.g. 5×) group holdouts instead of a single run, so swings like 81%→88% are correctly understood as noise, not progress.

### 6. Validation Improvements
Same ablation-test requirement as P1 (remove `tool_wear`, check for macro-F1 collapse) — identical tautology mechanism, softer. Run LOMO-CV specifically to quantify the swing — if fold-to-fold std-dev is, say, ±5–8 points, the observed swing is unsurprising sampling noise, turning an anecdotal worry into a measured, reportable number. Keep macro-F1 (gate 0.70) but surface the LOMO-CV std-dev next to it on the admin dashboard so anyone reading "88%" also sees its confidence interval.

### 7. Retraining Strategy
Manual-trigger only, same tautology-adjacent concern as P1 (softer). A scheduled cadence would just chase noise. Trigger: none automated; retrain only alongside a P2 retrain (shares features and underlying data maturity), always inspect the F1 delta manually rather than trusting a single-run pass/fail. Batch only. Enlarge the holdout set before trusting any retrain-driven change.

### 8. Expected Impact
Same verdict as P1: **80–90% is not a real target** under the current label; any single-run number on 60 rows of tautological labels is untrustworthy regardless of the digit shown. Real-world requirement: priority labels from planners' actual triage order (timestamped) or real downstream cost/urgency outcomes, plus a larger holdout — 60 rows is too small to produce a stable percentage independent of label quality.

### 9. Implementation Priority
**Medium** — less user-facing-visible than P1 (internal prioritization, not a headline "accuracy" number shown as prominently), but same root cause, so bundle its real-label fix with P1's data workstream rather than treating it as separate work.

---

## P6 — Maintenance Schedule

### 1. Current Problem
Regression, 8 features (7 base + `tool_wear²`). **Never retrains** — hard-skipped every single run in code (`ml_retraining.py`: `"reason": "P6 requires actual maintenance scheduling outcomes"`), because zero ground-truth signal for "was this scheduled date correct" exists anywhere in the app's data model. Confirmed this session: `maintenances_planifiees.py` currently only carries `date_planifiee` (planned date) — no completion/actual-date or outcome field exists. Stale ~65% R² sitting in production, unverified this session, effectively unmonitored and displayed with no caveat.

### 2. Target State
Recommend a maintenance date/window that, if followed, reduces both premature (wasteful) and late (risky) interventions versus a fixed calendar schedule. Success = a real comparison — did machines scheduled per P6 see fewer unplanned failures *and* less wasted early maintenance than a naive fixed-interval baseline.

### 3. Required Dataset Improvements
The core gap, most literal "no ground truth exists" case in the roster: schema addition, not a new subsystem — add `date_realisee` (actual completion date, captured at WO closure) to the existing maintenance-planning table, paired with an explicit outcome tag: `schedule_outcome` enum (`ON_TIME` / `PREMATURE` — machine still healthy at scheduled time / `LATE` — a failure or urgent intervention occurred before the scheduled date / `SKIPPED_REPLANNED`), reconstructed by comparing `date_planifiee` vs. the real closure date of the linked `ordre_intervention`/`ordre_travail`. New features once outcome data exists: technician workload/capacity (available hours/week — "right time" is partly a resourcing constraint, not pure degradation physics), spare-parts lead time (sourced from P7's parts-ledger data — scheduling before parts are in stock is itself a bad-timing outcome). Target: 12–24 months of real completed cycles, 200+ scheduled-vs-actual pairs with a timing-outcome tag. **Synthetic role: not usable at all — unlike P1/P2/P5, there is no plausible formula to fake "was this scheduled at the right time"; inventing a synthetic proxy would just create a sixth tautology. Leave hard-skipped rather than fake it.**

### 4. Feature Engineering Improvements
Premature to build anything now — the prerequisite is data collection (above), not features. Once outcome data exists, the useful feature set mirrors P3's (cycles-since-maintenance, per-machine baseline, age/duty-cycle category), since scheduling is structurally RUL-adjacent. Until then, no rolling-window/lag feature work — it would be feature-engineering theater against a frozen, unvalidated model.

### 5. Model Improvements
No algorithm change can be responsibly recommended while there's no way to verify improvement — this is a measurement-gap problem, not a modeling problem. Correct action within scope: do not retrain, do not swap algorithms, surface "unverified" in UI/monitoring instead of letting a stale 65% R² sit silently alongside genuinely-validated models and look equivalent.

### 6. Validation Improvements
No split-based fix is possible without a label. Once outcome data accumulates, the same group-holdout/LOMO-CV approach used for P3 applies directly (structurally identical regression problem). Until then: label the stale 65% R² "unverified" everywhere it's displayed — a reporting-honesty fix that should ship immediately, independent of when real validation becomes possible.

### 7. Retraining Strategy
Correctly staying at "never automatically" — the code's own skip reason is accurate and should remain as-is. Concrete minimal schema change needed before this can ever change: the `date_realisee`/`schedule_outcome` addition described above (data-model prerequisite, not a retraining-cadence decision — flag to whoever owns the data model).

### 8. Expected Impact
**80–90% is entirely speculative** — there isn't even a way to honestly measure *current* performance; the stale 65% R² was almost certainly computed against a synthetic/tautological target like the others and hasn't been re-verified. Required real-world data: actual scheduled-vs-actual dates paired with outcome labels — doesn't exist anywhere today, per the retraining code's own explicit skip. Until it does, no accuracy claim about P6 is honest.

### 9. Implementation Priority
**Low** for modeling work (nothing to do until schema lands), **High** for the one-line fix of labeling it "unverified" in the UI — cheap, immediate, stops a silent trust gap today.

---

## P7 — Parts Demand

### 1. Current Problem
Not a trained model — a deterministic pipeline (`app/ml-microservice/src/p7_parts_demand.py`): `p_fail_within()` × failure-type probs from P2 → `survival_demand()` (decay curve off P3's RUL), plus `croston_forecast()` (intermittent-demand smoothing, α=0.4 default) on consumable usage, merged with current stock into shortfall/order/urgency via `build_parts_demand()`. Quality is mechanically capped by P2 and P3's real accuracy — garbage in, garbage out. Stale precision/recall (12% precision / 100% recall — over-flags almost everything), unverified this session. Root data gap confirmed this session: `StockService` (`app/backend/services/inventory/stock.py`) tracks current quantity only, not a historical movement time series — Croston fundamentally needs a per-SKU timestamped consumption series, which the original training source (`ordres_intervention.parts_replaced` free text) never structurally provided (and the dedicated CSVs were empty per project history).

### 2. Target State
Recommend parts to stock/order such that shortfall predictions correlate with real stockout events and urgency scores correlate with real time-to-need. Success is entirely outcome-based ("when P7 says order urgently, a real shortage was actually close"), not a training metric, since it's not a trained model.

### 3. Required Dataset Improvements
A `stock_movements` ledger table (`part_id`, `quantity`, `work_order_id`, `movement_type`, `timestamp`), populated automatically whenever `StockService.consume_stock`/`add_stock` runs — closes the single biggest concrete gap: the consumption side already fires on every real usage event, it just isn't persisted as queryable history today. The feedback loop is already half-built and unused: `app/backend/modules/ml/services/p7_feedback.py` already logs predicted-vs-actual parts to `ml_prediction_logs.p7_parts_demand` on intervention completion — currently write-only, never consumed. Build the read side: a periodic job aggregating this log into a live precision/recall report. Target: 6–12 months of real structured parts-movement data across SKUs used in interventions; 100+ completed interventions with an attached prediction for precision/recall re-verification. **Synthetic role: usable as a cold-start decay-weighted prior for SKUs with too little real history — but the stale 12%/100% metric suggests the deterministic thresholds need re-tuning against real feedback first; this is a threshold-tuning problem, not a "generate more synthetic parts data" problem.**

### 4. Feature Engineering Improvements
The only lever that moves P7's ceiling is upstream P2/P3 quality — feature engineering on P7 itself can't outrun a 69%-F1 P2 or an uncertainty-free P3. Legitimate P7-local work: align Croston demand-interval buckets to maintenance-calendar periods rather than raw calendar time (if consumable usage clusters around planned maintenance windows); add a lead-time-adjusted stock-coverage feature (days-of-runway at current burn rate) before the shortage threshold is applied — directly targets the 12%/100% symptom, since the pipeline currently has no sense of "how much runway is left," only "is a part predicted to be needed at all." Honest bound: these changes will not fix 12%/100% by more than a marginal amount while built on a below-gate P2 — state this explicitly rather than implying a threshold tweak solves it.

### 5. Model Improvements
No algorithm to improve independently of fixing P2/P3 — the survival curve's decay shape and Croston's α are the only levers that belong to P7 itself, and both are currently formula constants with no calibration loop. Concrete scoped improvements: grid-search Croston's α per part-class once real series are long enough (>12–18 points); refit the survival curve's decay shape against real censored time-to-failure data once P3's Cox/Weibull track and real labels land; recalibrate the shortfall/urgency threshold logic against real stockout frequency.

### 6. Validation Improvements
Backtesting against realized outcomes, not a train/val split. Freeze P2/P3 outputs and stock levels as of a historical date, compute what P7 would have predicted, compare against what was actually consumed/needed in the following window — use the current 12%/100% as the baseline to beat. Decompose before tuning: split error into (a) P2's 69%-F1 misclassification propagating into the wrong decay curve, (b) the Croston forecast alone, (c) the shortage-threshold logic itself being conservative — tune blindly and you risk trading recall for precision without knowing which upstream component drove the imbalance. Re-run the same backtest after P2/P3 fixes land to quantify how much of P7's precision improves "for free."

### 7. Retraining Strategy
Not classical retraining — **recalibration** of parameters, since it's a deterministic pipeline. `p7_feedback.py` already runs on every intervention completion and writes the comparison back into `ml_prediction_logs.p7_parts_demand` — captured correctly today, nothing reads it back out. Highest-value next step: a scheduled weekly batch job aggregating the already-logged `_feedback` blocks, recomputing (1) the flagging threshold (currently over-sensitive, recalibrate against accumulated false-positive rate) and (2) per-consumable Croston α, refit against logged predicted-vs-actual deltas. Needs its own before/after precision-recall check on a held-back slice of the feedback log so recalibration can't silently make over-flagging worse — doesn't need the accept-gate machinery proposed for P1-P6 (it's parameter tuning, not a model swap). Trigger: scheduled weekly batch (intervention-completion events arrive continuously but in small increments — batching avoids recalibrating on every single closed WO).

### 8. Expected Impact
Consistent with the stale 12%/100% (massive over-flagging, consistent with an uncalibrated decay shape/threshold, not "bad training" — there's no training to be bad). **80–90% precision is not realistic** until P2 and P3 both land real labels AND P7's own formula constants are separately calibrated against real stockout/consumption outcomes — explicitly sequenced, cannot be parallelized away. Realistic sequencing-adjusted target: once P2/P3 real-label fixes land and formula recalibration follows, 60–75% precision at reasonable recall is a defensible medium-term goal.

### 9. Implementation Priority
**Medium** — the weekly recalibration job (using data already being logged) is a cheap, immediate win independent of P2/P3 timing; the bigger precision jump is gated behind those two models and shouldn't be over-promised on its own timeline.

---

## Master Roadmap

### Phase 1 — Critical Fixes
**Objective:** Close the gap between "proven working in running containers" and "actually in git and in the Docker images" before the next restart silently reverts working fixes — the single most urgent operational risk, ahead of any modeling work.

| Task | Effort | Dependency |
|---|---|---|
| Bake the 9 `docker cp`'d backend fixes into the Docker image (`docker compose build backend` + recreate), re-verify each of the 9 behaviors post-recreate | 0.5–1 day | None — do first |
| Commit the `docker-compose.yml` `:ro`→rw volume-mount change + all `.py` fixes on branch `Phase_2`, as reviewable separate commit(s) | 0.5 day | Prior task verified |
| Resolve the P4 `_v1`/`_v2` pkl filename mismatch (`model_registry.py` line 56 vs. `ml_retraining.py` line 52) — repoint retrain path to the v2 filename the registry/frontend assumes; add a startup assertion that the two constants match | 0.5 day | None, parallel to above |
| Formalize a regressor accept-gate (today only classifiers enforce `min_f1>=0.70`; regressors compute `val_r2` but have no documented, deliberately-chosen threshold) — set P3's floor near its validated 67% (e.g. reject <0.60 on group-holdout), mark P6 explicitly "gate not applicable / hard-skipped" rather than silently unconfigured | 0.5–1 day | None, parallel to above |

**Expected gains:** eliminates the biggest live operational risk (fixes existing only in container memory — already lost a CSV twice across plain restarts); makes P4 retraining functional instead of writing to a file nobody reads; brings regressor deploy safety to parity with the classifier gate.

### Phase 2 — Data Collection
**Objective:** Replace tautological labels (P1, P5, and the tool_wear-threshold classes in P2) with real, business/outcome-decoupled ground truth — the root blocker is categorical, not volume. Stand up the structured ground-truth tables that don't exist today.

| Task | Models | Effort | Dependency |
|---|---|---|---|
| `failure_events` table + technician-confirmed failure tagging at WO closure | P1, P2 | 1–2 weeks dev + ongoing collection | Schema change only |
| Structured `failure_type` enum + root-cause coding taxonomy at WO closure | P2 | 1 week dev | Above |
| Persist `stock_movements` ledger from existing `StockService` calls | P7 | 2–3 weeks dev | None — hooks into existing service |
| Real dispatcher `priority_assigned` field + context (line criticality, parts availability, concurrent WO count) | P5 | 1 week dev + workflow rollout | Triage-screen UI change |
| `date_realisee` + `schedule_outcome` tag on maintenance-planning table | P6 | 1 week dev | Schema change only |
| `anomaly_events` adjudication log + lightweight technician review UI | P4 (eval only) | 1 week dev + 3–6 months passive collection | Phase 1's P4 pkl-path fix must land first |
| Periodic job consuming `ml_prediction_logs.p7_parts_demand` into an accuracy report | P7 | 3–5 days | Existing hook already logs, no schema change |
| Real-data accumulation window | P1, P2, P5, P6, P7-eval | 6–12 months calendar (passive) | Above tasks shipped |
| Extend P3 real run-to-failure coverage to 15–20 machines | P3 | Ongoing, 12+ months | None — highest-confidence, start immediately |

**Note:** schema/workflow tasks ship within a sprint, but resulting accuracy gains are calendar-gated (real events accruing under live operation), not engineering-effort-gated — set stakeholder expectations accordingly.

### Phase 3 — Feature Engineering
**Objective:** capture real, additive signal where it exists (P3, P4, P2 minority handling, P7 forecast inputs); explicitly decline to spend effort where feature engineering cannot address the underlying problem (P1/P5 tautology, P6 frozen/unlabeled state).

| Task | Effort | Dependency |
|---|---|---|
| P3: wear velocity/acceleration, rolling stats, cycles-since-maintenance, per-machine baseline | 3–5 days | Confirm maintenance-event timestamps joinable (0.5-day audit) |
| P4: rolling stats + rate-of-change of the 5 sensors; per-machine baseline replacing pooled `training_stats` | 2–3 days | None; benefit measurable only via Phase 5's proxy-label backtest |
| P2: class-weighting/SMOTE-NC for minority classes; `tool_wear × torque` interaction (flagged leak-adjacent) | 2 days | None |
| P7: maintenance-calendar-aligned Croston buckets, lead-time-adjusted stock-coverage feature | 2 days | Soft dependency on P2/P3 fixes for full ROI |
| P1/P5 | **Explicitly deferred** — no feature work beyond the ablation-test diagnostic | — | Blocked on labeling decision (Phase 2/4) |
| P6 | **No feature work this phase** | — | Blocked on Phase 2 schema instrumentation |

**Total:** ~10–13 engineer-days (excluding deferred work). **Expected gains:** P3 plausibly R² 67%→mid-70s (highest-confidence gain, real signal); P4 qualitatively fewer false spike-flags, measurable only after Phase 5's backtest; P2 minority F1 rises off the 0%/11% floor but may still not clear the 70% gate on ~240 rows alone — more data may still be required; P1/P5 zero expected change by design, any observed movement is noise or leak-amplification.

### Phase 4 — Model Redesign
**Objective:** stop reporting fabricated accuracy (P1/P2/P5) as real; extend P3 without regressing it; close the P4 deployment gap and stand up outcome-tracking; explicitly mark P6 unverified; make P7 a calibrated formula instead of an 8x-over-flagging black box.

| Sub-phase | Task | Effort | Dependency |
|---|---|---|---|
| 4.1 Reporting hygiene | Repeated group-holdout (mean±std, ≥5 runs) for P2/P5; "validation status" metadata flag (`leaked`/`unverified`/`group-holdout-validated`) per model in `model_registry.py` | 2–3 days | None — do first, prerequisite for every later number to mean anything |
| 4.2 P3 uncertainty | Quantile/pinball-loss heads on `XGBRegressor`; prototype Cox PH/Weibull AFT with explicit censoring, compare C-index vs. baseline under existing group-holdout | 5–8 days | None — start immediately |
| 4.3 P4 integrity + tracking | Install TensorFlow, re-enable Autoencoder; extend `p7_feedback.py` pattern to log whether a WO followed a P4 flag within N days | 3–5 days | None — start immediately |
| 4.4 P1/P2/P5 real-label migration | Retrain P1 on real failure-within-horizon labels + isotonic calibration; retrain P2 with class-weighting + threshold tuning on real failure-mode labels; retrain P5 on real triage-order/outcome labels; add monotonic constraints on tool_wear | 8–12 days once data available | **Hard-blocked** on Phase 2's real-label data |
| 4.5 P7 formula calibration | Grid-search Croston α per part-class; refit survival-decay shape against real censored data; recalibrate urgency/shortfall thresholds | 4–6 days | **Hard-blocked** on 4.4 (P2/P3 real labels) and Phase 2's parts-ledger data |
| 4.6 P6 status correction | No modeling — UI/metadata label "not yet validated," keep existing hard-skip as-is | <1 day | None — do alongside 4.1 |

**Portfolio-level verdict:** only P3 has a credible path to strong performance (C-index 0.75–0.85+) without a fundamental data-sourcing change. P1/P2/P5 cannot reach 80–90% through any modeling change — the ceiling is fully controlled by whether real outcome data materializes. P4 has no accuracy number until outcome tracking exists. P6 has no verification mechanism at all today. P7 is capped by P2/P3 and can't be fixed in isolation.

### Phase 5 — Validation Improvements
**Objective:** separate leakage from small-sample noise via ablation tests and LOMO-CV; upgrade single-machine holdout to LOMO-CV with mean±std reporting; build proxy-label backtesting for P4/P7; rationalize P3's R² gate against measured variance; add model-specific metrics (calibration for P1, per-class recall for P2, quantile coverage for P3, precision/recall@k for P4/P7).

| Task | Effort | Dependency |
|---|---|---|
| Feature-ablation diagnostic for P1 and P5 (drop `tool_wear`, reuse existing harness) | 1–2 days | None — highest-priority, lowest-cost task in the entire roadmap |
| LOMO-CV harness generalizing single-machine holdout, mean±std per model (P1, P2, P3, P5) | 3–4 days | Data-volume audit first (0.5 day) |
| Rationalize P3's `_MIN_REGRESSOR_R2` gate (0.40 → variance-informed, e.g. `mean − 1.5×std`) | 0.5 day | LOMO-CV task above |
| Calibration curve + Brier score for P1's probability output | 1 day | None |
| Quantile/prediction-interval estimation + coverage monitoring for P3 | 2–3 days | Feeds P3's explainability + P7's uncertainty propagation |
| P4 proxy-label backtest (join flagged cycles against `ordres_intervention` outcomes, precision/recall@k) | 2–3 days | Verify intervention timestamps joinable |
| P7 backtest harness decomposing error (P2-attributable vs. Croston vs. threshold-logic) | 3 days | Reuses P4 backtest's join pattern |
| P6 outcome-data instrumentation (suggested-vs-executed date, override reason) | 1–2 days build + indefinite wait | None — flagged as data-engineering work |
| Dashboard honesty pass: label P1/P5 "high but tautological," P6 "unverified," surface LOMO-CV std-dev everywhere | 1 day | Ablation + LOMO-CV tasks |

**Total:** ~15–19 engineer-days. **Expected outcome:** unlike Phase 3, most of this phase doesn't move accuracy numbers — it replaces unearned confidence with measured confidence (documented ablation proof, real confidence intervals, a functioning if imperfect feedback loop for P4/P7, an R² gate that actually enforces P3's demonstrated capability instead of a 0.40 floor that would pass almost any retrain).

### Phase 6 — Continuous Learning
**Objective:** mature retraining/feedback loops from manual-ad-hoc-sometimes-broken into per-model cadences matched to actual data maturity, using only what already exists in this stack (Docker Compose, the existing retrain endpoint, `ml_prediction_logs`) — no new algorithms, no Kubernetes.

| Task | Effort | Dependency |
|---|---|---|
| Lightweight scheduler (OS-level cron or a Compose sidecar hitting `POST /api/v1/ml/retrain`) — applied only to P3 (monthly / new-machine-lifecycle trigger) and P7's weekly recalibration | 1–2 days | Phase 1 complete |
| P2/P5 "N new labels available" counter surfaced on the ML dashboard, retrain stays manual-click | 1 day | Phase 2 label pipeline live |
| P7 recalibration batch job: aggregate `p7_feedback.py`'s logged comparisons, recompute threshold + Croston α, before/after precision-recall guard | 2–3 days | Phase 2's `stock_movements` ledger |
| Basic drift monitoring for P3/P4 (rolling sensor mean/std vs. training baseline) | 1–2 days | Phase 1's P4 fix |
| Extend `ml_prediction_logs`/`ShadowLogger` (currently P7-only) to P2, P3, P5 | 1–2 days | None — do before the "N new labels" counter, easiest computed from this table |

**Dependencies:** Phase 1 must complete first (P4 fix, committed volume mount, regressor gate are all prerequisites). **Expected gains:** P3 gets the scheduled cadence its 67% R² has earned; P7's already-collected feedback data finally closes the loop; P2/P5 retraining becomes visible and intentional; P3/P4 get early drift warning instead of silent degradation.

### Phase 7 — Production Monitoring
**Objective:** give every model a concrete tracked-signal set and alert thresholds, distinguishing models with a real accuracy metric (P2, P3, P5) from those that structurally can't have one (P1, P4) from disabled-pending-schema (P6) from recalibration-precision (P7) — extending the existing `ml_prediction_logs`/`ShadowLogger` pattern as the common backbone rather than inventing new logging.

| Model | What to track |
|---|---|
| P1 | Prediction-score distribution vs. `tool_wear` distribution (flags if label formula changes unnoticed); dashboard explicitly labeled "not independently validated" — no accuracy metric shown |
| P2 | `val_f1_macro` per retrain run as a trend line (not just pass/fail vs. 0.70); class-level prediction-distribution drift |
| P3 | `val_r2` per run against the Phase 1 floor, alert if a retrain lands below it; prediction-vs-actual RUL error on closed-out lifecycles via `ShadowLogger` |
| P4 | File-path health check (registry filename == retrain-output filename) as a standing assertion; sensor-drift %; anomaly-flag rate over time (a jump with no drift/retrain event is itself alertable) |
| P5 | F1 per run like P2, annotated with the known 81–88% noise band; alert only on retrains meaningfully outside that band |
| P6 | Visible "retraining disabled — no ground-truth signal" status (not silence); stale R² shown with an explicit "as of [date], unverified since" label |
| P7 | Precision/recall on the weekly recalibration cadence (before/after each run); raw over-flagging rate (12%/100% baseline) as the primary KPI to watch trend down |

**Cross-cutting:** extend `ml_prediction_logs`/`ShadowLogger` to persist predictions for P1–P6 (P7 already has it); one dashboard panel per model on `MLDashboard.tsx`/`ModelHealthTable.tsx`, clearly distinguishing metric categories so an XGBoost F1 and an anomaly flag-rate never look falsely comparable; alert thresholds (gate-failure alert extended to P3/P6 regressor gate; drift-% alert for P3/P4; P7 over-flagging alert if 3 consecutive recalibration cycles don't improve it — signals the approach, not just the parameters, needs review).

**Dependencies:** requires Phase 1's P4 fix + regressor gate, and Phase 6's `ShadowLogger` extension + P7 recalibration job. **Expected gains:** turns today's silent blind spots (P6 unmonitored, P4 zero metric) into explicitly-labeled, intentional states; every model gets a trend line instead of one pass/fail number; the next regression is visible on a dashboard instead of discovered via a support ticket.

---

## Agent Responsibility Map

| Role (as requested) | Mapped to | Deliverable |
|---|---|---|
| Data Engineering + Data Quality Agent | `senior-data-engineer` subagent | Dataset improvements (§3) per model, Phase 2 |
| Feature Engineering + Validation + Explainability/XAI Agent | `senior-data-scientist` subagent | Feature engineering (§4), validation (§6), XAI notes, Phase 3 + Phase 5 |
| ML Research + Model Training + Performance Optimization Agent | `senior-ml-engineer` subagent | Target state (§2), model improvements (§5), expected impact (§8), Phase 4 |
| MLOps Agent | `mlops-engineer` subagent | Retraining strategy (§7), Phase 1 + Phase 6 + Phase 7 |
| Orchestration, current-problem diagnosis (§1), priority calls (§9), synthesis | Main thread (grounded in this session's live code verification + prior debugging session) | This document |

---

## Session Traceability

Grounding facts verified by direct code read this session (not from memory alone):
- `app/ml-microservice/src/predictions.py` — confirmed 7-feature P1/P2/P3/P5/P6 input, 5-feature P4 input
- `app/backend/seed_ml_data_all.py` — confirmed exact tool_wear-threshold formulas for P1's `failure_prob` and P2's `failure_type` bands
- `app/backend/modules/ml/services/ml_retraining.py` — confirmed algorithms (XGBClassifier/XGBRegressor/RandomForestClassifier/IsolationForest), group-holdout mechanism (one `machine_id` held out), `min_f1=0.70` gate, P6 hard-skip, `_MIN_REGRESSOR_R2 = 0.40`
- `app/ml-microservice/src/p7_parts_demand.py` — confirmed deterministic survival + Croston pipeline, not a trained model
- `app/backend/modules/ml/services/model_registry.py` vs. `ml_retraining.py` — confirmed the P4 `_v1`/`_v2` pkl filename divergence
- `app/backend/modules/shared/maintenances_planifiees.py` — confirmed no actual/outcome date field exists today
- `app/backend/services/inventory/stock.py` — confirmed `StockService` tracks current quantity, not movement history
- `app/backend/modules/ml/services/p7_feedback.py` — confirmed write-only feedback logging, never consumed
