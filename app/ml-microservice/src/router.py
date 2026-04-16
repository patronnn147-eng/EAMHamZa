"""
ML Router - FastAPI routes for ML microservice
Provides all P1-P6 prediction endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict
from .predictions import MachineLearningService
from .model_loader import get_all_models_status
from .feature_store import feature_store
from .model_registry import registry

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])


# ==================== Request Models ====================
class TelemetryInput(BaseModel):
    """Input telemetry data for predictions."""
    air_temperature:    float
    process_temperature: float
    rotational_speed:   int
    torque:             float
    tool_wear:          int
    machine_id:         Optional[int] = -1
    _logs:              Optional[List[Dict]] = None

    class Config:
        populate_by_name = True


class RULInput(BaseModel):
    """Input for RUL calculation."""
    machine_id: Optional[int] = None
    air_temperature: float
    process_temperature: float
    rotational_speed: int
    torque: float
    tool_wear: int
    mtbf_days: Optional[float] = None  # Mean Time Between Failures


# ==================== Response Models ====================
class PredictionResponse(BaseModel):
    """Response for single prediction."""
    success: bool
    prediction: Dict


class AllPredictionsResponse(BaseModel):
    """Response for all P1-P6 predictions."""
    success: bool
    predictions: Dict


class ModelsStatusResponse(BaseModel):
    """Response for models status check."""
    success: bool
    models: Dict


# ==================== Endpoints ====================

@router.get("/health")
async def health():
    """Health check with model status."""
    from src.model_loader import (
        get_model, _ml_model_p2, _ml_model_p3,
        _ml_model_p4, _ml_model_p5, _ml_model_p6
    )
    
    return {
        "status": "healthy",
        "service": "ml-prediction",
        "version": "2.0.0",
        "models": {
            "p1_failure": get_model() is not None,
            "p2_failure_type": _ml_model_p2 is not None,
            "p3_rul": _ml_model_p3 is not None,
            "p4_anomaly": _ml_model_p4 is not None,
            "p5_priority": _ml_model_p5 is not None,
            "p6_schedule": _ml_model_p6 is not None,
        }
    }


@router.get("/models/status")
async def models_status():
    """Get detailed status of all loaded models."""
    status = get_all_models_status()
    return ModelsStatusResponse(
        success=True,
        models=status
    )


@router.post("/predict")
async def predict(data: TelemetryInput) -> PredictionResponse:
    """
    P1: Predict failure probability from telemetry.
    
    Returns failure probability (0-100) and risk level.
    """
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear
    ]
    
    try:
        failure_prob = MachineLearningService.predict_failure_probability(features)
        
        # Determine risk level
        if failure_prob >= 75:
            risk_level = "CRITICAL"
        elif failure_prob >= 50:
            risk_level = "HIGH"
        elif failure_prob >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return PredictionResponse(
            success=True,
            prediction={
                "failure_probability": failure_prob,
                "risk_level": risk_level,
                "features": features
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict-all")
async def predict_all(data: TelemetryInput) -> AllPredictionsResponse:
    """
    Get all P1-P6 predictions in a single request.
    
    Returns comprehensive prediction including:
    - P1: Failure probability & risk level
    - P2: Failure types (TWF, HDF, PWF, OSF, RNF)
    - P3: RUL (days until failure)
    - P4: Anomaly detection
    - P5: Priority prediction
    - P6: Maintenance schedule
    """
    telemetry = {
        "air_temperature":    data.air_temperature,
        "process_temperature": data.process_temperature,
        "rotational_speed":   data.rotational_speed,
        "torque":             data.torque,
        "tool_wear":          data.tool_wear,
        "machine_id":         data.machine_id if data.machine_id is not None else -1,
        "_logs":              data._logs or [],
    }

    try:
        predictions = MachineLearningService.predict_all(telemetry)
        
        return AllPredictionsResponse(
            success=True,
            predictions=predictions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/predict/failure-type")
async def predict_failure_type_get(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """
    P2: Predict specific failure types.
    
    Query parameters for features.
    """
    temp_delta = process - air
    features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]
    
    try:
        failure_types = MachineLearningService.predict_failure_type(features)
        
        return {
            "success": True,
            "failure_types": failure_types,
            "input_features": features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/failure-type")
async def predict_failure_type_post(data: TelemetryInput):
    """
    P2: Predict specific failure types (POST).
    """
    temp_delta = data.process_temperature - data.air_temperature
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear,
        temp_delta
    ]
    
    try:
        failure_types = MachineLearningService.predict_failure_type(features)
        
        return {
            "success": True,
            "failure_types": failure_types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/predict/rul")
async def predict_rul_get(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """
    P3: Predict Remaining Useful Life (RUL).
    
    Query parameters for features.
    """
    features = [float(air), float(process), float(rpm), float(torque), float(wear)]
    
    try:
        rul_days = MachineLearningService.predict_rul(features)
        
        return {
            "success": True,
            "rul_days": round(rul_days, 1) if rul_days else None,
            "rul_hours": round(rul_days * 24, 1) if rul_days else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/rul")
async def predict_rul_post(data: TelemetryInput):
    """
    P3: Predict Remaining Useful Life (RUL) (POST).
    """
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear
    ]
    
    try:
        rul_days = MachineLearningService.predict_rul(features)
        
        return {
            "success": True,
            "rul_days": round(rul_days, 1) if rul_days else None,
            "rul_hours": round(rul_days * 24, 1) if rul_days else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/predict/anomaly")
async def predict_anomaly_get(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """
    P4: Detect anomalies using Isolation Forest.
    
    Query parameters for features.
    """
    features = [float(air), float(process), float(rpm), float(torque), float(wear)]
    
    try:
        is_anomaly, score = MachineLearningService.detect_anomaly(features)
        
        return {
            "success": True,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 3)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/anomaly")
async def predict_anomaly_post(data: TelemetryInput):
    """
    P4: Detect anomalies (POST).
    """
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear
    ]
    
    try:
        is_anomaly, score = MachineLearningService.detect_anomaly(features)
        
        return {
            "success": True,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 3)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/predict/priority")
async def predict_priority_get(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """
    P5: Predict work order priority.
    
    Query parameters for features.
    """
    temp_delta = process - air
    features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]
    
    try:
        priority = MachineLearningService.predict_priority(features)
        
        return {
            "success": True,
            "predicted_priority": priority
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/priority")
async def predict_priority_post(data: TelemetryInput):
    """
    P5: Predict work order priority (POST).
    """
    temp_delta = data.process_temperature - data.air_temperature
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear,
        temp_delta
    ]
    
    try:
        priority = MachineLearningService.predict_priority(features)
        
        return {
            "success": True,
            "predicted_priority": priority
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/predict/schedule")
async def predict_schedule_get(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """
    P6: Predict maintenance schedule.
    
    Query parameters for features.
    """
    temp_delta = process - air
    features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]
    
    try:
        days = MachineLearningService.predict_maintenance_schedule(features)
        
        return {
            "success": True,
            "schedule_days": round(days, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/schedule")
async def predict_schedule_post(data: TelemetryInput):
    """
    P6: Predict maintenance schedule (POST).
    """
    temp_delta = data.process_temperature - data.air_temperature
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear,
        temp_delta
    ]
    
    try:
        days = MachineLearningService.predict_maintenance_schedule(features)
        
        return {
            "success": True,
            "schedule_days": round(days, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


# ==================== Batch Predictions ====================

class BatchTelemetryInput(BaseModel):
    """Batch input for multiple machines."""
    machines: List[TelemetryInput]


@router.post("/predict/batch")
async def predict_batch(data: BatchTelemetryInput):
    """
    Batch predict for multiple machines.
    
    Uses TTL cache to avoid redundant predictions.
    """
    from .cache import prediction_cache, get_cached_prediction, set_cached_prediction
    
    results = []
    for machine in data.machines:
        # Create cache key dict
        telemetry = {
            "air_temperature": machine.air_temperature,
            "process_temperature": machine.process_temperature,
            "rotational_speed": machine.rotational_speed,
            "torque": machine.torque,
            "tool_wear": machine.tool_wear
        }
        
        # Check cache first
        cached = get_cached_prediction(telemetry)
        if cached:
            results.append(cached)
        else:
            # Make prediction
            pred = MachineLearningService.predict_all(telemetry)
            set_cached_prediction(telemetry, pred)
            results.append(pred)
    
    return {
        "success": True,
        "predictions": results,
        "count": len(results)
    }


# ==================== Cache Management ====================

@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    from .cache import prediction_cache
    
    return prediction_cache.stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear prediction cache."""
    from .cache import clear_prediction_cache
    
    clear_prediction_cache()
    return {"success": True, "message": "Cache cleared"}


