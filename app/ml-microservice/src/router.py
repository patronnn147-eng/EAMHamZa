"""
ML Router - FastAPI routes for ML microservice
Provides all P1-P6 prediction endpoints
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from .predictions import MachineLearningService, failure_prob_to_risk
from .core.config import config
from .core.feature_pipeline import FeaturePipeline, SensorReading
from .core.model_loader import get_all_models_status, startup_check
from .feature_store import feature_store
from .model_registry import registry
from .rate_limiter import check_rate_limit

try:
    import numpy as _np
    def _to_python(obj):
        """Recursively convert numpy scalars/arrays to Python native types."""
        if isinstance(obj, dict):
            return {k: _to_python(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_python(v) for v in obj]
        if isinstance(obj, _np.integer):
            return int(obj)
        if isinstance(obj, _np.floating):
            return float(obj)
        if isinstance(obj, _np.bool_):
            return bool(obj)
        if isinstance(obj, _np.ndarray):
            return obj.tolist()
        return obj
except ImportError:
    def _to_python(obj):
        return obj

# Maximum number of telemetry log entries accepted per request
_MAX_LOGS = 500

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
    telemetry_logs:     Optional[List[Dict]] = None
    include_shap:       bool = False

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
    from .core.model_loader import load_p1, load_p2, load_p3, load_p4, load_p5, load_p6

    return {
        "status": "healthy",
        "service": "ml-prediction",
        "version": "2.0.0",
        "models": {
            "p1_failure":      load_p1() is not None,
            "p2_failure_type": load_p2() is not None,
            "p3_rul":          load_p3() is not None,
            "p4_anomaly":      load_p4() is not None,
            "p5_priority":     load_p5() is not None,
            "p6_schedule":     load_p6() is not None,
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


@router.get("/model/metrics")
async def get_model_metrics():
    """Get trained metrics for P1 failure prediction model."""
    import joblib
    import os
    
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'basic_machine_model.pkl')
    
    try:
        if os.path.exists(model_path):
            model_data = joblib.load(model_path)
            if isinstance(model_data, dict):
                metrics = model_data.get('metrics', {})
                return {
                    "success": True,
                    "model": "p1_failure",
                    "metrics": metrics
                }
        
        return {
            "success": False,
            "error": "Model not found"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/predict")
async def predict(data: TelemetryInput, request: Request, _: str = Depends(check_rate_limit)) -> PredictionResponse:
    """
    P1: Predict failure probability from telemetry.
    
    Returns failure probability (0-100) and risk level.
    """
    reading = SensorReading(
        air_temp=data.air_temperature,
        process_temp=data.process_temperature,
        rpm=data.rotational_speed,
        torque=data.torque,
        tool_wear=data.tool_wear,
    )
    features_7 = FeaturePipeline.build_7(reading)

    try:
        failure_prob = MachineLearningService.predict_failure_probability(features_7)

        risk_level = failure_prob_to_risk(failure_prob)

        return PredictionResponse(
            success=True,
            prediction=_to_python({
                "failure_probability": failure_prob,
                "risk_level": risk_level,
                "features": features_7
            })
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict-all")
async def predict_all(data: TelemetryInput, request: Request, _: str = Depends(check_rate_limit)) -> AllPredictionsResponse:
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
    if data.telemetry_logs and len(data.telemetry_logs) > _MAX_LOGS:
        raise HTTPException(
            status_code=422,
            detail=f"telemetry_logs exceeds maximum size of {_MAX_LOGS} entries"
        )
    telemetry = {
        "air_temperature":    data.air_temperature,
        "process_temperature": data.process_temperature,
        "rotational_speed":   data.rotational_speed,
        "torque":             data.torque,
        "tool_wear":          data.tool_wear,
        "machine_id":         data.machine_id if data.machine_id is not None else -1,
        "telemetry_logs":     data.telemetry_logs or [],
    }

    try:
        predictions = MachineLearningService.predict_all(telemetry, include_shap=data.include_shap)
        predictions = _to_python(predictions)
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
    wear: int,
    request: Request,
    _: str = Depends(check_rate_limit)
):
    """
    P2: Predict specific failure types.

    Query parameters for features.
    """
    _reading = SensorReading(air_temp=float(air), process_temp=float(process),
                             rpm=float(rpm), torque=float(torque), tool_wear=float(wear))
    features = FeaturePipeline.build_7(_reading)
    
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
    _reading = SensorReading(air_temp=float(data.air_temperature),
                             process_temp=float(data.process_temperature),
                             rpm=float(data.rotational_speed),
                             torque=float(data.torque),
                             tool_wear=float(data.tool_wear))
    features = FeaturePipeline.build_7(_reading)
    
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
    wear: int,
    request: Request,
    _: str = Depends(check_rate_limit)
):
    """
    P3: Predict Remaining Useful Life (RUL).
    
    Query parameters for features.
    """
    reading = SensorReading(air_temp=float(air), process_temp=float(process),
                            rpm=float(rpm), torque=float(torque), tool_wear=float(wear))
    features_7 = FeaturePipeline.build_7(reading)

    try:
        rul_days = MachineLearningService.predict_rul(features_7)

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
    reading = SensorReading(
        air_temp=data.air_temperature,
        process_temp=data.process_temperature,
        rpm=data.rotational_speed,
        torque=data.torque,
        tool_wear=data.tool_wear,
    )
    features_7 = FeaturePipeline.build_7(reading)

    try:
        rul_days = MachineLearningService.predict_rul(features_7)

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
    wear: int,
    request: Request,
    _: str = Depends(check_rate_limit)
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
    wear: int,
    request: Request,
    _: str = Depends(check_rate_limit)
):
    """
    P5: Predict work order priority.

    Query parameters for features.
    """
    _reading = SensorReading(air_temp=float(air), process_temp=float(process),
                             rpm=float(rpm), torque=float(torque), tool_wear=float(wear))
    features = FeaturePipeline.build_7(_reading)
    
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
    _reading = SensorReading(air_temp=float(data.air_temperature),
                             process_temp=float(data.process_temperature),
                             rpm=float(data.rotational_speed),
                             torque=float(data.torque),
                             tool_wear=float(data.tool_wear))
    features = FeaturePipeline.build_7(_reading)
    
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
    wear: int,
    request: Request,
    _: str = Depends(check_rate_limit)
):
    """
    P6: Predict maintenance schedule.

    Query parameters for features.
    """
    _reading = SensorReading(air_temp=float(air), process_temp=float(process),
                             rpm=float(rpm), torque=float(torque), tool_wear=float(wear))
    features = FeaturePipeline.build_7(_reading)
    
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
    _reading = SensorReading(air_temp=float(data.air_temperature),
                             process_temp=float(data.process_temperature),
                             rpm=float(data.rotational_speed),
                             torque=float(data.torque),
                             tool_wear=float(data.tool_wear))
    features = FeaturePipeline.build_7(_reading)
    
    try:
        days = MachineLearningService.predict_maintenance_schedule(features)
        
        return {
            "success": True,
            "schedule_days": round(days, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


# ==================== P7: Parts Demand ====================

class PartsDemandeInput(BaseModel):
    """Input for P7 parts demand prediction."""
    machine_id:          Optional[int]         = -1
    rul_days:            float                            # P3 output (days)
    failure_type_probs:  Dict[str, float]                # {TWF: 0.85, HDF: 0.1, ...} (0-1 scale)
    horizon_days:        Optional[int]         = 30


@router.post("/predict/parts-demand")
async def predict_parts_demand(
    data: PartsDemandeInput,
    request: Request,
    _: str = Depends(check_rate_limit),
):
    """
    P7: Predict parts needed in the next horizon_days.

    Returns the parts_demand contract:
        {horizon_days, source: "p7_model"|"deterministic_fallback", items:[...]}
    Each item: piece_id, name, expected_qty, on_hand, shortfall,
               urgency_score, recommended_order_qty, driver.
    """
    try:
        result = MachineLearningService.predict_parts_demand(
            machine_id=data.machine_id or -1,
            rul_days=data.rul_days,
            failure_type_probs=data.failure_type_probs,
            horizon_days=data.horizon_days or 30,
        )
        return {"success": True, "parts_demand": _to_python(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parts demand prediction error: {str(e)}")


# ==================== Batch Predictions ====================

class BatchTelemetryInput(BaseModel):
    """Batch input for multiple machines."""
    machines: List[TelemetryInput]


@router.post("/predict/batch")
async def predict_batch(data: BatchTelemetryInput, request: Request, _: str = Depends(check_rate_limit)):
    """
    Batch predict for multiple machines.
    
    Uses TTL cache to avoid redundant predictions.
    """
    if len(data.machines) > 100:
        raise HTTPException(
            status_code=422,
            detail="Batch size exceeds maximum of 100 machines per request"
        )
    from .cache import prediction_cache, get_cached_prediction, set_cached_prediction
    
    results = []
    for machine in data.machines:
        # Full telemetry dict — must include machine_id and telemetry_logs so
        # Wave 2 models (Kalman, Survival, DST fusion) are not silently bypassed.
        telemetry = {
            "air_temperature":    machine.air_temperature,
            "process_temperature": machine.process_temperature,
            "rotational_speed":   machine.rotational_speed,
            "torque":             machine.torque,
            "tool_wear":          machine.tool_wear,
            "machine_id":         machine.machine_id if machine.machine_id is not None else -1,
            "telemetry_logs":     machine.telemetry_logs or [],
        }

        # Cache key uses only sensor values (machine_id/logs are context, not identity)
        cache_key = {
            "air_temperature":    machine.air_temperature,
            "process_temperature": machine.process_temperature,
            "rotational_speed":   machine.rotational_speed,
            "torque":             machine.torque,
            "tool_wear":          machine.tool_wear,
        }

        # Check cache first
        cached = get_cached_prediction(cache_key)
        if cached:
            results.append(cached)
        else:
            pred = MachineLearningService.predict_all(telemetry)
            set_cached_prediction(cache_key, pred)
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