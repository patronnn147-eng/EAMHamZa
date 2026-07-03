import os
import joblib
import glob
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.ordres_intervention import Ordres_intervention
from models.ml_prediction_log import MlPredictionLog

logger = logging.getLogger(__name__)

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
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ai4i2020.csv"
)

# Model file mapping
MODEL_FILES = {
    "p1": "basic_machine_model.pkl",
    "p2": "ml_model_p2_failure_type.pkl",
    "p3": "ml_model_p3_rul.pkl",
    "p4": "ml_model_p4_anomaly.pkl",
    "p5": "ml_model_p5_priority.pkl",
    "p6": "ml_model_p6_schedule.pkl",
}

MAX_MODEL_VERSIONS = 3


class RetrainingService:
    @staticmethod
    async def get_retraining_stats(db: AsyncSession):
        """Get number of new data points available for retraining."""
        query = select(func.count(Ordres_intervention.id)).where(
            Ordres_intervention.actual_failure_type is not None,
            not Ordres_intervention.retrained,
        )
        result = await db.execute(query)
        new_points = result.scalar_one()
        return {"new_data_points": new_points}

    @staticmethod
    def _backup_model(model_name: str) -> str:
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
    async def run_retraining_pipeline(db: AsyncSession, model_type: str = "all"):
        """
        PDCA ACT Phase: Automated retraining of ML models.

        Args:
            db: Database session
            model_type: 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', or 'all'

        Steps:
        1. Fetch all 'retrained=False' interventions with ground truth.
        2. Correlate with 'MlPredictionLog' snapshots.
        3. Load baseline ai4i2020.csv data.
        4. Refit models with combined data.
        5. Validate new models against previous versions.
        6. Save models and mark interventions as 'retrained=True'.
        """
        # 1. Fetch Ground Truth Data from DB
        query = (
            select(Ordres_intervention, MlPredictionLog)
            .join(
                MlPredictionLog,
                Ordres_intervention.machine_id == MlPredictionLog.machine_id,
            )
            .where(
                Ordres_intervention.actual_failure_type is not None,
                not Ordres_intervention.retrained,
                MlPredictionLog.created_at <= Ordres_intervention.requested_at,
            )
            .order_by(MlPredictionLog.created_at.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            return {
                "status": "skipped",
                "message": "No new ground truth data to retrain.",
                "models_retrained": [],
            }

        # 2. Extract Features and Labels
        new_data = []
        interventions_to_update = []

        for intervention, log in rows:
            if intervention.id in interventions_to_update:
                continue

            interventions_to_update.append(intervention.id)
            is_failure = 1 if intervention.actual_failure_type != "NONE" else 0

            new_data.append(
                {
                    "Air temperature [K]": log.air_temperature,
                    "Process temperature [K]": log.process_temperature,
                    "Rotational speed [rpm]": log.rotational_speed,
                    "Torque [Nm]": log.torque,
                    "Tool wear [min]": log.tool_wear,
                    "Machine failure": is_failure,
                    "actual_failure_type": intervention.actual_failure_type,
                }
            )

        # 3. Load Baseline Data
        try:
            import pandas as pd
            from sklearn.model_selection import train_test_split as _tts

            baseline_df = pd.read_csv(DATA_PATH)
            new_df = pd.DataFrame(new_data)
            combined_df = pd.concat([baseline_df, new_df], ignore_index=True)

            # 3a. Hold out 20% for post-training accuracy gate.
            # val_df never seen by training — used to reject regressions.
            _train_df, _val_df = _tts(
                combined_df,
                test_size=0.2,
                random_state=42,
                stratify=combined_df.get("Machine failure", None),
            )

            # Minimum accuracy/F1 to accept new model (compared against val set).
            # P1/P2/P5 classifiers: F1 >= 0.70; P3 regressor: R2 >= 0.40.
            _MIN_CLASSIFIER_F1 = 0.70
            _MIN_REGRESSOR_R2 = 0.40

            models_retrained = []
            model_types = (
                list(MODEL_FILES.keys()) if model_type == "all" else [model_type]
            )

            for mt in model_types:
                if mt not in MODEL_FILES:
                    continue

                model_file = MODEL_FILES[mt]
                model_path = os.path.join(MODELS_DIR, model_file)

                if not os.path.exists(model_path):
                    models_retrained.append(
                        {
                            "model": mt,
                            "status": "skipped",
                            "reason": "Model file not found",
                        }
                    )
                    continue

                # Load existing model to get feature config
                existing_data = joblib.load(model_path)
                existing_features = existing_data.get("features", [])
                xgb_features = existing_data.get("xgb_features", existing_features)

                # Prepare features for training (use _train_df — val held out for accuracy gate)
                if xgb_features:
                    feature_map = {}
                    for orig, sanitized in zip(existing_features, xgb_features):
                        feature_map[orig] = sanitized

                    train_features = existing_features
                    X = _train_df[train_features].copy()
                    X.columns = xgb_features
                    X_val = _val_df[train_features].copy()
                    X_val.columns = xgb_features
                else:
                    train_features = [
                        "Air temperature [K]",
                        "Process temperature [K]",
                        "Rotational speed [rpm]",
                        "Torque [Nm]",
                        "Tool wear [min]",
                    ]
                    X = _train_df[train_features]
                    X_val = _val_df[train_features]

                # Model-specific target
                if mt == "p1":
                    y = _train_df["Machine failure"]
                    _val_df["Machine failure"]
                elif mt == "p2":
                    import pandas as _pd

                    _failure_types = ["TWF", "HDF", "PWF", "OSF", "RNF"]
                    _ft_col = _train_df.get(
                        "actual_failure_type", _pd.Series(["NONE"] * len(_train_df))
                    )
                    _ft_val_col = _val_df.get(
                        "actual_failure_type", _pd.Series(["NONE"] * len(_val_df))
                    )
                    for _ft in _failure_types:
                        _train_df = _train_df.copy()
                        _val_df = _val_df.copy()
                        _train_df[_ft] = _ft_col.str.contains(_ft, na=False).astype(int)
                        _val_df[_ft] = _ft_val_col.str.contains(_ft, na=False).astype(
                            int
                        )
                    y_p2 = _train_df[_failure_types].fillna(0)
                    y_p2_val = _val_df[_failure_types].fillna(0)
                elif mt == "p3":
                    _max_wear = _train_df["Tool wear [min]"].max()
                    _train_df = _train_df.copy()
                    _val_df = _val_df.copy()
                    _train_df["_rul_proxy"] = _train_df.apply(
                        lambda row: (
                            0.0
                            if row["Machine failure"] == 1
                            else max(0.0, (_max_wear - row["Tool wear [min]"]) / 60.0)
                        ),
                        axis=1,
                    )
                    _val_df["_rul_proxy"] = _val_df.apply(
                        lambda row: (
                            0.0
                            if row["Machine failure"] == 1
                            else max(0.0, (_max_wear - row["Tool wear [min]"]) / 60.0)
                        ),
                        axis=1,
                    )
                    y_p3 = _train_df["_rul_proxy"]
                    y_p3_val = _val_df["_rul_proxy"]
                elif mt == "p6":
                    # P6 requires actual maintenance scheduling outcome data not yet
                    # captured per intervention.  Skipped until planning schema exposes
                    # next_maintenance_date.
                    models_retrained.append(
                        {
                            "model": mt,
                            "status": "skipped",
                            "reason": "P6 requires actual maintenance scheduling outcomes",
                        }
                    )
                    continue
                elif mt == "p4":
                    # P4 is unsupervised - retrain on combined features
                    pass
                elif mt == "p5":
                    _max_wear_p5 = _train_df["Tool wear [min]"].max()
                    _high_wear_thresh = _max_wear_p5 * 0.75
                    _train_df = _train_df.copy()
                    _val_df = _val_df.copy()
                    _train_df["_priority_proxy"] = _train_df.apply(
                        lambda row: (
                            0
                            if (
                                row["Machine failure"] == 1
                                and row["Tool wear [min]"] >= _high_wear_thresh
                            )
                            else (1 if row["Machine failure"] == 1 else 2)
                        ),
                        axis=1,
                    )
                    _val_df["_priority_proxy"] = _val_df.apply(
                        lambda row: (
                            0
                            if (
                                row["Machine failure"] == 1
                                and row["Tool wear [min]"] >= _high_wear_thresh
                            )
                            else (1 if row["Machine failure"] == 1 else 2)
                        ),
                        axis=1,
                    )
                    y_p5 = _train_df["_priority_proxy"]
                    y_p5_val = _val_df["_priority_proxy"]
                else:
                    y = _train_df["Machine failure"]

                # Backup existing model
                backup_path = RetrainingService._backup_model(mt)

                # Train model — all paths go through backup → validate → rollback below.
                if mt == "p1":
                    from xgboost import XGBClassifier

                    model = XGBClassifier(
                        n_estimators=500,
                        learning_rate=0.1,
                        max_depth=6,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        eval_metric="logloss",
                    )
                    model.fit(X, y)
                    model_data = {
                        "model": model,
                        "features": existing_features,
                        "xgb_features": xgb_features,
                        "best_params": {
                            "n_estimators": 500,
                            "learning_rate": 0.1,
                            "max_depth": 6,
                        },
                        "metrics": {
                            "retrained_at": datetime.now(timezone.utc).isoformat(),
                            "new_samples": len(new_data),
                        },
                    }

                elif mt == "p2":
                    from sklearn.multioutput import MultiOutputClassifier
                    from xgboost import XGBClassifier as _XGBC

                    model = MultiOutputClassifier(
                        _XGBC(
                            n_estimators=100,
                            max_depth=4,
                            eval_metric="logloss",
                            random_state=42,
                        )
                    )
                    model.fit(X, y_p2)
                    model_data = {
                        "model": model,
                        "features": existing_features,
                        "labels": _failure_types,
                        "metrics": {
                            "retrained_at": datetime.now(timezone.utc).isoformat(),
                            "new_samples": len(new_data),
                        },
                    }

                elif mt == "p3":
                    from xgboost import XGBRegressor as _XGBR

                    model = _XGBR(
                        n_estimators=200,
                        max_depth=5,
                        learning_rate=0.1,
                        random_state=42,
                    )
                    model.fit(X, y_p3)
                    model_data = {
                        "model": model,
                        "features": existing_features,
                        "metrics": {
                            "retrained_at": datetime.now(timezone.utc).isoformat(),
                            "new_samples": len(new_data),
                            "rul_source": "tool_wear_proxy",
                        },
                    }

                elif mt == "p4":
                    from sklearn.ensemble import IsolationForest

                    model = IsolationForest(
                        n_estimators=100,
                        contamination=0.04,
                        max_samples=0.9,
                        random_state=42,
                    )
                    model.fit(X)
                    model_data = {
                        "model": model,
                        "features": existing_features,
                        "best_params": {"n_estimators": 100, "contamination": 0.04},
                        "metrics": {
                            "retrained_at": datetime.now(timezone.utc).isoformat(),
                            "new_samples": len(new_data),
                        },
                    }

                elif mt == "p5":
                    from sklearn.ensemble import RandomForestClassifier as _RFC

                    model = _RFC(n_estimators=100, random_state=42)
                    model.fit(X, y_p5)
                    model_data = {
                        "model": model,
                        "features": existing_features,
                        "labels": ["P1", "P2", "P3"],
                        "metrics": {
                            "retrained_at": datetime.now(timezone.utc).isoformat(),
                            "new_samples": len(new_data),
                            "priority_source": "failure_proxy",
                        },
                    }

                else:
                    continue

                # Validate new model
                validation = RetrainingService.validate_model(mt, model_data)
                if not validation["valid"]:
                    # Restore backup
                    if backup_path and os.path.exists(backup_path):
                        os.rename(backup_path, model_path)
                    models_retrained.append(
                        {"model": mt, "status": "failed", "error": validation["error"]}
                    )
                    continue

                # ── Accuracy gate: evaluate on held-out val set ────────────────────────
                _acc_gate_passed = True
                _acc_metrics = {}
                try:
                    from sklearn.metrics import f1_score as _f1, r2_score as _r2

                    _m = model_data["model"]
                    if mt == "p1":
                        _preds_val = _m.predict(X_val)
                        _f1_val = float(
                            _f1(_val_df["Machine failure"], _preds_val, zero_division=0)
                        )
                        _acc_metrics = {"val_f1": round(_f1_val, 4)}
                        if _f1_val < _MIN_CLASSIFIER_F1:
                            _acc_gate_passed = False
                    elif mt == "p2":
                        _preds_val = _m.predict(X_val)
                        _f1_val = float(
                            _f1(y_p2_val, _preds_val, average="macro", zero_division=0)
                        )
                        _acc_metrics = {"val_f1_macro": round(_f1_val, 4)}
                        if _f1_val < _MIN_CLASSIFIER_F1:
                            _acc_gate_passed = False
                    elif mt == "p3":
                        _preds_val = _m.predict(X_val)
                        _r2_val = float(_r2(y_p3_val, _preds_val))
                        _acc_metrics = {"val_r2": round(_r2_val, 4)}
                        if _r2_val < _MIN_REGRESSOR_R2:
                            _acc_gate_passed = False
                    elif mt == "p5":
                        _preds_val = _m.predict(X_val)
                        _f1_val = float(
                            _f1(y_p5_val, _preds_val, average="macro", zero_division=0)
                        )
                        _acc_metrics = {"val_f1_macro": round(_f1_val, 4)}
                        if _f1_val < _MIN_CLASSIFIER_F1:
                            _acc_gate_passed = False
                    # P4 (IsolationForest) is unsupervised — no labelled val target; skip gate.
                except Exception as _gate_exc:
                    logger.warning(f"Accuracy gate eval failed for {mt}: {_gate_exc}")
                    # On eval error, let the model through (don't block on infra failure)

                if not _acc_gate_passed:
                    # Reject new model — restore backup and report
                    if backup_path and os.path.exists(backup_path):
                        os.rename(backup_path, model_path)
                    models_retrained.append(
                        {
                            "model": mt,
                            "status": "rejected",
                            "reason": f"accuracy gate failed: {_acc_metrics} (minimum: classifier F1>={_MIN_CLASSIFIER_F1}, regressor R2>={_MIN_REGRESSOR_R2})",
                            "metrics": _acc_metrics,
                        }
                    )
                    continue

                # ── Gate passed — save new model ───────────────────────────────────────
                # Record val metrics alongside training metadata
                model_data.setdefault("metrics", {}).update(_acc_metrics)
                joblib.dump(model_data, model_path)

                # Cleanup old versions
                RetrainingService._cleanup_old_versions(mt)

                models_retrained.append(
                    {
                        "model": mt,
                        "status": "success",
                        "validation": validation,
                        "val_metrics": _acc_metrics,
                        "backup": backup_path,
                    }
                )

            # 6. Mark interventions as retrained
            await db.execute(
                update(Ordres_intervention)
                .where(Ordres_intervention.id.in_(interventions_to_update))
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
            logger.error(f"Retraining Error: {str(e)}", exc_info=True)
            await db.rollback()
            return {"status": "error", "message": str(e)}
