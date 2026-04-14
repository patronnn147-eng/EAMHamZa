# Graph Report - .  (2026-04-13)

## Corpus Check
- Large corpus: 520 files · ~227,325 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 2622 nodes · 5454 edges · 125 communities detected
- Extraction: 69% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 1717 edges (avg confidence: 0.51)
- Token cost: 39,400 input · 11,800 output

## God Nodes (most connected - your core abstractions)
1. `Utilisateurs` - 164 edges
2. `Machines` - 121 edges
3. `UserRole` - 97 edges
4. `PaginatedResponse` - 83 edges
5. `Ordres_intervention` - 76 edges
6. `Ordres_travail` - 63 edges
7. `NotificationsService` - 55 edges
8. `UserResponse` - 48 edges
9. `RapportsService` - 48 edges
10. `Base` - 47 edges

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
- **6 ML Problems Traversing Full 8-Step Pipeline** — ml_pipeline_plan, ml_step1_define, ml_step2_collect, ml_step3_prepare, ml_step4_split, ml_step5_choose, ml_step6_train, ml_step7_evaluate, ml_step8_tune [EXTRACTED 1.00]
- **PDCA Deployment Cycle: Shadow → Active → KPI Audit → Act** — ml_pdca_plan, pdca_shadow_mode, pdca_active_mode, pdca_kpi_downtime, pdca_auto_order_generation [EXTRACTED 1.00]
- **Sagemcom CMS1 SMT Assembly Line Machines** — pdf_zone_cms1, pdf_cms_line1, pdf_machine_pose, pdf_machine_reflow, pdf_machine_aoi3d [EXTRACTED 1.00]
- **Core Work Order Management Classes** — class_diagram_Ordre, class_diagram_OrdreTravail, class_diagram_Machine, class_diagram_Utilisateur, class_diagram_Planning, class_diagram_Rapport [EXTRACTED 0.95]
- **Enumeration Types** — class_diagram_Priorite, class_diagram_TypePanning, class_diagram_TypeOrdre, class_diagram_Statut [EXTRACTED 1.00]
- **ML Prediction Pipeline (Dataset → Model → API → UI)** — agent_ai4i_dataset, agent_basic_model_pkl, agent_ml_router, agent_predictive_panel [EXTRACTED 0.95]
- **PDCA Continuous Improvement Cycle** — impl_pdca_plan_phase, impl_pdca_do_phase, impl_pdca_check_phase, impl_pdca_act_phase [EXTRACTED 1.00]
- **Technician Workflow System (Dashboard, WorkOrders, Interventions, Layout)** — tech_dashboard, tech_work_orders, tech_interventions, tech_layout [EXTRACTED 0.95]
- **Planning Creation INSERT Error Flow** — image1_planning_creation, image1_insert_statement, image1_plannings_table, image1_shift_type_column, image1_sqlalchemy_error, image1_asyncpg_driver [EXTRACTED 1.00]
- **API Client Authentication Configuration** — image2_api_client, image2_auth_panel, image2_auth_dropdown, image2_jwt_bearer, image2_bearer_token_field, image2_auth_options [EXTRACTED 1.00]
- **Image Upload UI Design Pattern** — imageupload_icon, imageupload_uploadaction, imageupload_uiasset [INFERRED 0.85]

## Communities

### Community 0 - "Frontend Admin UI Components"
Cohesion: 0.01
Nodes (71): fetchRequests(), handleValidate(), getToken(), handleCreateWorkOrder(), handleDismiss(), exportCSV(), fetchAuditLog(), fetchMachineHistory() (+63 more)

### Community 1 - "Admin Intervention Routes"
Cohesion: 0.03
Nodes (211): Config, get_all_pending_requests(), ItvRequestResponse, ItvRequestValidation, Admin: Approve or Reject an intervention request, Admin: List all PENDING intervention requests, validate_itv_request(), List all work orders with ChefOp and Machine details for Admin (+203 more)

### Community 2 - "Backend Base Models & Helpers"
Cohesion: 0.02
Nodes (179): BaseModel, Query machiness with filtering, sorting, and pagination, get_planning_with_users(), get_user_by_id(), Send notifications to all assigned users, Get planning with assigned users.     Uses pre-loaded relationships if available, Verify that the current user is an admin, Validate planning data (+171 more)