# ==================== Rate Limiting ====================

@router.get("/rate-limit/status")
async def rate_limit_status(request: Request):
    """Get rate limit status for current client."""
    from .rate_limiter import get_rate_status
    
    return get_rate_status(request)


# ==================== Feature Store ====================

@router.get("/features/validate")
async def validate_features(
    air: float,
    process: float,
    rpm: int,
    torque: float,
    wear: int
):
    """Validate telemetry features against allowed ranges."""
    from .feature_store import feature_store
    
    telemetry = {
        "air_temperature": air,
        "process_temperature": process,
        "rotational_speed": rpm,
        "torque": torque,
        "tool_wear": wear
    }
    
    validated = feature_store.validate_telemetry(telemetry)
    derived = feature_store.compute_derived(validated)
    is_valid = all(
        feature_store.validate_range(validated.get(f), f)
        for f in validated
    )
    
    return {
        "valid": is_valid,
        "validated": validated,
        "derived": derived,
        "feature_names": feature_store.get_feature_names()
    }


# ==================== Model Registry ====================

@router.get("/registry/models")
async def list_models():
    """List all registered models."""
    from .model_registry import registry
    
    return {
        "success": True,
        "models": registry.list_all_models()
    }


@router.get("/registry/models/{model_name}")
async def get_model_versions(model_name: str):
    """Get versions for a specific model."""
    from .model_registry import registry
    
    return {
        "success": True,
        "model": model_name,
        "versions": registry.list_versions(model_name)
    }


