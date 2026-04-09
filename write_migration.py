content = """-- BEGIN MIGRATION: Fix Tonic-generated types
SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SELECT pg_catalog.set_config('search_path', 'public', false);
SET session_replication_role = 'replica';

BEGIN;

-- Table: alertes_urgentes
ALTER TABLE IF EXISTS alertes_urgentes RENAME TO alertes_urgentes__bak;
CREATE TABLE public.alertes_urgentes (
    id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    categorie character varying NOT NULL,
    description character varying NOT NULL,
    machine_id integer,
    photo_url character varying,
    statut character varying NOT NULL,
    ordre_travail_genere_id integer,
    created_at timestamp with time zone
);
INSERT INTO public.alertes_urgentes SELECT id, utilisateur_id, categorie::character varying, description::character varying, machine_id, photo_url::character varying, statut::character varying, ordre_travail_genere_id, created_at::timestamp with time zone FROM alertes_urgentes__bak;

-- Table: archives
ALTER TABLE IF EXISTS archives RENAME TO archives__bak;
CREATE TABLE public.archives (
    id integer NOT NULL,
    identifiant_archive character varying NOT NULL,
    nom character varying NOT NULL,
    date_archivage timestamp with time zone NOT NULL,
    type character varying NOT NULL,
    object_key character varying,
    ordre_travail_id integer,
    created_at timestamp with time zone
);
INSERT INTO public.archives SELECT id, identifiant_archive::character varying, nom::character varying, date_archivage::timestamp with time zone, type::character varying, object_key::character varying, ordre_travail_id, created_at::timestamp with time zone FROM archives__bak;

-- Table: commentaires
ALTER TABLE IF EXISTS commentaires RENAME TO commentaires__bak;
CREATE TABLE public.commentaires (
    id integer NOT NULL,
    ordre_travail_id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    contenu character varying NOT NULL,
    fichier_url character varying,
    created_at timestamp with time zone
);
INSERT INTO public.commentaires SELECT id, ordre_travail_id, utilisateur_id, contenu::character varying, fichier_url::character varying, created_at::timestamp with time zone FROM commentaires__bak;

-- Table: machines
ALTER TABLE IF EXISTS machines RENAME TO machines__bak;
CREATE TABLE public.machines (
    id integer NOT NULL,
    nom character varying NOT NULL,
    emplacement character varying,
    statut character varying,
    type character varying,
    date_derniere_maintenance timestamp with time zone,
    date_prochaine_maintenance timestamp with time zone,
    image_url character varying,
    created_at timestamp with time zone,
    air_temperature double precision DEFAULT '300'::double precision,
    process_temperature double precision DEFAULT '310'::double precision,
    rotational_speed integer DEFAULT 1500,
    torque double precision DEFAULT '40'::double precision,
    tool_wear integer DEFAULT 0,
    zone character varying,
    sous_zone character varying,
    ordre character varying
);
INSERT INTO public.machines SELECT id, nom::character varying, emplacement::character varying, statut::character varying, type::character varying, date_derniere_maintenance::timestamp with time zone, date_prochaine_maintenance::timestamp with time zone, image_url::character varying, created_at::timestamp with time zone, air_temperature::double precision, process_temperature::double precision, rotational_speed, torque::double precision, tool_wear, zone::character varying, sous_zone::character varying, ordre::character varying FROM machines__bak;

-- Table: ml_prediction_logs
ALTER TABLE IF EXISTS ml_prediction_logs RENAME TO ml_prediction_logs__bak;
CREATE TABLE public.ml_prediction_logs (
    id integer NOT NULL,
    machine_id integer NOT NULL,
    machine_name character varying,
    risk_level character varying(20),
    failure_probability double precision,
    rul_days double precision,
    predicted_failure_date character varying,
    predicted_priority character varying(20),
    is_anomaly boolean,
    anomaly_score double precision,
    p2_failure_types text,
    data_points integer,
    ml_model_used boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    air_temperature double precision,
    process_temperature double precision,
    rotational_speed integer,
    torque double precision,
    tool_wear integer
);
INSERT INTO public.ml_prediction_logs SELECT id, machine_id, machine_name::character varying, risk_level::character varying(20), failure_probability::double precision, rul_days::double precision, predicted_failure_date::character varying, predicted_priority::character varying(20), CASE WHEN is_anomaly::text IN ('t', 'true', '1') THEN true ELSE false END, anomaly_score::double precision, p2_failure_types, data_points, CASE WHEN ml_model_used::text IN ('t', 'true', '1') THEN true ELSE false END, created_at::timestamp with time zone, air_temperature::double precision, process_temperature::double precision, rotational_speed, torque::double precision, tool_wear FROM ml_prediction_logs__bak;

-- Table: ordres_intervention
ALTER TABLE IF EXISTS ordres_intervention RENAME TO ordres_intervention__bak;
CREATE TABLE public.ordres_intervention (
    id integer NOT NULL,
    date_intervention timestamp with time zone NOT NULL,
    rapport character varying,
    ordre_travail_id integer,
    created_at timestamp with time zone DEFAULT now(),
    technicien_id integer,
    statut character varying(20) NOT NULL,
    date_debut timestamp with time zone,
    date_fin timestamp with time zone,
    updated_at timestamp with time zone,
    problem_description text,
    priority character varying(20),
    estimated_duration_minutes integer,
    required_materials text,
    machine_id integer,
    requested_at timestamp with time zone,
    approved_by integer,
    approved_at timestamp with time zone,
    rejection_reason text,
    actual_failure_type character varying(20),
    ml_prediction_matched boolean,
    retrained boolean,
    machine_category character varying,
    symptoms text,
    problem_start_time timestamp with time zone,
    frequency character varying,
    operating_state character varying,
    load_level integer,
    temperature character varying,
    impact character varying,
    estimated_loss character varying,
    similar_issue_before boolean,
    suggested_cause character varying,
    suggested_priority character varying,
    risk_score character varying,
    intervention_type character varying,
    root_cause_category character varying,
    root_cause_description text,
    actions_performed text,
    parts_replaced text,
    tools_used text,
    machine_status_after character varying,
    plan_hypothesis text,
    check_resolved boolean,
    check_verification_method character varying,
    act_preventive_actions text,
    act_recommendations text
);
INSERT INTO public.ordres_intervention SELECT id, date_intervention::timestamp with time zone, rapport::character varying, ordre_travail_id, created_at::timestamp with time zone, technicien_id, statut::character varying(20), date_debut::timestamp with time zone, date_fin::timestamp with time zone, updated_at::timestamp with time zone, problem_description, priority::character varying(20), estimated_duration_minutes, required_materials, machine_id, requested_at::timestamp with time zone, approved_by, approved_at::timestamp with time zone, rejection_reason, actual_failure_type::character varying(20), ml_prediction_matched::boolean, retrained::boolean, machine_category::character varying, symptoms, problem_start_time::timestamp with time zone, frequency::character varying, operating_state::character varying, load_level, temperature::character varying, impact::character varying, estimated_loss::character varying, similar_issue_before::boolean, suggested_cause::character varying, suggested_priority::character varying, risk_score::character varying, intervention_type::character varying, root_cause_category::character varying, root_cause_description, actions_performed, parts_replaced, tools_used, machine_status_after::character varying, plan_hypothesis, check_resolved::boolean, check_verification_method::character varying, act_preventive_actions, act_recommendations FROM ordres_intervention__bak;

-- Table: utilisateurs
ALTER TABLE IF EXISTS utilisateurs RENAME TO utilisateurs__bak;
CREATE TABLE public.utilisateurs (
    id integer NOT NULL,
    nom character varying NOT NULL,
    mot_de_passe character varying NOT NULL,
    email character varying NOT NULL,
    role public.userrole NOT NULL,
    created_at timestamp without time zone,
    status public.userstatus NOT NULL,
    shift_type character varying(7) NOT NULL,
    updated_at timestamp without time zone
);
INSERT INTO public.utilisateurs SELECT id, nom::character varying, mot_de_passe::character varying, email::character varying, role::public.userrole, created_at::timestamp without time zone, status::public.userstatus, shift_type::character varying(7), updated_at::timestamp without time zone FROM utilisateurs__bak;

-- Table: plannings
ALTER TABLE IF EXISTS plannings RENAME TO plannings__bak;
CREATE TABLE public.plannings (
    id integer NOT NULL,
    identifiant_planning character varying NOT NULL,
    date_debut timestamp with time zone NOT NULL,
    date_fin timestamp with time zone NOT NULL,
    type public.planningtype NOT NULL,
    created_at timestamp with time zone,
    sous_zone character varying(100),
    ordre character varying(100),
    shift_type public.shifttype,
    chef_operation_id integer,
    chef_technique_id integer,
    zone_travail character varying
);
INSERT INTO public.plannings SELECT id, identifiant_planning::character varying, date_debut::timestamp with time zone, date_fin::timestamp with time zone, type::public.planningtype, created_at::timestamp with time zone, sous_zone::character varying(100), ordre::character varying(100), shift_type::public.shifttype, chef_operation_id, chef_technique_id, zone_travail::character varying FROM plannings__bak;

-- Table: maintenances_planifiees
ALTER TABLE IF EXISTS maintenances_planifiees RENAME TO maintenances_planifiees__bak;
CREATE TABLE public.maintenances_planifiees (
    id integer NOT NULL,
    utilisateur_id integer,
    rapport_id integer,
    date_planifiee timestamp with time zone NOT NULL,
    description character varying,
    created_at timestamp with time zone
);
INSERT INTO public.maintenances_planifiees SELECT id, utilisateur_id, rapport_id, date_planifiee::timestamp with time zone, description::character varying, created_at::timestamp with time zone FROM maintenances_planifiees__bak;

-- Table: ordres_travail
ALTER TABLE IF EXISTS ordres_travail RENAME TO ordres_travail__bak;
CREATE TABLE public.ordres_travail (
    id integer NOT NULL,
    date_echeance timestamp with time zone,
    priorite character varying NOT NULL,
    machine_id integer NOT NULL,
    utilisateur_id integer,
    statut character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    titre character varying(255) NOT NULL,
    description text NOT NULL,
    updated_at timestamp with time zone,
    date_debut timestamp with time zone,
    date_fin timestamp with time zone,
    rapport text,
    failure_type character varying(100),
    cheftech_feedback text,
    timer_started_at timestamp with time zone,
    created_by integer,
    validated_by integer,
    date_validation timestamp with time zone,
    estimated_duration integer
);
INSERT INTO public.ordres_travail SELECT id, date_echeance::timestamp with time zone, priorite::character varying, machine_id, utilisateur_id, statut::character varying, created_at::timestamp with time zone, titre::character varying(255), description, updated_at::timestamp with time zone, date_debut::timestamp with time zone, date_fin::timestamp with time zone, rapport, failure_type::character varying(100), cheftech_feedback, timer_started_at::timestamp with time zone, created_by, validated_by, date_validation::timestamp with time zone, estimated_duration FROM ordres_travail__bak;

-- Table: rapports
ALTER TABLE IF EXISTS rapports RENAME TO rapports__bak;
CREATE TABLE public.rapports (
    id integer NOT NULL,
    identifiant_rapport character varying NOT NULL,
    titre character varying NOT NULL,
    date_generation timestamp with time zone NOT NULL,
    contenu character varying NOT NULL,
    utilisateur_id integer,
    created_at timestamp with time zone
);
INSERT INTO public.rapports SELECT id, identifiant_rapport::character varying, titre::character varying, date_generation::timestamp with time zone, contenu::character varying, utilisateur_id, created_at::timestamp with time zone FROM rapports__bak;

-- Table: pieces
ALTER TABLE IF EXISTS pieces RENAME TO pieces__bak;
CREATE TABLE public.pieces (
    id integer NOT NULL,
    reference character varying NOT NULL,
    name character varying NOT NULL,
    description text,
    unit_price double precision,
    category character varying,
    min_stock integer,
    created_at timestamp with time zone DEFAULT now()
);
INSERT INTO public.pieces SELECT id, reference::character varying, name::character varying, description, unit_price::double precision, category::character varying, min_stock, created_at::timestamp with time zone FROM pieces__bak;

-- Table: stock
ALTER TABLE IF EXISTS stock RENAME TO stock__bak;
CREATE TABLE public.stock (
    id integer NOT NULL,
    piece_id integer NOT NULL,
    quantity integer NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);
INSERT INTO public.stock SELECT id, piece_id, quantity, created_at::timestamp with time zone FROM stock__bak;

-- Table: mouvement_stock
ALTER TABLE IF EXISTS mouvement_stock RENAME TO mouvement_stock__bak;
CREATE TABLE public.mouvement_stock (
    id integer NOT NULL,
    piece_id integer NOT NULL,
    quantity integer NOT NULL,
    movement_type character varying NOT NULL,
    reference character varying,
    created_at timestamp with time zone DEFAULT now()
);
INSERT INTO public.mouvement_stock SELECT id, piece_id, quantity, movement_type::character varying, reference::character varying, created_at::timestamp with time zone FROM mouvement_stock__bak;

-- Table: notifications
ALTER TABLE IF EXISTS notifications RENAME TO notifications__bak;
CREATE TABLE public.notifications (
    id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    titre character varying NOT NULL,
    priorite character varying,
    type character varying NOT NULL,
    message character varying NOT NULL,
    date_envoi timestamp with time zone,
    lu boolean NOT NULL,
    created_at timestamp with time zone
);
INSERT INTO public.notifications SELECT id, utilisateur_id, titre::character varying, priorite::character varying, type::character varying, message::character varying, date_envoi::timestamp with time zone, lu::boolean, created_at::timestamp with time zone FROM notifications__bak;

-- Table: ordres
ALTER TABLE IF EXISTS ordres RENAME TO ordres__bak;
CREATE TABLE public.ordres (
    id integer NOT NULL,
    identifiant character varying NOT NULL,
    titre character varying NOT NULL,
    description character varying,
    date_creation timestamp with time zone NOT NULL,
    statut character varying NOT NULL,
    created_at timestamp with time zone
);
INSERT INTO public.ordres SELECT id, identifiant::character varying, titre::character varying, description::character varying, date_creation::timestamp with time zone, statut::character varying, created_at::timestamp with time zone FROM ordres__bak;

-- Table: planning_machines
ALTER TABLE IF EXISTS planning_machines RENAME TO planning_machines__bak;
CREATE TABLE public.planning_machines (
    id integer NOT NULL,
    planning_id integer NOT NULL,
    machine_id integer NOT NULL,
    created_at timestamp with time zone
);
INSERT INTO public.planning_machines SELECT id, planning_id, machine_id, created_at::timestamp with time zone FROM planning_machines__bak;

-- Table: planning_ordres_travail
ALTER TABLE IF EXISTS planning_ordres_travail RENAME TO planning_ordres_travail__bak;
CREATE TABLE public.planning_ordres_travail (
    id integer NOT NULL,
    planning_id integer NOT NULL,
    ordre_travail_id integer NOT NULL,
    created_at timestamp with time zone
);
INSERT INTO public.planning_ordres_travail SELECT id, planning_id, ordre_travail_id, created_at::timestamp with time zone FROM planning_ordres_travail__bak;

-- Table: planning_utilisateurs
ALTER TABLE IF EXISTS planning_utilisateurs RENAME TO planning_utilisateurs__bak;
CREATE TABLE public.planning_utilisateurs (
    id integer NOT NULL,
    planning_id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    created_at timestamp with time zone
);
INSERT INTO public.planning_utilisateurs SELECT id, planning_id, utilisateur_id, created_at::timestamp with time zone FROM planning_utilisateurs__bak;

-- Table: piece_machine
ALTER TABLE IF EXISTS piece_machine RENAME TO piece_machine__bak;
CREATE TABLE public.piece_machine (
    piece_id integer NOT NULL,
    machine_id integer NOT NULL
);
INSERT INTO public.piece_machine SELECT piece_id, machine_id FROM piece_machine__bak;

-- Table: alembic_version
ALTER TABLE IF EXISTS alembic_version RENAME TO alembic_version__bak;
CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);
INSERT INTO public.alembic_version SELECT version_num::character varying(32) FROM alembic_version__bak;

-- 2. Constraints
ALTER TABLE ONLY public.alembic_version ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);
ALTER TABLE ONLY public.alertes_urgentes ADD CONSTRAINT alertes_urgentes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.archives ADD CONSTRAINT archives_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.commentaires ADD CONSTRAINT commentaires_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.machines ADD CONSTRAINT machines_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.maintenances_planifiees ADD CONSTRAINT maintenances_planifiees_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.ml_prediction_logs ADD CONSTRAINT ml_prediction_logs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.mouvement_stock ADD CONSTRAINT mouvement_stock_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.notifications ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.ordres ADD CONSTRAINT ordres_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.ordres_intervention ADD CONSTRAINT ordres_intervention_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.ordres_travail ADD CONSTRAINT ordres_travail_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.piece_machine ADD CONSTRAINT piece_machine_pkey PRIMARY KEY (piece_id, machine_id);
ALTER TABLE ONLY public.pieces ADD CONSTRAINT pieces_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.pieces ADD CONSTRAINT pieces_reference_key UNIQUE (reference);
ALTER TABLE ONLY public.planning_machines ADD CONSTRAINT planning_machines_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.planning_ordres_travail ADD CONSTRAINT planning_ordres_travail_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.planning_utilisateurs ADD CONSTRAINT planning_utilisateurs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.plannings ADD CONSTRAINT plannings_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.rapports ADD CONSTRAINT rapports_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.stock ADD CONSTRAINT stock_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.utilisateurs ADD CONSTRAINT utilisateurs_pkey PRIMARY KEY (id);

-- 3. Sequences
ALTER TABLE ONLY public.alertes_urgentes ALTER COLUMN id SET DEFAULT nextval('public.alertes_urgentes_id_seq'::regclass);
ALTER TABLE ONLY public.archives ALTER COLUMN id SET DEFAULT nextval('public.archives_id_seq'::regclass);
ALTER TABLE ONLY public.commentaires ALTER COLUMN id SET DEFAULT nextval('public.commentaires_id_seq'::regclass);
ALTER TABLE ONLY public.machines ALTER COLUMN id SET DEFAULT nextval('public.machines_id_seq'::regclass);
ALTER TABLE ONLY public.maintenances_planifiees ALTER COLUMN id SET DEFAULT nextval('public.maintenances_planifiees_id_seq'::regclass);
ALTER TABLE ONLY public.ml_prediction_logs ALTER COLUMN id SET DEFAULT nextval('public.ml_prediction_logs_id_seq'::regclass);
ALTER TABLE ONLY public.mouvement_stock ALTER COLUMN id SET DEFAULT nextval('public.mouvement_stock_id_seq'::regclass);
ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);
ALTER TABLE ONLY public.ordres ALTER COLUMN id SET DEFAULT nextval('public.ordres_id_seq'::regclass);
ALTER TABLE ONLY public.ordres_intervention ALTER COLUMN id SET DEFAULT nextval('public.ordres_intervention_id_seq'::regclass);
ALTER TABLE ONLY public.ordres_travail ALTER COLUMN id SET DEFAULT nextval('public.ordres_travail_id_seq'::regclass);
ALTER TABLE ONLY public.pieces ALTER COLUMN id SET DEFAULT nextval('public.pieces_id_seq'::regclass);
ALTER TABLE ONLY public.planning_machines ALTER COLUMN id SET DEFAULT nextval('public.planning_machines_id_seq'::regclass);
ALTER TABLE ONLY public.planning_ordres_travail ALTER COLUMN id SET DEFAULT nextval('public.planning_ordres_travail_id_seq'::regclass);
ALTER TABLE ONLY public.planning_utilisateurs ALTER COLUMN id SET DEFAULT nextval('public.planning_utilisateurs_id_seq'::regclass);
ALTER TABLE ONLY public.plannings ALTER COLUMN id SET DEFAULT nextval('public.plannings_id_seq'::regclass);
ALTER TABLE ONLY public.rapports ALTER COLUMN id SET DEFAULT nextval('public.rapports_id_seq'::regclass);
ALTER TABLE ONLY public.stock ALTER COLUMN id SET DEFAULT nextval('public.stock_id_seq'::regclass);
ALTER TABLE ONLY public.utilisateurs ALTER COLUMN id SET DEFAULT nextval('public.utilisateurs_id_seq'::regclass);

-- 4. Cleanup
DROP TABLE alertes_urgentes__bak;
DROP TABLE archives__bak;
DROP TABLE commentaires__bak;
DROP TABLE machines__bak;
DROP TABLE maintenances_planifiees__bak;
DROP TABLE ml_prediction_logs__bak;
DROP TABLE mouvement_stock__bak;
DROP TABLE notifications__bak;
DROP TABLE ordres__bak;
DROP TABLE ordres_intervention__bak;
DROP TABLE ordres_travail__bak;
DROP TABLE pieces__bak;
DROP TABLE plannings__bak;
DROP TABLE rapports__bak;
DROP TABLE utilisateurs__bak;
DROP TABLE stock__bak;
DROP TABLE planning_machines__bak;
DROP TABLE planning_ordres_travail__bak;
DROP TABLE planning_utilisateurs__bak;
DROP TABLE piece_machine__bak;
DROP TABLE alembic_version__bak;

COMMIT;
SET session_replication_role = 'origin';
"""

with open('fix_tonic_types.sql', 'w') as f:
    f.write(content)