### Community 3 - "AI Agent Integration Layer"
Cohesion: 0.02
Nodes (167): AI4I 2020 Predictive Maintenance Dataset, FastAPI Backend, basic_machine_model.pkl (Trained Random Forest), EAMSagemCom Agent Handoff Document, React + TypeScript + Vite Frontend, Groq Integration (Natural Language ML Explanations), HDF (Heat Dissipation Failure) — Top Predictor, healthScore.ts (Machine Health Score Utility) (+159 more)

### Community 4 - "JWT Authentication & RBAC"
Cohesion: 0.02
Nodes (115): Config, create_access_token(), decode_access_token(), get_admin_user(), get_bearer_token(), get_current_user(), get_me(), initialize_admin_user() (+107 more)

### Community 5 - "Work Order Route Handlers"
Cohesion: 0.02
Nodes (52): export_work_order_report(), list_work_orders(), Export a complete Work Order report to Excel (horizontal format, analysis-ready), export_cheftech_work_order_report(), list_cheftech_work_orders(), Export a complete Work Order report to Excel (horizontal format), List all Work Orders assigned to technicians (for ChefTech monitoring), _require_cheftech() (+44 more)

### Community 6 - "ML Pipeline & Planning Docs"
Cohesion: 0.03
Nodes (101): Active Pilot Phase (Weeks 4-8), AI4I 2020 Predictive Maintenance Dataset (Kaggle), Backend Reorganization Implementation Plan, basic_machine_model.pkl — Saved P1 Model, Chronological Train/Test Split (P6 Time-Series), Codebase Reorganization Design Spec, EAMSagemCom Enterprise Asset Management Platform, HDF — Heat Dissipation Failure (+93 more)

### Community 7 - "Marked.js Markdown Parser"
Cohesion: 0.04
Nodes (15): cleanUrl(), escape$1(), findClosingBracket(), _Hooks, indentCodeCompensation(), _Lexer, Marked, outputLink() (+7 more)

### Community 8 - "Reports Service & CRUD"
Cohesion: 0.04
Nodes (68): check_and_send_due_reports(), Config, create_rapports(), create_rapportss_batch(), delete_rapports(), delete_rapportss_batch(), get_rapports(), query_rapportss() (+60 more)

### Community 9 - "Codebase Architecture Specs"
Cohesion: 0.05
Nodes (66): 350-Line File Size Constraint, AppRoutes.tsx (564 lines, to be split), Auto-Discovery via pkgutil.walk_packages, Backend Reorganization Implementation Plan, Codebase Reorganization Design Spec, main.py — FastAPI Application Entry Point, modules/admin/ — Admin Module, modules/cheftech/ — ChefTech Role Module (+58 more)

### Community 10 - "Alerts & Audit Logging"
Cohesion: 0.05
Nodes (47): Alertes_urgentes, AuditActionType, AuditEntityType, AuditLog, AuditLogResponse, AuditService, AuditStatsResponse, Config (+39 more)

### Community 11 - "Config & Environment Settings"
Cohesion: 0.04
Nodes (37): BaseSettings, Config, getAPIBaseURL(), getConfig(), Dynamically read attributes from environment variables.         For example: se, Settings, check_database_health(), _check_db_exist() (+29 more)

### Community 12 - "MinIO Object Storage"
Cohesion: 0.17
Nodes (39): BucketInfo, BucketListResponse, BucketRequest, BucketResponse, delete_object(), DeleteResponse, download_file(), FileUpDownRequest (+31 more)

### Community 13 - "AI Hub LLM Service"
Cohesion: 0.12
Nodes (42): AIHubService, ChatMessage, ContentPartImage, ContentPartText, extract_error_message(), _extract_image_ref(), _filename_from_content_type(), generate_image() (+34 more)

### Community 14 - "ML Pipeline Documentation"
Cohesion: 0.06
Nodes (50): AI4I 2020 Dataset (Kaggle, 10k rows), API Endpoint: GET /api/v1/ml/machines/{id}/prediction, API Endpoint: POST /api/v1/ml/retrain, basic_machine_model.pkl (P1 Trained Model), Enterprise Asset Management Platform, EAMSagemCom ML Pipeline Plan, ML Backend Module (app/backend/modules/ml/), ml_predictive.py (Active ML Service) (+42 more)

