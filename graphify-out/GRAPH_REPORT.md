# Graph Report - .  (2026-07-22)

## Corpus Check
- 0 files · ~99,999 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6231 nodes · 14294 edges · 247 communities detected
- Extraction: 59% EXTRACTED · 41% INFERRED · 0% AMBIGUOUS · INFERRED: 5817 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Utilisateurs` - 494 edges
2. `Machines` - 335 edges
3. `UserRole` - 240 edges
4. `OrdresIntervention` - 201 edges
5. `OrdresTravail` - 192 edges
6. `PaginatedResponse` - 168 edges
7. `Alert` - 118 edges
8. `Piece` - 111 edges
9. `MlPredictionLog` - 102 edges
10. `NotificationsService` - 99 edges

## Surprising Connections (you probably didn't know these)
- `PDCA Pilot Target: Zone SMT (Surface-Mount Technology)` --semantically_similar_to--> `Zone CMS1 — Component Surface Mounting`  [INFERRED] [semantically similar]
  ML_Pipeline/2-PDCA_Action_Plan.md → Sagemcom Ezzahra - Production Zones Structure.pdf
- `P1: Binary Failure Prediction (XGBoost Classifier)` --semantically_similar_to--> `Machine: Four de Refusions (Reflow Oven)`  [INFERRED] [semantically similar]
  ML_Pipeline/1-Define_the_problem.md → Sagemcom Ezzahra - Production Zones Structure.pdf
- `Internal PostgreSQL EAM Database (machines, interventions, work_orders, plannings)` --semantically_similar_to--> `Sagemcom Ezzahra Production Zones Structure & Equipment`  [INFERRED] [semantically similar]
  ML_Pipeline/2-Collect_data.md → Sagemcom Ezzahra - Production Zones Structure.pdf
- `TC007: POST /api/v1/ml/retrain Trigger (Passed)` --references--> `ml_predictive.py (Active ML Service)`  [INFERRED]
  testsprite_tests/tmp/raw_report.md → app/backend/modules/ml/ml_predictive.py
- `P4 - Anomaly Detection (Isolation Forest)` --monitors--> `Zone CMS1 — Component Surface Mounting`  [INFERRED]
  testsprite_tests/tmp/prd_files/ML_PIPELINE_PLAN.md → Sagemcom Ezzahra - Production Zones Structure.pdf

## Hyperedges (group relationships)
- **Zone â†’ Sous-zone â†’ Ordre Validation Cascade** — template_check_eda32726_rule_zone, template_check_eda32726_rule_sous_zone, template_check_eda32726_rule_ordre [INFERRED 0.80]
- **CMS Line Ordre Numbering Scheme (shared 1-9 positions across lines)** — template_check_eda32726_cms_line1, template_check_eda32726_cms_line2, template_check_eda32726_rule_ordre [INFERRED 0.75]
- **Top-level vs Sous-zone Naming Collision for Test Zones** — template_check_eda32726_zone_test_fonctionnel, template_check_eda32726_zone_test_wifi, template_check_eda32726_test_fonctionnel_subzone, template_check_eda32726_test_wifi_subzone [INFERRED 0.40]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (152): fetchRequests(), handleValidate(), buildPageNumbers(), getPageNumbers(), getToken(), handleCreateWorkOrder(), handleDismiss(), load() (+144 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (598): _drift_rows(), get_ml_model_metrics(), get_retraining_stats(), Config, get_all_pending_requests(), _handle_itv_approved(), _handle_itv_rejected(), ItvRequestResponse (+590 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (300): Alertes_urgentes, AlertesUrgentes, ArchiveRule, ArchiveService — soft-archive lifecycle for date-based modules.  Modules cover, AuditActionType, AuditEntityType, AuditLog, AuditLogResponse (+292 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (288): AnomalyEnsemble, CUSUMDetector, fit_anomaly_ensemble(), Model E: Isolation Forest + CUSUM Control Chart Anomaly Ensemble Dual-gate: BOTH, Fit the ensemble on healthy (in-control) data.          Args:             X: (n_, Create fresh (zero-state) CUSUM detectors from stored baselines., Replay history observations through temp_cusums (mutates in place)., Score current observation x against per-feature CUSUM detectors. (+280 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (223): BaseModel, query_machiness(), Query machiness with filtering, sorting, and pagination, Query machiness with filtering, sorting, and pagination, List ChefOp's own intervention requests, _apply_filters(), _apply_sort(), get_machine_latest_telemetry() (+215 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (204): _enum_val(), _get_machine_ids(), get_planning_with_users(), get_user_by_id(), _load_users_from_db(), _load_users_preloaded(), Validate shift_type / chef_operation_id consistency for SHIFT plannings., Raise 404 if user not found, 400 if role mismatch. (+196 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (163): _autofit_columns(), _build_admin_export_flat_row(), export_work_order_report(), _fetch_consumed_summary(), _itv_str(), Export a complete Work Order report to Excel (horizontal format, analysis-ready), Export a complete Work Order report to Excel (horizontal format, analysis-ready), _fallback_plan() (+155 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (145): Config, create_access_token(), decode_access_token(), get_admin_user(), get_bearer_token(), get_current_user(), get_me(), login() (+137 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (168): 350-Line File Size Constraint, Active Pilot Phase (Weeks 4-8), AI4I 2020 Predictive Maintenance Dataset (Kaggle), AppRoutes.tsx (564 lines, to be split), Auto-Discovery via pkgutil.walk_packages, Backend Reorganization Implementation Plan, Backend Reorganization Implementation Plan, basic_machine_model.pkl — Saved P1 Model (+160 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (167): AI4I 2020 Predictive Maintenance Dataset, FastAPI Backend, basic_machine_model.pkl (Trained Random Forest), EAMSagemCom Agent Handoff Document, React + TypeScript + Vite Frontend, Groq Integration (Natural Language ML Explanations), HDF (Heat Dissipation Failure) — Top Predictor, healthScore.ts (Machine Health Score Utility) (+159 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (123): embed_batch(), embed_cache_stats(), embed_text(), get_embedder(), Embedding model singleton.  SentenceTransformer.encode() is synchronous — call v, Sync batch embed — run in thread pool, never call directly in async context., Async-safe batch embed. Runs sync encode in thread pool executor., Async-safe single text embed with in-memory TTL cache.      Cache key = raw text (+115 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (111): ChatMessage, ChatRequest, ChatResponse, ChatSessionSummary, CreateSessionRequest, Chat schemas for AI chat endpoint, Request to AI chat endpoint, Tool call requested by AI (+103 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (15): cleanUrl(), escape$1(), findClosingBracket(), _Hooks, indentCodeCompensation(), _Lexer, Marked, outputLink() (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (76): _apply_filters(), _apply_sort(), Config, create_maintenances_planifiees(), create_maintenances_planifieess_batch(), create_MaintenancesPlanifiees(), create_MaintenancesPlanifieess_batch(), delete_maintenances_planifiees() (+68 more)

### Community 14 - "Community 14"
Cohesion: 0.04
Nodes (80): _apply_filters(), _apply_sort(), check_and_send_due_reports(), _collect_recipients(), Config, create_rapports(), create_rapportss_batch(), delete_rapports() (+72 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (74): hybrid_enabled(), hybrid_stats(), keyword_search(), Phase 13.1 hybrid retrieval: keyword (Postgres FTS via two GENERATED tsvector co, Postgres FTS keyword search across content_tsv_fr + content_tsv_en.      Returns, Fuse two ranked lists by Reciprocal Rank Fusion (Cormack 2009).      Each input, Toggle: env HYBRID_ENABLED, default true., Update module-level counters after a hybrid query completes.      Args: (+66 more)

### Community 16 - "Community 16"
Cohesion: 0.03
Nodes (57): check_database_health(), _check_db_exist(), close_database(), DatabaseManager, get_db(), initialize_database(), Ensure QueuePool settings are applied when not in Lambda environment., When Lambda detection is enabled, engine uses NullPool. (+49 more)

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (51): BucketInfo, BucketListResponse, BucketRequest, BucketResponse, delete_object(), DeleteResponse, download_file(), FileUpDownRequest (+43 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (53): _apply_filters(), _apply_sort(), Archives, ArchivesBatchCreateRequest, ArchivesBatchDeleteRequest, ArchivesBatchUpdateItem, ArchivesBatchUpdateRequest, ArchivesData (+45 more)

### Community 19 - "Community 19"
Cohesion: 0.03
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 0.1
Nodes (55): AIHubService, ChatMessage, ContentPartImage, ContentPartText, extract_error_message(), _extract_image_ref(), _filename_from_content_type(), generate_image() (+47 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (61): _dispatch_route(), format_traceback(), get_backend_app(), get_mangum_handler(), get_mangum_handler_sync(), handle_backend_request_sync(), handle_config_request(), initialize_dynamic_routes() (+53 more)

### Community 22 - "Community 22"
Cohesion: 0.05
Nodes (49): _apply_filters(), _apply_sort(), Config, create_ordress_batch(), delete_ordres(), delete_ordress_batch(), get_ordres(), Ordres (+41 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (26): Enum, AutoIntEnum, AutoStrEnum, Enhanced Enum classes with automatic type conversion support. This module provi, Enhanced string enum that automatically converts to string value.      This en, Return the string value of the enum., Return a string representation of the enum., Enhanced integer enum that automatically converts to integer value.      This (+18 more)

### Community 24 - "Machine Zone Import Templates"
Cohesion: 0.06
Nodes (46): Atelier 1 (Emplacement), CMS (Machine Type), Ligne 1 (Example Sous-zone), Machine-XYZ (Example Row), Machines Import Sheet, Zone A (Example Zone), Machine AOI 3D (Final Inspection), AttÃ©nuateurs (30dB, 6dB, 3dB) (+38 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (22): get_ml_predictions(), get_model_metrics(), is_ml_service_available(), MLClient, ML Client - Backend client for ML microservice Calls ML predictions from the se, P2: Predict specific failure types., P3: Predict Remaining Useful Life., P5: Predict work order priority. (+14 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (37): _extract(), _extract_model(), get_all_models_status(), get_model(), _load(), load_p1(), load_p2(), load_p3() (+29 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (23): NamedTuple, Finding, main(), _map_npm_severity(), _map_zap_severity(), parse_gitleaks(), parse_pip_audit(), parse_pnpm_audit() (+15 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (18): _apply_filters(), _apply_sort(), Planning_ordres_travail, Planning_ordres_travailService, PlanningOrdresTravailService, Delete planning_ordres_travail, Delete planning_OrdresTravail, Get planning_ordres_travail by any field (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (17): _apply_filters(), _apply_sort(), Ordres_interventionService, OrdresInterventionService, Delete ordres_intervention, Delete OrdresIntervention, Get ordres_intervention by any field, Get OrdresIntervention by any field (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.06
Nodes (11): make_chunk(), Unit tests — RAG prompt injection and priority behavior.  Covers:   - build_r, RAG + memories both present — no crash, both injected., Verify that when RAG context is present, the system prompt     contains explici, The instruction must clearly tell the LLM to skip tool calls         when docum, LLM should be told to cite the document filename in its response., The 'INSTRUCTION CRITIQUE' label makes priority unambiguous to LLM., Critical: LLM must be told to use docs before calling tools. (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (20): check_drift(), _compute_psi(), DriftDetector, get_drift_status(), Drift Detector Statistical drift detection using Kolmogorov-Smirnov test + Popu, Load persisted baseline from disk if available., Add one observation to the reference (baseline) window., Add one observation to the current (production) window. (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.1
Nodes (21): check_sync(), _file_hash(), get_model_info(), _headline_metric(), list_model_versions(), _load_metrics(), ModelRegistry, Model Registry Track ML model versions and metadata (+13 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (17): clear_prediction_cache(), get_cached_prediction(), TTL Cache for ML Predictions In-memory cache with time-to-live expiration and b, Get cached prediction if available.      Args:         telemetry: Dict with a, Cache a prediction.      Args:         telemetry: Input telemetry         pr, Clear all cached predictions., In-memory cache with TTL expiration and _MAX_ENTRIES bound., Args:             ttl_seconds: Time-to-live in seconds (default: 5 minutes) (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.1
Nodes (15): BaseEstimator, build_feature_pipeline(), ClusterStateTransformer, InteractionFeatureTransformer, load_feature_pipeline(), Shared Feature Engineering Pipeline — V3 =======================================, Adds engineered interaction features between sensor readings.      Features adde, Adds K-Means machine state cluster_id as a feature.      Automatically selects o (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.12
Nodes (16): _build_drift_summary(), DriftMonitor, DriftReport, FeatureDriftResult, from_training_data(), Drift Monitor — V3 MLOps Layer ================================ Detects feature, Set expected anomaly rate from training (e.g. 0.034 = 3.4% failures)., Map KS p-value to drift severity label. (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.11
Nodes (24): _bpa_to_score(), _bpa_to_verdict(), _combine_all_bpas(), _combine_bpa_pair(), _conflict_mass(), _dempster_combine(), get_dst_fusion(), _intersect_label() (+16 more)

### Community 37 - "Community 37"
Cohesion: 0.11
Nodes (24): _check_name_uniqueness(), _clean_dataframe(), download_import_template(), _extract_row_fields(), preview_machine_import(), _process_row(), Run all field validations; return (valid, errors)., Generate/standardise name; return (final_name, warnings, valid, errors). (+16 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (18): _estimate_cadence_days(), get_moment_anomaly_detector(), get_moment_rul_estimator(), _logs_to_tensor(), MOMENTAnomalyDetector, MOMENTRULEstimator, _normalise(), Model M: MOMENT Foundation Model for Time Series Wraps AutonLab/MOMENT-1-large (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (14): fetch_hotspots(), fetch_issues(), _get(), main(), _print_dashboard_fallback(), print_report(), Print dashboard URL when the API call fails (e.g. wrong token type)., Read .scannerwork/report-task.txt produced by sonar-scanner. (+6 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (16): ConnectionManager, WebSocket Manager for real-time notifications, Manages WebSocket connections for real-time notifications, Manages WebSocket connections for real-time notifications, Accept a new WebSocket connection, Accept a new WebSocket connection, Remove a WebSocket connection, Remove a WebSocket connection (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (14): dt(), make_planning(), Unit tests — validate_task_dates logic in planning/taches.py  Tests the pure d, Off-by-one at minute granularity on end., Return a minimal planning-like object with date_debut / date_fin., Happy path — task fully inside planning window., Task start == planning start is allowed., Task end == planning end is allowed. (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.11
Nodes (13): verify_cheftech_only(), _apply_intervention_dates(), create_intervention_request(), get_interventions(), get_my_intervention_requests(), _notify_status_change(), _propagate_wo_status(), ChefOp requests an intervention (PDS) (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.13
Nodes (21): _delete_existing(), delete_row(), delete_stale_docs(), fetch_rows(), _fmt_alerte(), _fmt_dt(), _fmt_machine(), _fmt_maintenance_planifiee() (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.1
Nodes (21): close_OrdresTravail(), complete_validation_OrdresIntervention(), concordance_index_score(), ordinal_mae(), Shared Validation Utilities — V3 ================================== Custom score, Close a Work Order (ADMIN only), MAE on ordinal class indices.     Priority: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3., Validate or reject a Work Order (CHEFTECH only) (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (21): build_full_system_prompt(), build_memory_context(), build_ml_context(), build_rag_context(), build_sensor_status(), format_response_for_user(), format_tool_result(), get_system_prompt() (+13 more)

### Community 46 - "Community 46"
Cohesion: 0.1
Nodes (2): handleOptimize(), token()

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (12): check_rate_limit(), get_rate_status(), RateLimiter, Rate Limiter for ML API Simple in-memory rate limiting by client IP, Check rate limit for request.          Args:         request: FastAPI Request, Get current rate limit status., Simple rate limiter using sliding window., Args:             max_requests: Maximum requests allowed in window (+4 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (16): build_object_key(), delete_object(), _ensure_bucket(), _get_minio_client(), get_object_bytes(), list_bucket_objects(), presigned_download_url(), RAG document storage on MinIO/S3 (bucket: rag-docs).  Server-side upload/downl (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.12
Nodes (4): Second call returns same object without re-reading disk., startup_check() must not raise even if all models are missing., test_load_p1_cache_hit(), test_startup_check_runs_without_exception()

### Community 50 - "Community 50"
Cohesion: 0.22
Nodes (14): _autofit_columns(), _build_export_flat_row(), _build_wo_row(), _calc_duration(), export_cheftech_work_order_report(), _fetch_consumed_summary(), _itv_attr(), _itv_str() (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (1): T27 — P7 feedback pure-function tests (no DB, no async).

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (14): Archive, ContratIntervention, Machine, MaintenancePlanNee, Ordre, OrdreTravail, Planning, Priorite (enum) (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.19
Nodes (13): cache_key(), compute_facts(), facts_hash(), make_briefing(), _prune_stale(), Dashboard AI briefing — role-scoped facts, daily in-memory cache, LLM phrasing, Cache-first orchestration. Returns {"text", "generated_at", "source"}.     sour, Material facts that drive the briefing. Sync + pure -> unit-testable.      deg (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.19
Nodes (13): asyncpg PostgreSQL Driver, INSERT INTO plannings SQL Statement, Create Planning Operation, Plannings Database Table, shift_type Column (Missing), SQLAlchemy ProgrammingError - Missing shift_type Column, API Client Tool (Insomnia/Postman-like), Authentication Type Dropdown Menu (+5 more)

### Community 55 - "Community 55"
Cohesion: 0.29
Nodes (12): discover_machine(), _grounding_hits(), layer1_stack_health(), layer2_bridge(), layer3_degradation(), login(), main(), Smoke test: ML <-> RAG chat bridge.  Spec: docs/superpowers/specs/2026-06-12-m (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.15
Nodes (1): Quick Action pure-helper tests (no DB, no async).

### Community 57 - "Community 57"
Cohesion: 0.15
Nodes (1): T21/T22 — readiness score + timeline pure-function tests.

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (8): Send email notification that account has been approved, Send email notification that account has been approved, Send email notification that account has been rejected, Send email notification that account has been rejected, Send an email          Args:             to_email: Recipient email address, Send an email                  Args:             to_email: Recipient email ad, Send email notification that registration is pending approval, Send email notification that registration is pending approval

### Community 59 - "Community 59"
Cohesion: 0.2
Nodes (11): build_parts_demand(), croston_forecast(), p_fail_within(), Expected demand per piece_id from condition signals.     demand = sum_ft [ ft_pr, Croston intermittent-demand per-period forecast (size / interval)., Days of runway on_hand actually covers at the expected burn rate over     the ho, P(failure within `horizon` days) given remaining useful life.     Exponential mo, Merge survival + consumable demand, join stock, compute shortfall/order/urgency. (+3 more)

### Community 60 - "Community 60"
Cohesion: 0.29
Nodes (10): _load_config(), Integration test for the final .gitlab-ci.yml: verifies stage order, allow_failu, test_all_scan_jobs_reference_security_report_or_sonar_report(), test_build_images_stays_blocking(), test_license_scan_jobs_are_in_sca_deps_stage(), test_quality_gate_needs_includes_license_scan_optionally(), test_quality_gate_stays_blocking(), test_security_jobs_are_non_blocking() (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.35
Nodes (10): assertWithinBase(), escapeHtml(), formatDate(), generateListPage(), generateTOC(), getHtmlTemplate(), main(), parseFrontmatter() (+2 more)

### Community 62 - "Community 62"
Cohesion: 0.42
Nodes (8): banner(), err(), info(), main(), ok(), reset_minio(), reset_postgres(), warn()

### Community 63 - "Community 63"
Cohesion: 0.18
Nodes (1): T11 — parts_alerts pure-function tests (no DB, no async). Tests extract_shortage

### Community 64 - "Community 64"
Cohesion: 0.25
Nodes (6): _piece(), Quick Action plan-builder tests (pure, no DB)., test_bad_piece_id_falls_through_to_reference(), test_resolve_by_name_case_insensitive(), test_resolve_by_piece_id_existing(), test_skip_when_stock_already_covers_target()

### Community 65 - "Community 65"
Cohesion: 0.18
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 0.31
Nodes (9): _check_admin_guard(), _login(), main(), _parse_json_resp(), Live smoke for Quick Action. Runs against the running stack (backend:8000).  V, Stable JSON string of all stock rows — used to assert dry_run writes nothing., Return parsed JSON body if response is JSON content-type, else empty dict., Verify non-ADMIN gets HTTP 403. Skips quietly when TECH creds are not set. (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.33
Nodes (7): _facts(), test_compute_facts_shape(), test_hash_stable_and_sensitive(), test_make_briefing_falls_back_to_template_and_does_not_cache(), test_make_briefing_uses_llm_then_caches(), test_template_is_nonempty_and_mentions_counts(), test_whitespace_llm_falls_back_to_template()

### Community 68 - "Community 68"
Cohesion: 0.2
Nodes (1): T18 — parts_drafts pure-function tests (no DB, no async).

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (7): make_reading(), test_build_5_correct_order(), test_build_5_returns_5_features(), test_build_7_contains_build_5_prefix(), test_build_7_returns_7_features(), test_build_7_rpm_torque_correct(), test_build_7_temp_delta_correct()

### Community 70 - "Community 70"
Cohesion: 0.22
Nodes (0): 

### Community 71 - "ZAP DAST Metrics Push"
Cohesion: 0.33
Nodes (8): build_metrics(), _label(), main(), _map_severity(), push(), HTTP POST metrics to Prometheus Pushgateway., Sanitize a string to be safe inside Prometheus label values., Convert ZAP JSON report → Prometheus text format.

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (7): downgrade(), Add cheftech_feedback column to OrdresTravail  Revision ID: a1b2c3d4e5f6 Revi, Add cheftech_feedback text column., Add cheftech_feedback text column., Remove cheftech_feedback column., Remove cheftech_feedback column., upgrade()

### Community 73 - "Community 73"
Cohesion: 0.25
Nodes (7): downgrade(), Standardize utilisateurs schema to use id, nom, email, mot_de_passe, role  Rev, Upgrade schema: standardize utilisateurs table., Upgrade schema: standardize utilisateurs table., Downgrade schema: restore old utilisateurs columns., Downgrade schema: restore old utilisateurs columns., upgrade()

### Community 74 - "Community 74"
Cohesion: 0.25
Nodes (7): downgrade(), Update OrdresTravail table for CHETOP functionality  Revision ID: update_Ordre, Update ordres_travail table to match CHETOP requirements, Update OrdresTravail table to match CHETOP requirements, Revert changes to ordres_travail table, Revert changes to OrdresTravail table, upgrade()

### Community 75 - "Community 75"
Cohesion: 0.36
Nodes (8): Installation Guide, JWT Authentication System (bcrypt + SQLite/PostgreSQL), POST /api/v1/auth/login Endpoint, Login.tsx (Tabbed Register/Login UI), GET /api/v1/auth/me Endpoint, JWT Authentication Migration Document, OIDC Removal Rationale, POST /api/v1/auth/register Endpoint

### Community 76 - "Community 76"
Cohesion: 0.36
Nodes (7): build_metrics(), _label(), main(), push(), HTTP POST metrics to Prometheus Pushgateway., Sanitize a string to be safe inside Prometheus label values., Convert Trivy JSON → Prometheus text format.

### Community 77 - "Community 77"
Cohesion: 0.25
Nodes (1): Pure, no-DB tests for the shared machine-status vocabulary.

### Community 78 - "Community 78"
Cohesion: 0.39
Nodes (7): _build_response(), T8 — Verify parts_demand is plumbed through unified-health response. Pure unit t, Mirrors the parts_demand extraction logic in backend ml/router.py     get_unifie, test_parts_demand_contract_shape(), test_parts_demand_none_when_fusion_result_is_none(), test_parts_demand_none_when_key_missing_from_fusion(), test_parts_demand_present_when_fusion_result_has_p7()

### Community 79 - "Community 79"
Cohesion: 0.39
Nodes (6): _FakeUser, Pure, no-DB tests — verify_cheftech_only is a plain sync function; calling it di, test_verify_cheftech_only_allows_cheftech(), test_verify_cheftech_only_rejects_admin(), test_verify_cheftech_only_rejects_chetop(), test_verify_cheftech_only_rejects_technicien()

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (6): _column_exists(), downgrade(), Add planning_id to intervention model for Phase 2  Revision ID: phase2_interve, Add planning_id column to link interventions to plannings., Remove planning_id column., upgrade()

### Community 81 - "Community 81"
Cohesion: 0.52
Nodes (5): collectAlertActions(), collectPmActions(), collectWorkOrderActions(), getMachineImpact(), rankNextBestActions()

### Community 82 - "Community 82"
Cohesion: 0.29
Nodes (0): 

### Community 83 - "Community 83"
Cohesion: 0.29
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 0.29
Nodes (1): Test suite for labor forecast service.

### Community 85 - "Community 85"
Cohesion: 0.29
Nodes (2): Ensure the model was trained on 7 features (guards against accidental retraining, TestMLPrediction

### Community 86 - "Community 86"
Cohesion: 0.29
Nodes (0): 

### Community 87 - "Community 87"
Cohesion: 0.47
Nodes (4): _column_exists(), Add PDCA ML prediction logs table and feedback columns  Revision ID: add_pdca_, _table_exists(), upgrade()

### Community 88 - "Community 88"
Cohesion: 0.33
Nodes (5): downgrade(), Bridge migration: fix_enhance_work_orders  Revision ID: fix_enhance_work_order, Bridge migration — intentional no-op, see module docstring., Bridge migration — intentional no-op, see module docstring., upgrade()

### Community 89 - "Community 89"
Cohesion: 0.47
Nodes (4): _column_exists(), _index_exists(), Add intervention approval workflow fields  Revision ID: interventions_approval, upgrade()

### Community 90 - "Community 90"
Cohesion: 0.47
Nodes (4): _column_exists(), _index_exists(), Phase 1: Work Orders & Interventions workflow  Revision ID: phase1_work_orders, upgrade()

### Community 91 - "Community 91"
Cohesion: 0.47
Nodes (4): _index_exists(), Add PlanningMachines table for multi-machine selection in planning  Revision I, _table_exists(), upgrade()

### Community 92 - "Community 92"
Cohesion: 0.53
Nodes (5): decrypt_text(), _derive_fernet_key(), encrypt_text(), _get_fernet(), Derive a valid Fernet key from arbitrary string using SHA-256 and urlsafe base64

### Community 93 - "Community 93"
Cohesion: 0.4
Nodes (3): DummyIntervention, DummyMachine, test_fleet_dashboard_caching()

### Community 94 - "Community 94"
Cohesion: 0.6
Nodes (5): downgrade(), _index_exists(), Add PlanningTaches table for CHEFTECH execution tasks  Revision ID: add_Planni, _table_exists(), upgrade()

### Community 95 - "Community 95"
Cohesion: 0.33
Nodes (5): downgrade(), Merge heads and fix telemetry old columns  Revision ID: merge_and_fix_telemetr, Merge migration — joins branches, no schema changes., Merge migration — joins branches, no schema changes., upgrade()

### Community 96 - "Community 96"
Cohesion: 0.53
Nodes (5): add_rul(), drop_constant_sensors(), load_raw(), main(), P3 "practice test" on NASA CMAPSS (FD001) — NOT Sagemcom data, NOT production.

### Community 97 - "Community 97"
Cohesion: 0.4
Nodes (3): DummyIntervention, DummyMachine, test_fleet_dashboard_caching()

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (0): 

### Community 99 - "Community 99"
Cohesion: 0.33
Nodes (1): Verifies the .gitlab-ci.yml branch-rules anchor matches the intended branch nami

### Community 100 - "Community 100"
Cohesion: 0.5
Nodes (3): MockMachine, Verification script for P3 RUL Estimation. Tests the MachineLearningService int, test_rul_prediction()

### Community 101 - "Community 101"
Cohesion: 0.5
Nodes (3): _column_exists(), Add machine telemetry sensor columns  Revision ID: add_machine_telemetry_colum, upgrade()

### Community 102 - "Community 102"
Cohesion: 0.5
Nodes (3): _column_exists(), add_timer_started_at_to_ot  Revision ID: b7c8d9e0f1a3 Revises: a1b2c3d4e5f6, upgrade()

### Community 103 - "Community 103"
Cohesion: 0.5
Nodes (4): generate_machine_name(), Generate the standardized machine name matching frontend logic., Generate the standardized machine name matching frontend logic., _short_machine_name()

### Community 104 - "Community 104"
Cohesion: 0.5
Nodes (3): MockMachine, Verification Script for P4 Anomaly Detection Tests the integration of P4 model, test_p4_scenarios()

### Community 105 - "Community 105"
Cohesion: 0.5
Nodes (3): MockMachine, Verification Script for P5 Priority Prediction Tests the integration of P5 mode, test_p5_scenarios()

### Community 106 - "Community 106"
Cohesion: 0.4
Nodes (1): TestMLPrediction

### Community 107 - "Community 107"
Cohesion: 0.5
Nodes (3): _column_exists(), Add health score snapshot columns to OrdresTravail  Adds two nullable Float colu, upgrade()

### Community 108 - "Community 108"
Cohesion: 0.5
Nodes (3): _column_exists(), Add statut to PlanningTaches and planning_tache_id to OrdresIntervention  Revi, upgrade()

### Community 109 - "Community 109"
Cohesion: 0.5
Nodes (3): _column_exists(), Add content_hash and version columns to documents for dedup support.  content_, upgrade()

### Community 110 - "Community 110"
Cohesion: 0.5
Nodes (3): Create machine_status_change_requests table  Revision ID: machine_status_change_, _table_exists(), upgrade()

### Community 111 - "Community 111"
Cohesion: 0.5
Nodes (3): _column_exists(), Add is_synthetic flag to OrdresIntervention to quarantine seed-generated rows  R, upgrade()

### Community 112 - "Community 112"
Cohesion: 0.5
Nodes (3): _column_exists(), Add P4 anomaly-flag adjudication columns to ml_prediction_logs  Revision ID: p4_, upgrade()

### Community 113 - "Community 113"
Cohesion: 0.5
Nodes (3): _column_exists(), Add P4 flag-to-outcome tracking column to ml_prediction_logs  Revision ID: p4_wo, upgrade()

### Community 114 - "Community 114"
Cohesion: 0.5
Nodes (3): _column_exists(), Add p7_parts_demand JSON column to ml_prediction_logs  Revision ID: p7_parts_dem, upgrade()

### Community 115 - "Community 115"
Cohesion: 0.5
Nodes (3): Create quick_action_runs idempotency table  Revision ID: quick_action_runs Re, _table_exists(), upgrade()

### Community 116 - "Community 116"
Cohesion: 0.5
Nodes (3): _column_exists(), Add s3_object_key column to documents table for RAG file storage in MinIO/S3, upgrade()

### Community 117 - "Community 117"
Cohesion: 0.6
Nodes (4): _col_exists(), downgrade(), Rename machine_telemetry_logs columns and drop machines telemetry columns  Rev, upgrade()

### Community 118 - "Community 118"
Cohesion: 0.5
Nodes (3): _column_exists(), Extend is_synthetic quarantine to machine_telemetry_logs and ml_prediction_logs, upgrade()

### Community 119 - "Community 119"
Cohesion: 0.4
Nodes (1): T10 — PARTS_SHORTAGE alert type exists in AlertType enum.

### Community 120 - "Community 120"
Cohesion: 0.4
Nodes (1): Pure test: pydantic validation only.

### Community 121 - "Community 121"
Cohesion: 0.4
Nodes (0): 

### Community 122 - "Community 122"
Cohesion: 0.7
Nodes (4): test_hash_mismatch_flagged(), test_identical_files_match(), test_missing_in_microservice(), _write()

### Community 123 - "Community 123"
Cohesion: 0.4
Nodes (0): 

### Community 124 - "Community 124"
Cohesion: 0.5
Nodes (1): Make ordre_travail_id nullable  Revision ID: 55c181562e1e Revises: be6721db28

### Community 125 - "Community 125"
Cohesion: 0.5
Nodes (1): Add sous_zone and ordre to plannings  Revision ID: add_granular_planning_field

### Community 126 - "Community 126"
Cohesion: 0.5
Nodes (1): add more performance indexes for machines and related tables  Revision ID: mor

### Community 127 - "Community 127"
Cohesion: 0.5
Nodes (1): add performance indexes  Revision ID: new_perf_indexes Revises: 55c181562e1e

### Community 128 - "Community 128"
Cohesion: 0.5
Nodes (1): add PlanningMachines machine_id index  Revision ID: add_plannings_idx Revises

### Community 129 - "Community 129"
Cohesion: 0.5
Nodes (1): Add requested_by column to OrdresIntervention  Revision ID: add_requested_by

### Community 130 - "Community 130"
Cohesion: 0.5
Nodes (1): add status and shift type to utilisateurs  Revision ID: b9e76d0812f5 Revises:

### Community 131 - "Community 131"
Cohesion: 0.5
Nodes (1): merge multiple heads  Revision ID: be6721db2847 Revises: b9e76d0812f5, f44d6d

### Community 132 - "Community 132"
Cohesion: 0.5
Nodes (1): auto update  Revision ID: db0b16342160 Revises: Create Date: 2026-01-27 03:0

### Community 133 - "Community 133"
Cohesion: 0.5
Nodes (1): Add WorkOrder execution validation fields  Revision ID: e0fddb28a2cf Revises:

### Community 134 - "Community 134"
Cohesion: 0.5
Nodes (1): add_status_shift_type_to_utilisateurs  Revision ID: f44d6d0416f4 Revises: b7c

### Community 135 - "Community 135"
Cohesion: 0.5
Nodes (0): 

### Community 136 - "Community 136"
Cohesion: 0.5
Nodes (1): P1 — Failure Prediction (Optimized) Training script: XGBoost + SMOTE + 5-fold Gr

### Community 137 - "Community 137"
Cohesion: 0.5
Nodes (1): P5 — Work Order Priority Prediction (Optimized) Training script: XGBoost Classi

### Community 138 - "Community 138"
Cohesion: 0.5
Nodes (1): P6 — Maintenance Schedule Optimization (Optimized) Training script: XGBoost Regr

### Community 139 - "Community 139"
Cohesion: 0.5
Nodes (4): Build Error: Missing badges utility module, Frontend Build Error Log, Importer: AdminWorkOrdersList.tsx, Missing Module: src/modules/shared/utils/badges

### Community 140 - "Community 140"
Cohesion: 0.67
Nodes (4): Frontend Public Images Directory, Image Upload Icon, UI Asset - Image Upload Button, Upload Action

### Community 141 - "Community 141"
Cohesion: 0.5
Nodes (1): merge_phase2_and_base  Revision ID: 3d8edf736d26 Revises: add_ai_memories, ph

### Community 142 - "Community 142"
Cohesion: 0.5
Nodes (1): Add ai_memories table for dynamic LLM user memory  Revision ID: add_ai_memorie

### Community 143 - "Community 143"
Cohesion: 0.5
Nodes (1): Add chat_sessions table — DB-backed conversation history  Revision ID: add_cha

### Community 144 - "Community 144"
Cohesion: 0.5
Nodes (1): Stub migration: restore add_ml_alert_details revision  Revision ID: add_ml_ale

### Community 145 - "Community 145"
Cohesion: 0.5
Nodes (1): Enable pgvector and create RAG tables  Revision ID: add_pgvector_rag Revises:

### Community 146 - "Community 146"
Cohesion: 0.5
Nodes (1): Add title column to chat_sessions for multi-conversation support  Revision ID:

### Community 147 - "Community 147"
Cohesion: 0.5
Nodes (1): Phase 13.1 hybrid search — add two GENERATED tsvector columns + GIN indexes on d

### Community 148 - "Community 148"
Cohesion: 0.5
Nodes (1): Inventory consumption workflow — reservations, consumed pieces, pending pieces

### Community 149 - "Community 149"
Cohesion: 0.5
Nodes (1): Make stock.quantity DECIMAL(10,2) for consumable fractional units  Revision ID

### Community 150 - "Community 150"
Cohesion: 0.5
Nodes (1): Merge all dangling heads into a single clean tip  Revision ID: merge_all_heads

### Community 151 - "Community 151"
Cohesion: 0.5
Nodes (1): Universal soft-archive columns across date-based modules  Revision ID: univers

### Community 152 - "Community 152"
Cohesion: 0.5
Nodes (1): Upgrade doc_chunks embedding column from vector(384) to vector(1024) for BAAI/bg

### Community 153 - "Community 153"
Cohesion: 0.5
Nodes (3): forecast_budget(), Budget forecast — pure function. Labor + parts reorder cost., Pure function.     labor_cost = labor_demand_hours * labor_rate     parts_cost

### Community 154 - "Community 154"
Cohesion: 0.67
Nodes (3): compute_drift(), population_stability_index(), Drift detection over logged predictions — PSI + mean shift. Pure, stdlib only.

### Community 155 - "Community 155"
Cohesion: 0.5
Nodes (3): forecast_labor(), Labor demand/capacity forecast — pure function., Pure function to forecast labor demand vs capacity.      demand  = sum(expecte

### Community 156 - "Community 156"
Cohesion: 0.67
Nodes (3): build_dataset(), main(), Phase 4.2 prototype: Cox PH / Weibull AFT for P3 RUL, explicitly modeling right-

### Community 157 - "Community 157"
Cohesion: 0.5
Nodes (0): 

### Community 158 - "Community 158"
Cohesion: 0.5
Nodes (0): 

### Community 159 - "Community 159"
Cohesion: 0.5
Nodes (0): 

### Community 160 - "Community 160"
Cohesion: 0.67
Nodes (1): # NOTE: RAG sync is event-driven via SQLAlchemy after_commit hooks

### Community 161 - "Community 161"
Cohesion: 0.67
Nodes (0): 

### Community 162 - "Community 162"
Cohesion: 0.67
Nodes (0): 

### Community 163 - "Community 163"
Cohesion: 0.67
Nodes (1): P3 — RUL Estimation (Optimized) Training script: XGBoost Regressor with GridSear

### Community 164 - "Community 164"
Cohesion: 0.67
Nodes (1): Shared machine-status vocabulary.  Single source of truth for both Machines.stat

### Community 165 - "Community 165"
Cohesion: 0.67
Nodes (1): Deterministic guarded-retraining recommendation.

### Community 166 - "Community 166"
Cohesion: 0.67
Nodes (0): 

### Community 167 - "Community 167"
Cohesion: 1.0
Nodes (0): 

### Community 168 - "Community 168"
Cohesion: 1.0
Nodes (0): 

### Community 169 - "Community 169"
Cohesion: 1.0
Nodes (0): 

### Community 170 - "Community 170"
Cohesion: 1.0
Nodes (0): 

### Community 171 - "Community 171"
Cohesion: 1.0
Nodes (0): 

### Community 172 - "Community 172"
Cohesion: 1.0
Nodes (0): 

### Community 173 - "Community 173"
Cohesion: 1.0
Nodes (0): 

### Community 174 - "Community 174"
Cohesion: 1.0
Nodes (0): 

### Community 175 - "Community 175"
Cohesion: 1.0
Nodes (0): 

### Community 176 - "Community 176"
Cohesion: 1.0
Nodes (0): 

### Community 177 - "Community 177"
Cohesion: 1.0
Nodes (0): 

### Community 178 - "Community 178"
Cohesion: 1.0
Nodes (0): 

### Community 179 - "Community 179"
Cohesion: 1.0
Nodes (0): 

### Community 180 - "Community 180"
Cohesion: 1.0
Nodes (0): 

### Community 181 - "Community 181"
Cohesion: 1.0
Nodes (0): 

### Community 182 - "Community 182"
Cohesion: 1.0
Nodes (0): 

### Community 183 - "Community 183"
Cohesion: 1.0
Nodes (0): 

### Community 184 - "Community 184"
Cohesion: 1.0
Nodes (0): 

### Community 185 - "Community 185"
Cohesion: 1.0
Nodes (0): 

### Community 186 - "Community 186"
Cohesion: 1.0
Nodes (1): P2 — Failure Type Classification (Optimized) Training script: MultiOutputClassif

### Community 187 - "Community 187"
Cohesion: 1.0
Nodes (1): P4 — Anomaly Detection (Optimized) Training script: Isolation Forest with GridS

### Community 188 - "Community 188"
Cohesion: 1.0
Nodes (0): 

### Community 189 - "Community 189"
Cohesion: 1.0
Nodes (0): 

### Community 190 - "Community 190"
Cohesion: 1.0
Nodes (0): 

### Community 191 - "Community 191"
Cohesion: 1.0
Nodes (0): 

### Community 192 - "Community 192"
Cohesion: 1.0
Nodes (0): 

### Community 193 - "Community 193"
Cohesion: 1.0
Nodes (0): 

### Community 194 - "Community 194"
Cohesion: 1.0
Nodes (2): Frontend Dependency: axios, Frontend Requirements (axios)

### Community 195 - "Community 195"
Cohesion: 1.0
Nodes (1): CI gate: fail if the two model dirs diverge. Exit 1 on divergence, else 0.

### Community 196 - "Community 196"
Cohesion: 1.0
Nodes (0): 

### Community 197 - "Community 197"
Cohesion: 1.0
Nodes (1): One-shot patch: add rpm_torque auto-derivation to predict_priority.

### Community 198 - "Community 198"
Cohesion: 1.0
Nodes (1): Patch predictions.py: auto-derive missing features for P3/P4/P6.  P3 (RUL)

### Community 199 - "Community 199"
Cohesion: 1.0
Nodes (1): Patch router.py to handle numpy scalar serialization with pydantic + numpy 2.x.

### Community 200 - "Community 200"
Cohesion: 1.0
Nodes (0): 

### Community 201 - "Community 201"
Cohesion: 1.0
Nodes (0): 

### Community 202 - "Community 202"
Cohesion: 1.0
Nodes (0): 

### Community 203 - "Community 203"
Cohesion: 1.0
Nodes (0): 

### Community 204 - "Community 204"
Cohesion: 1.0
Nodes (0): 

### Community 205 - "Community 205"
Cohesion: 1.0
Nodes (0): 

### Community 206 - "Community 206"
Cohesion: 1.0
Nodes (1): Generate backend URL from host and port.

### Community 207 - "Community 207"
Cohesion: 1.0
Nodes (1): Handle missing enum values by trying to match against string values.         Th

### Community 208 - "Community 208"
Cohesion: 1.0
Nodes (1): Handle missing enum values by trying to match against integer values.         T

### Community 209 - "Community 209"
Cohesion: 1.0
Nodes (0): 

### Community 210 - "Community 210"
Cohesion: 1.0
Nodes (1): Generate SHAP explanations for a single prediction.                  Args:

### Community 211 - "Community 211"
Cohesion: 1.0
Nodes (1): Map dataset column names to user-friendly French labels.

### Community 212 - "Community 212"
Cohesion: 1.0
Nodes (1): Validate password requirements

### Community 213 - "Community 213"
Cohesion: 1.0
Nodes (1): Validate name is not empty

### Community 214 - "Community 214"
Cohesion: 1.0
Nodes (0): 

### Community 215 - "Community 215"
Cohesion: 1.0
Nodes (0): 

### Community 216 - "Community 216"
Cohesion: 1.0
Nodes (0): 

### Community 217 - "Community 217"
Cohesion: 1.0
Nodes (0): 

### Community 218 - "Community 218"
Cohesion: 1.0
Nodes (0): 

### Community 219 - "Community 219"
Cohesion: 1.0
Nodes (0): 

### Community 220 - "Community 220"
Cohesion: 1.0
Nodes (0): 

### Community 221 - "Community 221"
Cohesion: 1.0
Nodes (1): Favicon SVG — Sagemcom/EAM App Icon (White Stylized S-like Curve on Black Background, 16x16)

### Community 222 - "Community 222"
Cohesion: 1.0
Nodes (1): ITV Approval Bug (Not Converting to Work Order)

### Community 223 - "Community 223"
Cohesion: 1.0
Nodes (1): Chef d'Op ITV Request False Error Message

### Community 224 - "Community 224"
Cohesion: 1.0
Nodes (1): Deprecated Field 'Niveau de charge (%)' Removal

### Community 225 - "Community 225"
Cohesion: 1.0
Nodes (1): Design System Plan (Asana/Monday.com Style)

### Community 226 - "Community 226"
Cohesion: 1.0
Nodes (1): Database Schema Plan (All Tables)

### Community 227 - "Community 227"
Cohesion: 1.0
Nodes (1): Frontend Robots.txt

### Community 228 - "Community 228"
Cohesion: 1.0
Nodes (0): 

### Community 229 - "Community 229"
Cohesion: 1.0
Nodes (1): Generate backend URL from host and port.

### Community 230 - "Community 230"
Cohesion: 1.0
Nodes (1): Validate password requirements

### Community 231 - "Community 231"
Cohesion: 1.0
Nodes (1): Build human-readable drift summary string.

### Community 232 - "Community 232"
Cohesion: 1.0
Nodes (1): Factory method: create monitor from training data.          Args:             X_

### Community 233 - "Community 233"
Cohesion: 1.0
Nodes (1): Extract 5 features: [air, process, rpm, torque, wear]                  Args:

### Community 234 - "Community 234"
Cohesion: 1.0
Nodes (1): Extract 6 features with temp_delta.                  Args:             teleme

### Community 235 - "Community 235"
Cohesion: 1.0
Nodes (1): Validate and sanitize telemetry input.                  Args:             tel

### Community 236 - "Community 236"
Cohesion: 1.0
Nodes (1): Check if a value is in valid range.                  Args:             value:

### Community 237 - "Community 237"
Cohesion: 1.0
Nodes (1): Compute derived features from raw telemetry.                  Args:

### Community 238 - "Community 238"
Cohesion: 1.0
Nodes (1): Get feature names for each model.          Returns:             Dict mapping

### Community 239 - "Community 239"
Cohesion: 1.0
Nodes (1): Build a complete FeatureSnapshot dict from telemetry + optional context.

### Community 240 - "Community 240"
Cohesion: 1.0
Nodes (1): Build a time-ordered list of FeatureSnapshot dicts from prediction log entries.

### Community 241 - "Community 241"
Cohesion: 1.0
Nodes (1): Infer mean cadence (days) between log entries; default 1/24 (hourly).

### Community 242 - "Community 242"
Cohesion: 1.0
Nodes (1): Generate SHAP explanations for a single prediction.          Args:

### Community 243 - "Community 243"
Cohesion: 1.0
Nodes (1): Convenience wrapper: SHAP for P1 model using canonical 5-feature names.

### Community 244 - "Community 244"
Cohesion: 1.0
Nodes (1): Map dataset column names to user-friendly French labels.

### Community 245 - "Community 245"
Cohesion: 1.0
Nodes (1): 5 raw sensor features. Used by P3 and P4.

### Community 246 - "Community 246"
Cohesion: 1.0
Nodes (1): 7 features: 5 raw + temp_delta + rpm_torque. Used by P1, P2, P5, P6.

## Ambiguous Edges - Review These
- `Zone A (Example Zone)` → `ZONE CMS1 - COMPONENT SURFACE MOUNTING`  [AMBIGUOUS]
  graphify-out/converted/machines_import_template_4ba12002.md · relation: conceptually_related_to
- `ZONE TEST FONCTIONNEL` → `TEST FONCTIONNEL (Test de Fonctionnement) [sous-zone]`  [AMBIGUOUS]
  graphify-out/converted/template_check_eda32726.md · relation: conceptually_related_to
- `ZONE TEST WiFi` → `TEST WiFi (Test Sans Fil) [sous-zone]`  [AMBIGUOUS]
  graphify-out/converted/template_check_eda32726.md · relation: conceptually_related_to

## Knowledge Gaps
- **967 isolated node(s):** `Verification script for P3 RUL Estimation. Tests the MachineLearningService int`, `AWS Lambda handler for unified frontend and backend with Nginx reverse proxy Th`, `Format traceback with newlines replaced by '\\n' string literal`, `Initialize dynamic routes by scanning frontend dist directory`, `Initialize all services once for the Lambda function (equivalent to FastAPI life` (+962 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 167`** (2 nodes): `check_role_schema.py`, `check_schema()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 168`** (2 nodes): `check_zone_travail.py`, `check_zone_travail()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 169`** (2 nodes): `create_minio_bucket.py`, `create_bucket()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 170`** (2 nodes): `create_minio_bucket_manual.py`, `create_bucket_via_curl()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 171`** (2 nodes): `create_minio_bucket_mc.py`, `create_bucket_with_mc()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 172`** (2 nodes): `create_minio_bucket_mc_docker.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 173`** (2 nodes): `create_minio_bucket_mc_docker_fixed.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 174`** (2 nodes): `create_minio_bucket_mc_fixed2.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 175`** (2 nodes): `create_minio_bucket_mc_fixed3.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 176`** (2 nodes): `create_minio_bucket_simple.py`, `create_bucket()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 177`** (2 nodes): `create_tech_tables.py`, `create_tables()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 178`** (2 nodes): `fix_alembic.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 179`** (2 nodes): `inspect_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 180`** (2 nodes): `inspect_db_async.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 181`** (2 nodes): `planning_emails.py`, `send_planning_assignment_emails()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 182`** (2 nodes): `aspect-ratio.tsx`, `tailwind.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 183`** (2 nodes): `ChefTechMachinesHeader.tsx`, `ChefTechMachinesHeader()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 184`** (2 nodes): `index.ts`, `WelcomePage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 185`** (2 nodes): `predict_cli.py`, `predict_failure()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 186`** (2 nodes): `ml_train_p2.py`, `P2 — Failure Type Classification (Optimized) Training script: MultiOutputClassif`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 187`** (2 nodes): `ml_train_p4.py`, `P4 — Anomaly Detection (Optimized) Training script: Isolation Forest with GridS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 188`** (2 nodes): `test_failure_probability.py`, `test_failure_probability_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 189`** (2 nodes): `test_p2_failure_type.py`, `test_failure_type_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 190`** (2 nodes): `TC001_get_health_basic_check.py`, `test_get_health_basic_check()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 191`** (2 nodes): `TC002_get_api_v1_health_check_database_connected.py`, `test_get_api_v1_health_check_database_connected()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 192`** (2 nodes): `TC006_get_api_v1_ml_machines_machineid_prediction_success.py`, `test_get_api_v1_ml_machines_machineid_prediction_success()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 193`** (2 nodes): `TC007_post_api_v1_ml_retrain_trigger.py`, `test_post_api_v1_ml_retrain_trigger()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 194`** (2 nodes): `Frontend Dependency: axios`, `Frontend Requirements (axios)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 195`** (2 nodes): `check_model_sync.py`, `CI gate: fail if the two model dirs diverge. Exit 1 on divergence, else 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 196`** (2 nodes): `planning_tache_emails.py`, `send_task_assignment_email()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 197`** (2 nodes): `patch_predictions.py`, `One-shot patch: add rpm_torque auto-derivation to predict_priority.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 198`** (2 nodes): `patch_predictions2.py`, `Patch predictions.py: auto-derive missing features for P3/P4/P6.  P3 (RUL)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 199`** (2 nodes): `patch_router.py`, `Patch router.py to handle numpy scalar serialization with pydantic + numpy 2.x.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 200`** (2 nodes): `failure_probability.test.py`, `test_failure_probability_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 201`** (2 nodes): `p2_failure_type.test.py`, `test_failure_type_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 202`** (1 nodes): `analyze_zones.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 203`** (1 nodes): `check_migrations.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 204`** (1 nodes): `update_nb_p4.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 205`** (1 nodes): `write_migration.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 206`** (1 nodes): `Generate backend URL from host and port.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 207`** (1 nodes): `Handle missing enum values by trying to match against string values.         Th`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 208`** (1 nodes): `Handle missing enum values by trying to match against integer values.         T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 209`** (1 nodes): `piece_machine.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 210`** (1 nodes): `Generate SHAP explanations for a single prediction.                  Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 211`** (1 nodes): `Map dataset column names to user-friendly French labels.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 212`** (1 nodes): `Validate password requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 213`** (1 nodes): `Validate name is not empty`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 214`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 215`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 216`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 217`** (1 nodes): `build.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 218`** (1 nodes): `vite-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 219`** (1 nodes): `collapsible.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 220`** (1 nodes): `ml_eda.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 221`** (1 nodes): `Favicon SVG — Sagemcom/EAM App Icon (White Stylized S-like Curve on Black Background, 16x16)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 222`** (1 nodes): `ITV Approval Bug (Not Converting to Work Order)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 223`** (1 nodes): `Chef d'Op ITV Request False Error Message`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 224`** (1 nodes): `Deprecated Field 'Niveau de charge (%)' Removal`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 225`** (1 nodes): `Design System Plan (Asana/Monday.com Style)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 226`** (1 nodes): `Database Schema Plan (All Tables)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 227`** (1 nodes): `Frontend Robots.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 228`** (1 nodes): `mark_safe.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 229`** (1 nodes): `Generate backend URL from host and port.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 230`** (1 nodes): `Validate password requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 231`** (1 nodes): `Build human-readable drift summary string.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 232`** (1 nodes): `Factory method: create monitor from training data.          Args:             X_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 233`** (1 nodes): `Extract 5 features: [air, process, rpm, torque, wear]                  Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 234`** (1 nodes): `Extract 6 features with temp_delta.                  Args:             teleme`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 235`** (1 nodes): `Validate and sanitize telemetry input.                  Args:             tel`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 236`** (1 nodes): `Check if a value is in valid range.                  Args:             value:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 237`** (1 nodes): `Compute derived features from raw telemetry.                  Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 238`** (1 nodes): `Get feature names for each model.          Returns:             Dict mapping`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 239`** (1 nodes): `Build a complete FeatureSnapshot dict from telemetry + optional context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 240`** (1 nodes): `Build a time-ordered list of FeatureSnapshot dicts from prediction log entries.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 241`** (1 nodes): `Infer mean cadence (days) between log entries; default 1/24 (hourly).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 242`** (1 nodes): `Generate SHAP explanations for a single prediction.          Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 243`** (1 nodes): `Convenience wrapper: SHAP for P1 model using canonical 5-feature names.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 244`** (1 nodes): `Map dataset column names to user-friendly French labels.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 245`** (1 nodes): `5 raw sensor features. Used by P3 and P4.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 246`** (1 nodes): `7 features: 5 raw + temp_delta + rpm_torque. Used by P1, P2, P5, P6.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Zone A (Example Zone)` and `ZONE CMS1 - COMPONENT SURFACE MOUNTING`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `ZONE TEST FONCTIONNEL` and `TEST FONCTIONNEL (Test de Fonctionnement) [sous-zone]`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `ZONE TEST WiFi` and `TEST WiFi (Test Sans Fil) [sous-zone]`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Utilisateurs` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `Machines` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 37`, `Community 6`, `Community 14`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `services/inventory.py (350 lines, to be split)` connect `Community 8` to `Community 2`, `Community 5`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 489 inferred relationships involving `Utilisateurs` (e.g. with `Get a human-readable name for an entity` and `Process pending audit entries after flush`) actually correct?**
  _`Utilisateurs` has 489 INFERRED edges - model-reasoned connections that need verification._