@router.post("/registry/register")
async def register_model(
    model_name: str,
    version: str,
    metrics: Optional[Dict] = None,
    model_path: Optional[str] = None
):
    """Register a new model version."""
    from .model_registry import registry
    
    entry = registry.register(model_name, version, metrics, model_path)
    
    return {
        "success": True,
        "registered": entry
    }


# ==================== Drift Detection ====================

@router.post("/drift/baseline")
async def add_baseline(data: TelemetryInput):
    """Add features to drift detection baseline."""
    from .drift_detector import update_baseline
    
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear
    ]
    update_baseline(features)
    
    return {
        "success": True,
        "message": "Added to baseline"
    }


@router.get("/drift/status")
async def drift_status():
    """Get drift detection status."""
    from .drift_detector import get_drift_status
    
    return get_drift_status()


@router.post("/drift/check")
async def check_drift(data: TelemetryInput):
    """Check for drift with input features."""
    from .drift_detector import check_drift
    
    features = [
        data.air_temperature,
        data.process_temperature,
        data.rotational_speed,
        data.torque,
        data.tool_wear
    ]
    
    result = check_drift(features)
    return {
        "success": True,
        "drift": result
    }


@router.post("/drift/reset")
async def reset_drift():
    """Reset drift detection current window."""
    from .drift_detector import drift_detector
    
    drift_detector.reset_current()
    return {
        "success": True,
        "message": "Current window reset"
    }