### Community 15 - "Equipment Archives CRUD"
Cohesion: 0.06
Nodes (35): Archives, ArchivesBatchCreateRequest, ArchivesBatchDeleteRequest, ArchivesBatchUpdateItem, ArchivesBatchUpdateRequest, ArchivesData, ArchivesListResponse, ArchivesResponse (+27 more)

### Community 16 - "Planned Maintenance CRUD"
Cohesion: 0.07
Nodes (38): Config, create_maintenances_planifiees(), create_maintenances_planifieess_batch(), delete_maintenances_planifiees(), delete_maintenances_planifieess_batch(), get_maintenances_planifiees(), Maintenances_planifiees, Maintenances_planifieesBatchCreateRequest (+30 more)

### Community 17 - "Maintenance Orders CRUD"
Cohesion: 0.07
Nodes (32): Config, create_ordress_batch(), delete_ordres(), delete_ordress_batch(), get_ordres(), Ordres, OrdresBatchCreateRequest, OrdresBatchDeleteRequest (+24 more)

### Community 18 - "AWS Lambda Deployment"
Cohesion: 0.09
Nodes (36): format_traceback(), get_backend_app(), get_mangum_handler(), get_mangum_handler_sync(), handle_backend_request_sync(), handle_config_request(), initialize_dynamic_routes(), initialize_services_once() (+28 more)

### Community 19 - "Planning Work Orders Service"
Cohesion: 0.17
Nodes (10): Planning_ordres_travail, Planning_ordres_travailService, Delete planning_ordres_travail, Get planning_ordres_travail by any field, Service layer for Planning_ordres_travail operations, Get list of planning_ordres_travails filtered by field, Create a new planning_ordres_travail, Get planning_ordres_travail by ID (+2 more)

### Community 20 - "Intervention Orders Service"
Cohesion: 0.12
Nodes (9): Ordres_interventionService, Delete ordres_intervention, Get ordres_intervention by any field, Service layer for Ordres_intervention operations, Get list of ordres_interventions filtered by field, Create a new ordres_intervention, Get ordres_intervention by ID, Get paginated list of ordres_interventions (+1 more)

### Community 21 - "Work Orders Service"
Cohesion: 0.12
Nodes (9): Ordres_travailService, Update ordres_travail, Delete ordres_travail, Service layer for Ordres_travail operations, Get ordres_travail by any field, Get list of ordres_travails filtered by field, Create a new ordres_travail, Get ordres_travail by ID (+1 more)

### Community 22 - "WebSocket Real-time Notifications"
Cohesion: 0.13
Nodes (9): ConnectionManager, WebSocket Manager for real-time notifications, Manages WebSocket connections for real-time notifications, Accept a new WebSocket connection, Remove a WebSocket connection, Send a message to a specific user (all their connections), Broadcast a message to all users with a specific role, Notify a user about their account status change (+1 more)

### Community 23 - "Machine Asset CRUD Service"
Cohesion: 0.16
Nodes (6): MachinesService, Get machines by any field, Service layer for Machines operations, Get list of machiness filtered by field, Create a new machines, Get paginated list of machiness

### Community 24 - "Domain Class Diagram Models"
Cohesion: 0.16
Nodes (14): Archive, ContratIntervention, Machine, MaintenancePlanNee, Ordre, OrdreTravail, Planning, Priorite (enum) (+6 more)

### Community 25 - "ML Prediction Engine"
Cohesion: 0.18
Nodes (2): _predict_model_rul(), _project_health_end()

### Community 26 - "DB shift_type Schema Error"
Cohesion: 0.19
Nodes (13): asyncpg PostgreSQL Driver, INSERT INTO plannings SQL Statement, Create Planning Operation, Plannings Database Table, shift_type Column (Missing), SQLAlchemy ProgrammingError - Missing shift_type Column, API Client Tool (Insomnia/Postman-like), Authentication Type Dropdown Menu (+5 more)

### Community 27 - "Shared UI Components"
Cohesion: 0.15
Nodes (0): 

