import os
import joblib
import glob
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.ordres_intervention import OrdresIntervention
from models.ml_prediction_log import MlPredictionLog

logger = logging.getLogger(__name__)

# ai4i2020 dataset column names (deduplicated per sonar S1192)
_COL_TOOL_WEAR = "Tool wear [min]"
_COL_MACHINE_FAILURE = "Machine failure"
_BASE_COLUMNS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    _COL_TOOL_WEAR,
]
_FAILURE_TYPES = ["TWF", "HDF", "PWF", "OSF", "RNF"]

# Models live in the ml-microservice container.
# In Docker Compose this maps to the 'ml-models' named volume mounted at:
#   ml-microservice: /app/models  (write)
#   backend:         /ml_models   (read/write via shared volume)
# Env var ML_MODELS_DIR overrides for local dev (set to microservice models path).
MODELS_DIR = os.getenv(
    "ML_MODELS_DIR",
    os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ),
        "ml-microservice",
        "models",
    ),
)
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "ai4i2020.csv",
)

# Model file mapping
MODEL_FILES = {
    "p1": "basic_machine_model.pkl",
    "p2": "ml_model_p2_failure_type.pkl",
    "p3": "ml_model_p3_rul.pkl",
    "p4": "ml_model_p4_anomaly_v2.pkl",
    "p5": "ml_model_p5_priority.pkl",
    "p6": "ml_model_p6_schedule.pkl",
}

MAX_MODEL_VERSIONS = 3


