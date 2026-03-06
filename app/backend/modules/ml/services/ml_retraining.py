import os
import joblib
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from models.ordres_intervention import Ordres_intervention
from models.ml_prediction_log import MlPredictionLog
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai4i2020.csv')

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
    async def run_retraining_pipeline(db: AsyncSession):
        """
        PDCA ACT Phase: Automated retraining of the failure prediction model (P1).
        
        Steps:
        1. Fetch all 'retrained=False' interventions with ground truth.
        2. Correlate with 'MlPredictionLog' snapshots.
        3. Load baseline ai4i2020.csv data.
        4. Incremental update or full refit of the XGBoost model.
        5. Save model and mark interventions as 'retrained=True'.
        """
        # 1. Fetch Ground Truth Data from DB
        query = select(Ordres_intervention, MlPredictionLog).join(
            MlPredictionLog, 
            Ordres_intervention.machine_id == MlPredictionLog.machine_id
        ).where(
            Ordres_intervention.actual_failure_type != None,
            Ordres_intervention.retrained == False,
            # Ensure the log happened close to the intervention request
            MlPredictionLog.created_at <= Ordres_intervention.requested_at
        ).order_by(MlPredictionLog.created_at.desc())
        
        result = await db.execute(query)
        rows = result.all()
        
        if not rows:
            return {"status": "skipped", "message": "No new ground truth data to retrain."}

        # 2. Extract Features and Labels
        new_data = []
        interventions_to_update = []
        
        for intervention, log in rows:
            # Avoid duplicate logs for the same intervention if many predictions happened
            if intervention.id in interventions_to_update:
                continue
                
            interventions_to_update.append(intervention.id)
            
            # Map ACTUAL failure type to binary failure (0 or 1)
            is_failure = 1 if intervention.actual_failure_type != "NONE" else 0
            
            new_data.append({
                "Air temperature [K]": log.air_temperature,
                "Process temperature [K]": log.process_temperature,
                "Rotational speed [rpm]": log.rotational_speed,
                "Torque [Nm]": log.torque,
                "Tool wear [min]": log.tool_wear,
                "Machine failure": is_failure
            })

        # 3. Load Baseline Data
        try:
            baseline_df = pd.read_csv(DATA_PATH)
            # Standardize column names if needed
            new_df = pd.DataFrame(new_data)
            
            # 4. Prepare Training Set (Upsampling new data could be done here)
            # For simplicity, we just concatenate and refit.
            # In a real system, we might use weighted sampling to favor recent data.
            combined_df = pd.concat([baseline_df, new_df], ignore_index=True)
            
            X = combined_df[["Air temperature [K]", "Process temperature [K]", 
                             "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]]
            y = combined_df["Machine failure"]

            # 5. Fit & Save Model (P1)
            model_p1 = XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            model_p1.fit(X, y)
            
            # Save the new model
            p1_path = os.path.join(MODELS_DIR, 'basic_machine_model.pkl')
            # Backup old model
            if os.path.exists(p1_path):
                os.rename(p1_path, f"{p1_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            joblib.dump(model_p1, p1_path)
            
            # 6. Mark as Retrained in DB
            await db.execute(
                update(Ordres_intervention)
                .where(Ordres_intervention.id.in_(interventions_to_update))
                .values(retrained=True)
            )
            await db.commit()

            return {
                "status": "success", 
                "message": f"Model P1 retrained with {len(new_data)} new samples.",
                "new_total_samples": len(combined_df)
            }
            
        except Exception as e:
            logger.error(f"Retraining Error: {str(e)}", exc_info=True)
            await db.rollback()
            return {"status": "error", "message": str(e)}