### Community 28 - "Blog HTML Generator"
Cohesion: 0.38
Nodes (9): escapeHtml(), formatDate(), generateListPage(), generateTOC(), getHtmlTemplate(), main(), parseFrontmatter(), processMarkdownFile() (+1 more)

### Community 29 - "JWT Migration Guide"
Cohesion: 0.36
Nodes (8): Installation Guide, JWT Authentication System (bcrypt + SQLite/PostgreSQL), POST /api/v1/auth/login Endpoint, Login.tsx (Tabbed Register/Login UI), GET /api/v1/auth/me Endpoint, JWT Authentication Migration Document, OIDC Removal Rationale, POST /api/v1/auth/register Endpoint

### Community 30 - "ChefTech Feedback Migration"
Cohesion: 0.33
Nodes (5): downgrade(), Add cheftech_feedback column to ordres_travail  Revision ID: a1b2c3d4e5f6 Revise, Add cheftech_feedback text column., Remove cheftech_feedback column., upgrade()

### Community 31 - "PDCA ML Tables Migration"
Cohesion: 0.47
Nodes (4): _column_exists(), Add PDCA ML prediction logs table and feedback columns  Revision ID: add_pdca_, _table_exists(), upgrade()

### Community 32 - "Intervention Approval Migration"
Cohesion: 0.47
Nodes (4): _column_exists(), _index_exists(), Add intervention approval workflow fields  Revision ID: interventions_approval_w, upgrade()

### Community 33 - "Work Order Phase 1 Migration"
Cohesion: 0.47
Nodes (4): _column_exists(), _index_exists(), Phase 1: Work Orders & Interventions workflow  Revision ID: phase1_work_orders_i, upgrade()

### Community 34 - "Planning Multi-select Migration"
Cohesion: 0.47
Nodes (4): _index_exists(), Add planning_machines table for multi-machine selection in planning  Revision ID, _table_exists(), upgrade()

### Community 35 - "User Schema Migration"
Cohesion: 0.33
Nodes (5): downgrade(), Standardize utilisateurs schema to use id, nom, email, mot_de_passe, role  Rev, Upgrade schema: standardize utilisateurs table., Downgrade schema: restore old utilisateurs columns., upgrade()

### Community 36 - "CheTop Orders Migration"
Cohesion: 0.33
Nodes (5): downgrade(), Update ordres_travail table for CHETOP functionality  Revision ID: update_ordr, Update ordres_travail table to match CHETOP requirements, Revert changes to ordres_travail table, upgrade()

### Community 37 - "Encryption Utilities"
Cohesion: 0.53
Nodes (5): decrypt_text(), _derive_fernet_key(), encrypt_text(), _get_fernet(), Derive a valid Fernet key from arbitrary string using SHA-256 and urlsafe base64

### Community 38 - "Notification Broadcaster Service"
Cohesion: 0.33
Nodes (2): NotificationBroadcaster, Manages SSE connections for notifications

### Community 39 - "Fleet Dashboard Cache Tests"
Cohesion: 0.4
Nodes (3): DummyIntervention, DummyMachine, test_fleet_dashboard_caching()

### Community 40 - "P3 RUL Verification Tests"
Cohesion: 0.5
Nodes (3): MockMachine, Verification script for P3 RUL Estimation. Tests the MachineLearningService int, test_rul_prediction()

### Community 41 - "Machine Telemetry Migration"
Cohesion: 0.5
Nodes (3): _column_exists(), Add machine telemetry sensor columns  Revision ID: add_machine_telemetry_colum, upgrade()

### Community 42 - "Work Order Timer Migration"
Cohesion: 0.5
Nodes (3): _column_exists(), add_timer_started_at_to_ot  Revision ID: b7c8d9e0f1a3 Revises: a1b2c3d4e5f6 Crea, upgrade()

### Community 43 - "P4 Anomaly Verification Tests"
Cohesion: 0.5
Nodes (3): MockMachine, Verification Script for P4 Anomaly Detection Tests the integration of P4 model, test_p4_scenarios()

### Community 44 - "P5 Priority Verification Tests"
Cohesion: 0.5
Nodes (3): MockMachine, Verification Script for P5 Priority Prediction Tests the integration of P5 mode, test_p5_scenarios()

