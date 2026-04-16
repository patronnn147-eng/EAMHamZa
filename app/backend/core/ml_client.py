"""
ML Client - Backend client for ML microservice
Calls ML predictions from the separate ML container
"""
import os
import httpx
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ML service URL - internal Docker network
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")
ML_SERVICE_EXTERNAL = os.getenv("ML_SERVICE_EXTERNAL", "http://localhost:8001")
TIMEOUT = 30.0


class MLClient:
    """Client for ML microservice."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or ML_SERVICE_URL
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=TIMEOUT
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> Dict:
        """Check ML service health."""
        client = await self.get_client()
        try:
            response = await client.get("/api/v1/ml/health")
            return response.json()
        except Exception as e:
            logger.error(f"ML service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def predict_failure_probability(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P1: Predict failure probability."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def predict_all(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int,
        machine_id: int = -1,
        telemetry_logs: list = None,
    ) -> Dict:
        """Get all P1-P6 predictions plus DST fusion."""
        client = await self.get_client()
        payload = {
            "air_temperature":    air_temperature,
            "process_temperature": process_temperature,
            "rotational_speed":   rotational_speed,
            "torque":             torque,
            "tool_wear":          tool_wear,
            "machine_id":         machine_id,
        }
        if telemetry_logs:
            payload["_logs"] = telemetry_logs
        response = await client.post("/api/v1/ml/predict-all", json=payload)
        return response.json()
    
    async def predict_failure_type(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P2: Predict specific failure types."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/failure-type",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def predict_rul(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P3: Predict Remaining Useful Life."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/rul",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def detect_anomaly(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P4: Detect anomaly."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/anomaly",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def predict_priority(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P5: Predict work order priority."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/priority",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def predict_schedule(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """P6: Predict maintenance schedule."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/schedule",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()
    
    async def batch_predict(
        self,
        machines: List[Dict]
    ) -> Dict:
        """Batch predict for multiple machines."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/predict/batch",
            json={"machines": machines}
        )
        return response.json()
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        client = await self.get_client()
        response = await client.get("/api/v1/ml/cache/stats")
        return response.json()
    
    async def clear_cache(self) -> Dict:
        """Clear prediction cache."""
        client = await self.get_client()
        response = await client.post("/api/v1/ml/cache/clear")
        return response.json()
    
    async def get_rate_limit_status(self) -> Dict:
        """Get rate limit status."""
        client = await self.get_client()
        response = await client.get("/api/v1/ml/rate-limit/status")
        return response.json()
    
    async def validate_features(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """Validate features against allowed ranges."""
        client = await self.get_client()
        response = await client.get(
            "/api/v1/ml/features/validate",
            params={
                "air": air_temperature,
                "process": process_temperature,
                "rpm": rotational_speed,
                "torque": torque,
                "wear": tool_wear
            }
        )
        return response.json()
    
    async def check_drift(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: int,
        torque: float,
        tool_wear: int
    ) -> Dict:
        """Check for data drift."""
        client = await self.get_client()
        response = await client.post(
            "/api/v1/ml/drift/check",
            json={
                "air_temperature": air_temperature,
                "process_temperature": process_temperature,
                "rotational_speed": rotational_speed,
                "torque": torque,
                "tool_wear": tool_wear
            }
        )
        return response.json()


# Global ML client instance
ml_client = MLClient()


# Convenience functions
async def get_ml_predictions(
    air_temperature: float,
    process_temperature: float,
    rotational_speed: int,
    torque: float,
    tool_wear: int
) -> Dict:
    """Get all ML predictions for telemetry data."""
    return await ml_client.predict_all(
        air_temperature,
        process_temperature,
        rotational_speed,
        torque,
        tool_wear
    )


async def is_ml_service_available() -> bool:
    """Check if ML service is available."""
    try:
        health = await ml_client.health_check()
        return health.get("status") == "healthy"
    except Exception:
        return False