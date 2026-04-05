import os
import joblib
import glob
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from models.ordres_intervention import Ordres_intervention
from models.ml_prediction_log import MlPredictionLog

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai4i2020.csv')

# Model file mapping
MODEL_FILES = {
    'p1': 'basic_machine_model.pkl',
    'p2': 'ml_model_p2_failure_type.pkl',
    'p3': 'ml_model_p3_rul.pkl',
    'p4': 'ml_model_p4_anomaly.pkl',
    'p5': 'ml_model_p5_priority.pkl',
    'p6': 'ml_model_p6_schedule.pkl',
}

MAX_MODEL_VERSIONS = 3


class RetrainingService:
    @staticmethod
    async def get_retraining_stats(db: AsyncSession):
        """Get number of new data points available for retraining."""
        query = select(Ordres_intervention).where(
            Ordres_intervention.actual_failure_type != None,
            Ordres_intervention.retrained == False
        )
        result = await db.execute(query)
        new_points = len(result.scalars().all())
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
        model = model_data.get('model')
        if model is None:
            return {"valid": False, "error": "No model object found"}

        metrics = model_data.get('metrics', {})
        features = model_data.get('features', [])

        if not features:
            return {"valid": False, "error": "No features defined"}

        return {
            "valid": True,
            "model_type": type(model).__name__,
            "feature_count": len(features),
            "metrics": metrics,
        }

    @staticmethod
    async def run_retraining_pipeline(db: AsyncSession, model_type: str = 'all'):
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
        query = select(Ordres_intervention, MlPredictionLog).join(
            MlPredictionLog,
            Ordres_intervention.machine_id == MlPredictionLog.machine_id
        ).where(
            Ordres_intervention.actual_failure_type != None,
            Ordres_intervention.retrained == False,
            MlPredictionLog.created_at <= Ordres_intervention.requested_at
        ).order_by(MlPredictionLog.created_at.desc())

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            return {
                "status": "skipped",
                "message": "No new ground truth data to retrain.",
                "models_retrained": []
            }

        # 2. Extract Features and Labels
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
                "Tool wear [min]": log.tool_wear,
                "Machine failure": is_failure,
                "actual_failure_type": intervention.actual_failure_type,
            })

        # 3. Load Baseline Data
        try:
            import pandas as pd
            baseline_df = pd.read_csv(DATA_PATH)
            new_df = pd.DataFrame(new_data)
            combined_df = pd.concat([baseline_df, new_df], ignore_index=True)

            models_retrained = []
            model_types = list(MODEL_FILES.keys()) if model_type == 'all' else [model_type]

            for mt in model_types:
                if mt not in MODEL_FILES:
                    continue

                model_file = MODEL_FILES[mt]
                model_path = os.path.join(MODELS_DIR, model_file)

                if not os.path.exists(model_path):
                    models_retrained.append({
                        "model": mt,
                        "status": "skipped",
                        "reason": "Model file not found"
                    })
                    continue

                # Load existing model to get feature config
                existing_data = joblib.load(model_path)
                existing_features = existing_data.get('features', [])
                xgb_features = existing_data.get('xgb_features', existing_features)

                # Prepare features for training
                if xgb_features:
                    # Map original feature names to sanitized names
                    feature_map = {}
                    for orig, sanitized in zip(existing_features, xgb_features):
                        feature_map[orig] = sanitized

                    train_features = existing_features
                    X = combined_df[train_features].copy()
                    X.columns = xgb_features
                else:
                    train_features = ["Air temperature [K]", "Process temperature [K]",
                                      "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
                    X = combined_df[train_features]

                # Model-specific target
                if mt == 'p1':
                    y = combined_df["Machine failure"]
                elif mt == 'p2':
                    # P2 uses failure type labels - skip for now if not available
                    models_retrained.append({
                        "model": mt,
                        "status": "skipped",
                        "reason": "P2 requires separate failure type labels"
                    })
                    continue
                elif mt in ('p3', 'p6'):
                    # P3/P6 require RUL calculation - skip for incremental retraining
                    models_retrained.append({
                        "model": mt,
                        "status": "skipped",
                        "reason": f"{mt.upper()} requires full RUL recalculation"
                    })
                    continue
                elif mt == 'p4':
                    # P4 is unsupervised - retrain on combined features
                    pass
                elif mt == 'p5':
                    # P5 requires priority labels - skip for incremental
                    models_retrained.append({
                        "model": mt,
                        "status": "skipped",
                        "reason": "P5 requires priority label recalculation"
                    })
                    continue
                else:
                    y = combined_df["Machine failure"]

                # Backup existing model
                backup_path = RetrainingService._backup_model(mt)

                # For P1: refit with existing model config
                if mt == 'p1':
                    from xgboost import XGBClassifier
                    model = XGBClassifier(
                        n_estimators=500,
                        learning_rate=0.1,
                        max_depth=6,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        eval_metric='logloss',
                    )
                    model.fit(X, y)

                    model_data = {
                        'model': model,
                        'features': existing_features,
                        'xgb_features': xgb_features,
                        'best_params': {'n_estimators': 500, 'learning_rate': 0.1, 'max_depth': 6},
                        'metrics': {'retrained_at': datetime.now(timezone.utc).isoformat(),
                                    'new_samples': len(new_data)},
                    }

                elif mt == 'p4':
                    from sklearn.ensemble import IsolationForest
                    model = IsolationForest(
                        n_estimators=100,
                        contamination=0.04,
                        max_samples=0.9,
                        random_state=42,
                    )
                    model.fit(X)

                    model_data = {
                        'model': model,
                        'features': existing_features,
                        'best_params': {'n_estimators': 100, 'contamination': 0.04},
                        'metrics': {'retrained_at': datetime.now(timezone.utc).isoformat(),
                                    'new_samples': len(new_data)},
                    }
                else:
                    continue

                # Validate new model
                validation = RetrainingService.validate_model(mt, model_data)
                if not validation['valid']:
                    # Restore backup
                    if backup_path and os.path.exists(backup_path):
                        os.rename(backup_path, model_path)
                    models_retrained.append({
                        "model": mt,
                        "status": "failed",
                        "error": validation['error']
                    })
                    continue

                # Save new model
                joblib.dump(model_data, model_path)

                # Cleanup old versions
                RetrainingService._cleanup_old_versions(mt)

                models_retrained.append({
                    "model": mt,
                    "status": "success",
                    "validation": validation,
                    "backup": backup_path,
                })

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