### Community 45 - "ML Prediction Unit Tests"
Cohesion: 0.4
Nodes (1): TestMLPrediction

### Community 46 - "Order ID Nullable Migration"
Cohesion: 0.5
Nodes (1): Make ordre_travail_id nullable  Revision ID: 55c181562e1e Revises: be6721db2847

### Community 47 - "Granular Planning Fields Migration"
Cohesion: 0.5
Nodes (1): Add sous_zone and ordre to plannings  Revision ID: add_granular_planning_field

### Community 48 - "Performance Index Migration v2"
Cohesion: 0.5
Nodes (1): add more performance indexes for machines and related tables  Revision ID: more_

### Community 49 - "Performance Index Migration v1"
Cohesion: 0.5
Nodes (1): add performance indexes  Revision ID: new_perf_indexes Revises: 55c181562e1e

### Community 50 - "Planning Index Migration"
Cohesion: 0.5
Nodes (1): add planning_machines machine_id index  Revision ID: add_plannings_idx Revises:

### Community 51 - "Requested By Field Migration"
Cohesion: 0.5
Nodes (1): Add requested_by column to Ordres_intervention  Revision ID: add_requested_by Re

### Community 52 - "User Status & Shift Migration"
Cohesion: 0.5
Nodes (1): add status and shift type to utilisateurs  Revision ID: b9e76d0812f5 Revises: b7

### Community 53 - "Alembic Multi-head Merge"
Cohesion: 0.5
Nodes (1): merge multiple heads  Revision ID: be6721db2847 Revises: b9e76d0812f5, f44d6d

### Community 54 - "Auto Update Migration"
Cohesion: 0.5
Nodes (1): auto update  Revision ID: db0b16342160 Revises:  Create Date: 2026-01-27 03:

### Community 55 - "Work Order Validation Migration"
Cohesion: 0.5
Nodes (1): Add WorkOrder execution validation fields  Revision ID: e0fddb28a2cf Revises: ad

### Community 56 - "User Shift Type Migration v2"
Cohesion: 0.5
Nodes (1): add_status_shift_type_to_utilisateurs  Revision ID: f44d6d0416f4 Revises: b7c8d9

### Community 57 - "Work Order Enhancement Migration"
Cohesion: 0.5
Nodes (1): Bridge migration: fix_enhance_work_orders  Revision ID: fix_enhance_work_orders

### Community 58 - "Logout & Loading UI"
Cohesion: 0.5
Nodes (0): 

### Community 59 - "P5 Priority ML Training"
Cohesion: 0.5
Nodes (1): P5 — Work Order Priority Prediction (Optimized) Training script: XGBoost Classif

### Community 60 - "P6 Schedule ML Training"
Cohesion: 0.5
Nodes (1): P6 — Maintenance Schedule Optimization (Optimized) Training script: XGBoost Regr

### Community 61 - "Frontend Build Error Docs"
Cohesion: 0.5
Nodes (4): Build Error: Missing badges utility module, Frontend Build Error Log, Importer: AdminWorkOrdersList.tsx, Missing Module: src/modules/shared/utils/badges

### Community 62 - "Frontend Public Images"
Cohesion: 0.67
Nodes (4): Frontend Public Images Directory, Image Upload Icon, UI Asset - Image Upload Button, Upload Action

### Community 63 - "Technician Security Check"
Cohesion: 0.67
Nodes (2): Dependency to verify that the current user has the TECHNICIEN role., verify_technicien()

### Community 64 - "Machine Naming Standards"
Cohesion: 0.67
Nodes (2): generate_machine_name(), Generate the standardized machine name matching frontend logic.

### Community 65 - "API Health Check"
Cohesion: 0.67
Nodes (2): database_health_check(), Check database connection health

### Community 66 - "Machine Detail Hook"
Cohesion: 0.67
Nodes (0): 

### Community 67 - "P3 RUL ML Training"
Cohesion: 0.67
Nodes (1): P3 — RUL Estimation (Optimized) Training script: XGBoost Regressor with GridSear

