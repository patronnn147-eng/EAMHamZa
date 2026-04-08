import shap
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class XAIService:
    @staticmethod
    def explain_prediction(model, features: List[float], feature_names: List[str]) -> List[Dict]:
        """
        Generate SHAP explanations for a single prediction.
        
        Args:
            model: The trained ML model (Scikit-learn or XGBoost).
            features: [air_temp, process_temp, rpm, torque, tool_wear]
            feature_names: Human-readable names for these features.
            
        Returns:
            A list of dicts: [{"factor": "Torque", "impact": "High", "direction": "Positive"}]
        """
        if model is None:
            return []

        try:
            # Create a localized dataframe for the single sample
            X = pd.DataFrame([features], columns=feature_names)
            
            # Initialize explainer. 
            # Note: For production with many calls, we should cache the explainer instance.
            actual_model = model['model'] if isinstance(model, dict) and 'model' in model else model
            explainer = shap.Explainer(actual_model, X)
            shap_values = explainer(X)

            # Extract impacts
            # shap_values.values for a single sample is a 1D array of length len(features)
            # For classifiers, it might be 3D [sample, feature, class]
            values = shap_values.values[0]
            if len(values.shape) > 1:
                # If binary classifier with 2 classes, take class 1 (failure)
                values = values[:, 1] if values.shape[1] > 1 else values.flatten()

            # Map features to their SHAP impacts
            impacts = []
            for i, name in enumerate(feature_names):
                impact_val = float(values[i])
                if abs(impact_val) > 0.01: # Threshold to ignore noise
                    impacts.append({
                        "factor": name,
                        "impact": impact_val,
                        "intensity": "high" if abs(impact_val) > 0.1 else "medium" if abs(impact_val) > 0.05 else "low"
                    })

            # Sort by absolute impact descending
            impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)
            
            return impacts[:3] # Return top 3 factors
            
        except Exception as e:
            logger.error(f"XAI Error: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_friendly_factor_name(internal_name: str) -> str:
        """Map dataset column names to user-friendly French labels."""
        mapping = {
            "Air temperature [K]": "Température Ambiante",
            "Process temperature [K]": "Température du Processus",
            "Rotational speed [rpm]": "Vitesse de Rotation",
            "Torque [Nm]": "Couple (Torque)",
            "Tool wear [min]": "Usure de l'Outil",
            "air_temperature": "Température Ambiante",
            "process_temperature": "Température du Processus",
            "rotational_speed": "Vitesse de Rotation",
            "torque": "Couple (Torque)",
            "tool_wear": "Usure de l'Outil"
        }
        return mapping.get(internal_name, internal_name)