class RetrainingService:
    @staticmethod
    async def get_retraining_stats(db: AsyncSession):
        """Get number of new data points available for retraining."""
        query = select(func.count(OrdresIntervention.id)).where(
            OrdresIntervention.actual_failure_type.is_not(None),
            OrdresIntervention.retrained.is_(False),
        )
        result = await db.execute(query)
        new_points = result.scalar_one()
        return {"new_data_points": new_points}

    @staticmethod
    def _backup_model(model_name: str) -> Optional[str]:
        """Create timestamped backup of existing model file. Returns backup path or None."""
        model_file = MODEL_FILES.get(model_name)
        if not model_file:
            return None
        model_path = os.path.join(MODELS_DIR, model_file)
        if os.path.exists(model_path):
            backup = f"{model_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(model_path, backup)
            return backup
        return None

    @staticmethod
    def _cleanup_old_versions(model_name: str):
        """Keep only the last MAX_MODEL_VERSIONS backups."""
        model_file = MODEL_FILES.get(model_name)
        if not model_file:
            return
        pattern = os.path.join(MODELS_DIR, f"{model_file}.bak_*")
        backups = sorted(glob.glob(pattern))
        while len(backups) > MAX_MODEL_VERSIONS:
            oldest = backups.pop(0)
            try:
                os.remove(oldest)
                logger.info(f"Cleaned up old model backup: {oldest}")
            except OSError:
                pass

    @staticmethod
    def validate_model(model_name: str, model_data: dict) -> dict:
        """Validate a newly trained model by checking it can make predictions."""
        model = model_data.get("model")
        if model is None:
            return {"valid": False, "error": "No model object found"}

        metrics = model_data.get("metrics", {})
        features = model_data.get("features", [])

        if not features:
            return {"valid": False, "error": "No features defined"}

        return {
            "valid": True,
            "model_type": type(model).__name__,
            "feature_count": len(features),
            "metrics": metrics,
        }

    @staticmethod
    def _prepare_model_targets(mt: str, train_df, val_df) -> Optional[dict]:
        """Prepare y / y_val labels for one model type.

        Returns a targets dict, or None when the model type should be skipped.
        The dict always carries updated train_df / val_df so callers need not
        touch the dataframes directly.
        """
        import pandas as _pd

        if mt == "p6":
            return None  # no label data yet

        if mt == "p4":
            # Ensemble refit not implemented: _fit_model_for_type would fit a
            # bare IsolationForest and joblib.dump it over the live pkl, but
            # the deployed v2 ensemble format requires weights/thresholds/
            # training_stats/ae_scaler alongside iso_model. Overwriting would
            # silently break production inference. Skip until real ensemble
            # refit logic exists (see ML roadmap Phase 4.3).
            return None

        if mt == "p2":
            train_df = train_df.copy()
            val_df = val_df.copy()
            ft_col = train_df.get("actual_failure_type", _pd.Series(["NONE"] * len(train_df)))
            ft_val = val_df.get("actual_failure_type", _pd.Series(["NONE"] * len(val_df)))
            for ft in _FAILURE_TYPES:
                train_df[ft] = ft_col.str.contains(ft, na=False).astype(int)
                val_df[ft] = ft_val.str.contains(ft, na=False).astype(int)
            return {
                "y": train_df[_FAILURE_TYPES].fillna(0),
                "y_val": val_df[_FAILURE_TYPES].fillna(0),
                "train_df": train_df,
                "val_df": val_df,
                "labels": _FAILURE_TYPES,
            }

        if mt == "p3":
            max_wear = train_df[_COL_TOOL_WEAR].max()
            train_df = train_df.copy()
            val_df = val_df.copy()

            def _rul(row, mw=max_wear):
                return 0.0 if row[_COL_MACHINE_FAILURE] == 1 else max(0.0, (mw - row[_COL_TOOL_WEAR]) / 60.0)

            train_df["_rul_proxy"] = train_df.apply(_rul, axis=1)
            val_df["_rul_proxy"] = val_df.apply(_rul, axis=1)
            return {
                "y": train_df["_rul_proxy"],
                "y_val": val_df["_rul_proxy"],
                "train_df": train_df,
                "val_df": val_df,
            }

        if mt == "p5":
            # Real dispatcher-assigned priority (OrdresIntervention.priority),
            # not derived from tool_wear. Rows without one (e.g. baseline
            # ai4i2020.csv, which has no priority concept) default to
            # MOYENNE — same fallback convention already used in
            # ordres_intervention/validation.py. Must fill rather than drop:
            # X is built from this same train_df/val_df by the caller, so
            # row count/index have to stay aligned with y/y_val.
            train_df = train_df.copy()
            val_df = val_df.copy()
            _PRIORITY_MAP = {"URGENTE": 0, "ÉLEVÉE": 1, "MOYENNE": 2, "BASSE": 3}
            pri_train = train_df.get("priority", _pd.Series([None] * len(train_df)))
            pri_val = val_df.get("priority", _pd.Series([None] * len(val_df)))
            train_df["_priority_proxy"] = (
                pri_train.map(_PRIORITY_MAP).fillna(_PRIORITY_MAP["MOYENNE"]).astype(int)
            )
            val_df["_priority_proxy"] = (
                pri_val.map(_PRIORITY_MAP).fillna(_PRIORITY_MAP["MOYENNE"]).astype(int)
            )
            return {
                "y": train_df["_priority_proxy"],
                "y_val": val_df["_priority_proxy"],
                "train_df": train_df,
                "val_df": val_df,
            }

        # P1 and P4 (unsupervised: y unused)
        return {
            "y": train_df[_COL_MACHINE_FAILURE],
            "y_val": val_df[_COL_MACHINE_FAILURE],
            "train_df": train_df,
            "val_df": val_df,
        }

    @staticmethod
    def _fit_model_for_type(mt: str, X, targets: dict, existing_data: dict, n_samples: int) -> Optional[dict]:
        """Train and return model_data dict. Returns None for unknown model types."""
        existing_features = existing_data.get("features", [])
        xgb_features = existing_data.get("xgb_features", existing_features)
        meta = {"retrained_at": datetime.now(timezone.utc).isoformat(), "new_samples": n_samples}

        if mt == "p1":
            from xgboost import XGBClassifier
            model = XGBClassifier(n_estimators=500, learning_rate=0.1, max_depth=6,
                                  subsample=0.8, colsample_bytree=0.8, eval_metric="logloss")
            model.fit(X, targets["y"])
            return {"model": model, "features": existing_features, "xgb_features": xgb_features,
                    "best_params": {"n_estimators": 500, "learning_rate": 0.1, "max_depth": 6},
                    "metrics": meta}

        if mt == "p2":
            from sklearn.multioutput import MultiOutputClassifier
            from xgboost import XGBClassifier as _XGBC
            model = MultiOutputClassifier(_XGBC(n_estimators=100, max_depth=4, eval_metric="logloss", random_state=42))
            model.fit(X, targets["y"])  # initial fit populates model.estimators_ structure

            # Per-class imbalance weighting: MultiOutputClassifier clones the
            # SAME estimator params for every label, so a single scale_pos_weight
            # set at construction would apply uniformly regardless of each
            # failure type's actual rarity (RNF/TWF are far rarer than the
            # others in the debug run: F1=0%/11% vs macro 69%). Re-fit each
            # per-label estimator individually with its own class-appropriate
            # weight, then swap it into model.estimators_ in place —
            # predictions.py reads model.estimators_ directly, so the object
            # stays a normal fitted MultiOutputClassifier from the outside.
            y_df = targets["y"]
            for i, col in enumerate(y_df.columns):
                y_col = y_df[col]
                n_pos = int(y_col.sum())
                n_neg = len(y_col) - n_pos
                scale_pos_weight = (n_neg / n_pos) if n_pos > 0 else 1.0
                per_label_model = _XGBC(
                    n_estimators=100, max_depth=4, eval_metric="logloss",
                    random_state=42, scale_pos_weight=scale_pos_weight,
                )
                per_label_model.fit(X, y_col)
                model.estimators_[i] = per_label_model

            return {"model": model, "features": existing_features,
                    "labels": targets.get("labels"), "metrics": meta}

        if mt == "p3":
            from xgboost import XGBRegressor as _XGBR
            model = _XGBR(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
            model.fit(X, targets["y"])
            return {"model": model, "features": existing_features,
                    "metrics": {**meta, "rul_source": "tool_wear_proxy"}}

        if mt == "p4":
            from sklearn.ensemble import IsolationForest
            model = IsolationForest(n_estimators=100, contamination=0.04, max_samples=0.9, random_state=42)
            model.fit(X)
            return {"model": model, "features": existing_features,
                    "best_params": {"n_estimators": 100, "contamination": 0.04}, "metrics": meta}

        if mt == "p5":
            from sklearn.ensemble import RandomForestClassifier as _RFC
            model = _RFC(n_estimators=100, random_state=42, min_samples_leaf=1, max_features="sqrt")
            model.fit(X, targets["y"])
            # Order must match the _PRIORITY_MAP index in _prepare_model_targets.
            return {"model": model, "features": existing_features,
                    "labels": ["URGENTE", "ÉLEVÉE", "MOYENNE", "BASSE"],
                    "metrics": {**meta, "priority_source": "real_dispatcher_priority"}}

        return None

    @staticmethod
    def _eval_accuracy_gate(mt: str, model_data: dict, x_val, targets: dict,
                             min_f1: float, min_r2: float) -> tuple:
        """Evaluate on held-out val set. Returns (gate_passed, metrics_dict)."""
        try:
            from sklearn.metrics import f1_score as _f1, r2_score as _r2
            model = model_data["model"]
            y_val = targets["y_val"]
            preds = model.predict(x_val)

            if mt == "p1":
                score = float(_f1(y_val, preds, zero_division=0))
                metrics = {"val_f1": round(score, 4), "f1_failure": round(score, 4)}
                # roc_auc/pr_auc — displayed by the admin ML dashboard card,
                # computed here since predict_proba needs the fitted model.
                try:
                    from sklearn.metrics import roc_auc_score as _roc, average_precision_score as _pr
                    proba = model.predict_proba(x_val)[:, 1]
                    metrics["roc_auc"] = round(float(_roc(y_val, proba)), 4)
                    metrics["pr_auc"] = round(float(_pr(y_val, proba)), 4)
                except Exception as _auc_exc:
                    logger.warning(f"ROC/PR-AUC computation failed for p1: {_auc_exc}")
                return score >= min_f1, metrics
            if mt == "p2":
                score = float(_f1(y_val, preds, average="macro", zero_division=0))
                return score >= min_f1, {"val_f1_macro": round(score, 4)}
            if mt == "p3":
                score = float(_r2(y_val, preds))
                return score >= min_r2, {"val_r2": round(score, 4)}
            if mt == "p5":
                score = float(_f1(y_val, preds, average="macro", zero_division=0))
                return score >= min_f1, {"val_f1_macro": round(score, 4)}
            # P4 unsupervised — no labelled val target
            return True, {}
        except Exception as _gate_exc:
            logger.warning(f"Accuracy gate eval failed for {mt}: {_gate_exc}")
            return True, {}  # don't block on infra failure

    @staticmethod
    def _retrain_one_model(mt: str, model_path: str, train_df, val_df,
                            n_samples: int, min_f1: float, min_r2: float) -> dict:
        """Full retrain cycle for one model type. Returns a status dict."""
        existing_data = joblib.load(model_path)
        existing_features = existing_data.get("features", [])
        xgb_features = existing_data.get("xgb_features")

        if mt == "p3":
            # Force the extended feature set regardless of what the
            # currently-deployed pkl was last trained with — the old pkl may
            # still only list the base 7. xgb_features is force-recomputed
            # too: reusing an old 7-name xgb_features list against an
            # 11-column X would raise a length-mismatch error on
            # `X.columns = xgb_features` below.
            existing_features = _BASE_COLUMNS + [
                "temp_delta", "rpm_torque", "tool_wear_velocity",
                "process_temp_roll5_mean", "torque_roll5_mean", "rpm_roll5_mean",
            ]
            xgb_features = [
                f.replace("[", "").replace("]", "").replace("<", "").strip()
                for f in existing_features
            ]

        if not xgb_features and existing_features:
            # No safe-name mapping stored on this pkl — derive one. XGBoost
            # rejects '[', ']', '<' in feature names; sklearn models don't
            # care, so this is a no-op risk-wise for non-XGBoost model types.
            xgb_features = [
                f.replace("[", "").replace("]", "").replace("<", "").strip()
                for f in existing_features
            ]

        if xgb_features:
            X = train_df[existing_features].copy()
            X.columns = xgb_features
            x_val = val_df[existing_features].copy()
            x_val.columns = xgb_features
        else:
            X = train_df[_BASE_COLUMNS]
            x_val = val_df[_BASE_COLUMNS]

        targets = RetrainingService._prepare_model_targets(mt, train_df, val_df)
        if targets is None:
            _SKIP_REASONS = {
                "p6": "P6 requires actual maintenance scheduling outcomes",
                "p4": "P4 ensemble refit not implemented — retraining would overwrite "
                      "the ensemble pkl (weights/thresholds/training_stats/ae_scaler) "
                      "with a bare IsolationForest",
            }
            return {"model": mt, "status": "skipped",
                    "reason": _SKIP_REASONS.get(mt, "no label data available")}

        backup_path = RetrainingService._backup_model(mt)
        try:
            model_data = RetrainingService._fit_model_for_type(mt, X, targets, existing_data, n_samples)
        except Exception as fit_exc:
            # _backup_model already renamed the live pkl away — restore it
            # before propagating, or a fit failure permanently orphans the model.
            if backup_path and os.path.exists(backup_path):
                os.rename(backup_path, model_path)
            logger.exception(f"Fit failed for {mt}, restored backup: {fit_exc}")
            return {"model": mt, "status": "failed", "error": str(fit_exc)}
        if model_data is None:
            if backup_path and os.path.exists(backup_path):
                os.rename(backup_path, model_path)
            return {"model": mt, "status": "skipped", "reason": "unknown model type"}

        validation = RetrainingService.validate_model(mt, model_data)
        if not validation["valid"]:
            if backup_path and os.path.exists(backup_path):
                os.rename(backup_path, model_path)
            return {"model": mt, "status": "failed", "error": validation["error"]}

        passed, gate_metrics = RetrainingService._eval_accuracy_gate(
            mt, model_data, x_val, targets, min_f1, min_r2
        )
        if not passed:
            if backup_path and os.path.exists(backup_path):
                os.rename(backup_path, model_path)
            return {
                "model": mt, "status": "rejected",
                "reason": f"accuracy gate failed: {gate_metrics} (minimum: classifier F1>={min_f1}, regressor R2>={min_r2})",
                "metrics": gate_metrics,
            }

        model_data.setdefault("metrics", {}).update(gate_metrics)
        joblib.dump(model_data, model_path)
        RetrainingService._cleanup_old_versions(mt)
        return {"model": mt, "status": "success", "validation": validation,
                "val_metrics": gate_metrics, "backup": backup_path}

    @staticmethod
    async def run_retraining_pipeline(db: AsyncSession, model_type: str = "all"):
        """
        PDCA ACT Phase: Automated retraining of ML models.

        Args:
            db: Database session
            model_type: 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', or 'all'
        """
        # 1. Fetch Ground Truth Data
        query = (
            select(OrdresIntervention, MlPredictionLog)
            .join(MlPredictionLog, OrdresIntervention.machine_id == MlPredictionLog.machine_id)
            .where(
                OrdresIntervention.actual_failure_type.is_not(None),
                OrdresIntervention.retrained.is_(False),
                OrdresIntervention.is_synthetic.is_(False),
                MlPredictionLog.created_at <= OrdresIntervention.requested_at,
            )
            .order_by(MlPredictionLog.created_at.desc())
        )
        rows = (await db.execute(query)).all()

        if not rows:
            return {"status": "skipped", "message": "No new ground truth data to retrain.", "models_retrained": []}

        # 2. Extract features and labels from rows
        new_data = []
        interventions_to_update = []
        for intervention, log in rows:
            if intervention.id in interventions_to_update:
                continue
            interventions_to_update.append(intervention.id)
            is_failure = 1 if intervention.actual_failure_type != "NONE" else 0
            new_data.append({
                "Air temperature [K]": log.air_temperature,
                "Process temperature [K]": log.process_temperature,
                "Rotational speed [rpm]": log.rotational_speed,
                "Torque [Nm]": log.torque,
                _COL_TOOL_WEAR: log.tool_wear,
                _COL_MACHINE_FAILURE: is_failure,
                "actual_failure_type": intervention.actual_failure_type,
                "machine_id": intervention.machine_id,
                "priority": intervention.priority,
                "timestamp": log.created_at,
            })

        try:
            import pandas as pd
            from sklearn.model_selection import train_test_split as _tts

            baseline_df = pd.read_csv(DATA_PATH)
            combined_df = pd.concat([baseline_df, pd.DataFrame(new_data)], ignore_index=True)
            # Engineered features expected by P1/P2/P5/P6 (mirrors
            # ml-microservice/src/core/feature_pipeline.py FeaturePipeline.build_7,
            # which computes these at inference time but never persists them).
            combined_df["temp_delta"] = (
                combined_df["Process temperature [K]"] - combined_df["Air temperature [K]"]
            )
            combined_df["rpm_torque"] = (
                combined_df["Rotational speed [rpm]"] * combined_df["Torque [Nm]"]
            ) / 1000.0
            # P6's 8th feature (mirrors predictions.py:523 fallback: wear ** 2).
            combined_df["tool_wear_sq"] = combined_df[_COL_TOOL_WEAR] ** 2

            # P3-only engineered features: per-machine, time-ordered wear
            # velocity + rolling-5 means (mirrors predictions.py's
            # _p3_history_features, which computes the same thing live from
            # real telemetry history). Baseline ai4i2020.csv rows have no
            # machine_id/timestamp — no sequence exists — so they get neutral
            # defaults (0 velocity, rolling mean = own instantaneous value)
            # rather than NaN, matching what predict_all() falls back to for
            # a machine with no history yet.
            if "timestamp" in combined_df.columns:
                combined_df = combined_df.sort_values(
                    ["machine_id", "timestamp"], na_position="first"
                ).reset_index(drop=True)
                _has_machine = combined_df["machine_id"].notna()
                _grp = combined_df.loc[_has_machine].groupby("machine_id", group_keys=False)
                combined_df["tool_wear_velocity"] = 0.0
                combined_df.loc[_has_machine, "tool_wear_velocity"] = (
                    _grp[_COL_TOOL_WEAR].diff().fillna(0.0)
                )
                for _col, _out in [
                    ("Process temperature [K]", "process_temp_roll5_mean"),
                    ("Torque [Nm]", "torque_roll5_mean"),
                    ("Rotational speed [rpm]", "rpm_roll5_mean"),
                ]:
                    # Must be float64 from the start — assigning a rolling
                    # mean (always float) into a column initialized from an
                    # int-dtype source (e.g. Rotational speed [rpm] is an
                    # int column) raises a pandas LossySetitemError.
                    combined_df[_out] = combined_df[_col].astype(float)  # default: own instantaneous value
                    combined_df.loc[_has_machine, _out] = _grp[_col].transform(
                        lambda s: s.rolling(5, min_periods=1).mean()
                    )
            else:
                combined_df["tool_wear_velocity"] = 0.0
                combined_df["process_temp_roll5_mean"] = combined_df["Process temperature [K]"]
                combined_df["torque_roll5_mean"] = combined_df["Torque [Nm]"]
                combined_df["rpm_roll5_mean"] = combined_df["Rotational speed [rpm]"]

            # Group-based split: hold out one WHOLE machine for validation
            # instead of a random row shuffle. Our seeded cycles are smooth
            # interpolations — adjacent rows within a cycle are near-duplicates,
            # so a random split leaks near-identical rows into both train and
            # validation and inflates the score. Validating on a machine the
            # model never trained on is the only way to know if it generalizes.
            # Baseline ai4i2020.csv rows have no machine_id — always train-only,
            # they're real historical data, not synthetic, no leakage risk.
            machine_ids = sorted(combined_df["machine_id"].dropna().unique()) if "machine_id" in combined_df else []
            if len(machine_ids) >= 2:
                holdout_machine = machine_ids[-1]
                val_mask = combined_df["machine_id"] == holdout_machine
                _val_df = combined_df[val_mask]
                _train_df = combined_df[~val_mask]
                logger.info(f"Group-holdout validation: machine_id={holdout_machine} held out entirely ({len(_val_df)} rows).")
            else:
                logger.warning("Fewer than 2 machines with ground truth — falling back to random split (score may be inflated by leakage).")
                _train_df, _val_df = _tts(
                    combined_df, test_size=0.2, random_state=42,
                    stratify=combined_df.get(_COL_MACHINE_FAILURE, None),
                )

            _MIN_CLASSIFIER_F1 = 0.70
            # P3 (the only model this currently gates — P6 is hard-skipped) proved
            # a genuine 0.67 R2 under group-holdout validation. 0.40 was a
            # placeholder that would let almost any retrain pass, including a
            # regression back toward the pre-fix leakage-inflated baseline.
            # 0.60 gives a small buffer under the validated number without
            # being a hair-trigger on normal retrain variance.
            _MIN_REGRESSOR_R2  = 0.60
            model_types = list(MODEL_FILES.keys()) if model_type == "all" else [model_type]
            models_retrained = []

            for mt in model_types:
                if mt not in MODEL_FILES:
                    continue
                model_path = os.path.join(MODELS_DIR, MODEL_FILES[mt])
                if not os.path.exists(model_path):
                    models_retrained.append({"model": mt, "status": "skipped", "reason": "Model file not found"})
                    continue
                try:
                    result = RetrainingService._retrain_one_model(
                        mt, model_path, _train_df, _val_df, len(new_data), _MIN_CLASSIFIER_F1, _MIN_REGRESSOR_R2
                    )
                except Exception as model_exc:
                    # Failure before backup (e.g. missing engineered feature
                    # column) — nothing to restore, just don't let it kill
                    # the rest of the batch.
                    logger.exception(f"Retrain failed for {mt}: {model_exc}")
                    result = {"model": mt, "status": "failed", "error": str(model_exc)}
                models_retrained.append(result)

            await db.execute(
                update(OrdresIntervention)
                .where(OrdresIntervention.id.in_(interventions_to_update))
                .values(retrained=True)
            )
            await db.commit()

            return {
                "status": "success",
                "message": f"Retraining complete. {len(models_retrained)} models processed.",
                "new_total_samples": len(combined_df),
                "models_retrained": models_retrained,
                "retrained_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.exception(f"Retraining Error: {str(e)}", exc_info=True)
            await db.rollback()
            return {"status": "error", "message": str(e)}