### Community 68 - "Role Schema Validation"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Work Zone Checker"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "MinIO Bucket Scripts"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "MinIO Manual Bucket"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "MinIO CLI Bucket"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "MinIO Docker Bucket"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "MinIO Docker Bucket Fixed"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "MinIO Bucket Fix v2"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "MinIO Bucket Fix v3"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "MinIO Simple Bucket"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Tech DB Tables Script"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Alembic Fix Script"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Database Inspector"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Async DB Inspector"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Celery Task Queue"
Cohesion: 1.0
Nodes (0): 

### Community 83 - "Planning Email Notifications"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Tailwind CSS Config"
Cohesion: 1.0
Nodes (0): 

### Community 85 - "Sitemap Generator"
Cohesion: 1.0
Nodes (0): 

### Community 86 - "Frontend Welcome Page"
Cohesion: 1.0
Nodes (0): 

### Community 87 - "ChefTech Machines Header"
Cohesion: 1.0
Nodes (0): 

### Community 88 - "Basic ML Training Script"
Cohesion: 1.0
Nodes (1): P1 — Failure Prediction (Optimized) Training script: XGBoost + SMOTE + 5-fold Gr

### Community 89 - "ML Prediction CLI"
Cohesion: 1.0
Nodes (0): 

### Community 90 - "P2 Failure Type Training"
Cohesion: 1.0
Nodes (1): P2 — Failure Type Classification (Optimized) Training script: MultiOutputClassif

### Community 91 - "P4 Anomaly Training"
Cohesion: 1.0
Nodes (1): P4 — Anomaly Detection (Optimized) Training script: Isolation Forest with GridSe

### Community 92 - "Failure Probability Tests"
Cohesion: 1.0
Nodes (0): 

### Community 93 - "P2 Failure Type Tests"
Cohesion: 1.0
Nodes (0): 

### Community 94 - "Health Check TC001"
Cohesion: 1.0
Nodes (0): 

### Community 95 - "DB Health Check TC002"
Cohesion: 1.0
Nodes (0): 

### Community 96 - "ML Prediction TC006"
Cohesion: 1.0
Nodes (0): 

### Community 97 - "ML Retrain TC007"
Cohesion: 1.0
Nodes (0): 

### Community 98 - "Frontend Dependencies"
Cohesion: 1.0
Nodes (2): Frontend Dependency: axios, Frontend Requirements (axios)

### Community 99 - "Zone Analysis Script"
Cohesion: 1.0
Nodes (0): 

### Community 100 - "Migration Checker Script"
Cohesion: 1.0
Nodes (0): 

### Community 101 - "P4 Notebook Update"
Cohesion: 1.0
Nodes (0): 

### Community 102 - "Migration Writer Script"
Cohesion: 1.0
Nodes (0): 

### Community 103 - "Config Rationale Note"
Cohesion: 1.0
Nodes (1): Generate backend URL from host and port.

### Community 104 - "Enum Rationale v1"
Cohesion: 1.0
Nodes (1): Handle missing enum values by trying to match against string values.         Th

### Community 105 - "Enum Rationale v2"
Cohesion: 1.0
Nodes (1): Handle missing enum values by trying to match against integer values.         T

### Community 106 - "Machine Parts Model"
Cohesion: 1.0
Nodes (0): 

### Community 107 - "ML XAI Rationale v1"
Cohesion: 1.0
Nodes (1): Generate SHAP explanations for a single prediction.                  Args:

### Community 108 - "ML XAI Rationale v2"
Cohesion: 1.0
Nodes (1): Map dataset column names to user-friendly French labels.

### Community 109 - "Auth Rationale v1"
Cohesion: 1.0
Nodes (1): Validate password requirements

### Community 110 - "Auth Rationale v2"
Cohesion: 1.0
Nodes (1): Validate name is not empty

### Community 111 - "ESLint Configuration"
Cohesion: 1.0
Nodes (0): 

### Community 112 - "PostCSS Configuration"
Cohesion: 1.0
Nodes (0): 

### Community 113 - "Vite Build Configuration"
Cohesion: 1.0
Nodes (0): 

### Community 114 - "Build Output"
Cohesion: 1.0
Nodes (0): 

### Community 115 - "Vite Type Definitions"
Cohesion: 1.0
Nodes (0): 

### Community 116 - "Collapsible Component"
Cohesion: 1.0
Nodes (0): 

### Community 117 - "ML EDA Notebook"
Cohesion: 1.0
Nodes (0): 

### Community 118 - "Favicon SVG Asset"
Cohesion: 1.0
Nodes (1): Favicon SVG — Sagemcom/EAM App Icon (White Stylized S-like Curve on Black Background, 16x16)

### Community 119 - "ITV Approval Problem"
Cohesion: 1.0
Nodes (1): ITV Approval Bug (Not Converting to Work Order)

### Community 120 - "ITV Error Problem"
Cohesion: 1.0
Nodes (1): Chef d'Op ITV Request False Error Message

### Community 121 - "Workload Level Problem"
Cohesion: 1.0
Nodes (1): Deprecated Field 'Niveau de charge (%)' Removal

### Community 122 - "Design System Todo"
Cohesion: 1.0
Nodes (1): Design System Plan (Asana/Monday.com Style)

### Community 123 - "DB Schema Todo"
Cohesion: 1.0
Nodes (1): Database Schema Plan (All Tables)

### Community 124 - "Frontend Robots.txt"
Cohesion: 1.0
Nodes (1): Frontend Robots.txt

## Knowledge Gaps
- **328 isolated node(s):** `Verification script for P3 RUL Estimation. Tests the MachineLearningService int`, `AWS Lambda handler for unified frontend and backend with Nginx reverse proxy Th`, `Format traceback with newlines replaced by '\\n' string literal`, `Initialize dynamic routes by scanning frontend dist directory`, `Initialize all services once for the Lambda function (equivalent to FastAPI life` (+323 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Role Schema Validation`** (2 nodes): `check_role_schema.py`, `check_schema()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Work Zone Checker`** (2 nodes): `check_zone_travail.py`, `check_zone_travail()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Bucket Scripts`** (2 nodes): `create_minio_bucket.py`, `create_bucket()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Manual Bucket`** (2 nodes): `create_minio_bucket_manual.py`, `create_bucket_via_curl()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO CLI Bucket`** (2 nodes): `create_minio_bucket_mc.py`, `create_bucket_with_mc()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Docker Bucket`** (2 nodes): `create_minio_bucket_mc_docker.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Docker Bucket Fixed`** (2 nodes): `create_minio_bucket_mc_docker_fixed.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Bucket Fix v2`** (2 nodes): `create_minio_bucket_mc_fixed2.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Bucket Fix v3`** (2 nodes): `create_minio_bucket_mc_fixed3.py`, `create_bucket_via_docker()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MinIO Simple Bucket`** (2 nodes): `create_minio_bucket_simple.py`, `create_bucket()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tech DB Tables Script`** (2 nodes): `create_tech_tables.py`, `create_tables()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Alembic Fix Script`** (2 nodes): `fix_alembic.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Database Inspector`** (2 nodes): `inspect_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Async DB Inspector`** (2 nodes): `inspect_db_async.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Celery Task Queue`** (2 nodes): `celery_app.py`, `_get_broker_url()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Planning Email Notifications`** (2 nodes): `planning_emails.py`, `send_planning_assignment_emails()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tailwind CSS Config`** (2 nodes): `aspect-ratio.tsx`, `tailwind.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Sitemap Generator`** (2 nodes): `generate-sitemap.js`, `collectHtmlFiles()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Welcome Page`** (2 nodes): `index.ts`, `WelcomePage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ChefTech Machines Header`** (2 nodes): `ChefTechMachinesHeader.tsx`, `ChefTechMachinesHeader()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Basic ML Training Script`** (2 nodes): `ml_train_basic.py`, `P1 — Failure Prediction (Optimized) Training script: XGBoost + SMOTE + 5-fold Gr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML Prediction CLI`** (2 nodes): `predict_cli.py`, `predict_failure()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P2 Failure Type Training`** (2 nodes): `ml_train_p2.py`, `P2 — Failure Type Classification (Optimized) Training script: MultiOutputClassif`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P4 Anomaly Training`** (2 nodes): `ml_train_p4.py`, `P4 — Anomaly Detection (Optimized) Training script: Isolation Forest with GridSe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Failure Probability Tests`** (2 nodes): `test_failure_probability.py`, `test_failure_probability_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P2 Failure Type Tests`** (2 nodes): `test_p2_failure_type.py`, `test_failure_type_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Health Check TC001`** (2 nodes): `TC001_get_health_basic_check.py`, `test_get_health_basic_check()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `DB Health Check TC002`** (2 nodes): `TC002_get_api_v1_health_check_database_connected.py`, `test_get_api_v1_health_check_database_connected()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML Prediction TC006`** (2 nodes): `TC006_get_api_v1_ml_machines_machineid_prediction_success.py`, `test_get_api_v1_ml_machines_machineid_prediction_success()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML Retrain TC007`** (2 nodes): `TC007_post_api_v1_ml_retrain_trigger.py`, `test_post_api_v1_ml_retrain_trigger()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Dependencies`** (2 nodes): `Frontend Dependency: axios`, `Frontend Requirements (axios)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Zone Analysis Script`** (1 nodes): `analyze_zones.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Checker Script`** (1 nodes): `check_migrations.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P4 Notebook Update`** (1 nodes): `update_nb_p4.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration Writer Script`** (1 nodes): `write_migration.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Config Rationale Note`** (1 nodes): `Generate backend URL from host and port.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Enum Rationale v1`** (1 nodes): `Handle missing enum values by trying to match against string values.         Th`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Enum Rationale v2`** (1 nodes): `Handle missing enum values by trying to match against integer values.         T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Machine Parts Model`** (1 nodes): `piece_machine.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML XAI Rationale v1`** (1 nodes): `Generate SHAP explanations for a single prediction.                  Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML XAI Rationale v2`** (1 nodes): `Map dataset column names to user-friendly French labels.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Rationale v1`** (1 nodes): `Validate password requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Rationale v2`** (1 nodes): `Validate name is not empty`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ESLint Configuration`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostCSS Configuration`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Build Configuration`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Build Output`** (1 nodes): `build.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Type Definitions`** (1 nodes): `vite-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Collapsible Component`** (1 nodes): `collapsible.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ML EDA Notebook`** (1 nodes): `ml_eda.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Favicon SVG Asset`** (1 nodes): `Favicon SVG — Sagemcom/EAM App Icon (White Stylized S-like Curve on Black Background, 16x16)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ITV Approval Problem`** (1 nodes): `ITV Approval Bug (Not Converting to Work Order)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ITV Error Problem`** (1 nodes): `Chef d'Op ITV Request False Error Message`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Workload Level Problem`** (1 nodes): `Deprecated Field 'Niveau de charge (%)' Removal`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Design System Todo`** (1 nodes): `Design System Plan (Asana/Monday.com Style)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `DB Schema Todo`** (1 nodes): `Database Schema Plan (All Tables)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Robots.txt`** (1 nodes): `Frontend Robots.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Codebase Reorganization Design Spec` connect `Codebase Architecture Specs` to `ML Pipeline & Planning Docs`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `EAMSagemCom Enterprise Asset Management Platform` connect `ML Pipeline & Planning Docs` to `Codebase Architecture Specs`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 160 inferred relationships involving `Utilisateurs` (e.g. with `Get a human-readable name for an entity` and `Process pending audit entries after flush`) actually correct?**
  _`Utilisateurs` has 160 INFERRED edges - model-reasoned connections that need verification._
- **Are the 119 inferred relationships involving `Machines` (e.g. with `Base` and `ItvRequestValidation`) actually correct?**
  _`Machines` has 119 INFERRED edges - model-reasoned connections that need verification._
- **Are the 95 inferred relationships involving `UserRole` (e.g. with `Base` and `ItvRequestValidation`) actually correct?**
  _`UserRole` has 95 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `PaginatedResponse` (e.g. with `ItvRequestValidation` and `ItvRequestResponse`) actually correct?**
  _`PaginatedResponse` has 81 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Verification script for P3 RUL Estimation. Tests the MachineLearningService int`, `AWS Lambda handler for unified frontend and backend with Nginx reverse proxy Th`, `Format traceback with newlines replaced by '\\n' string literal` to the rest of the system?**
  _328 weakly-connected nodes found - possible documentation gaps or missing edges._