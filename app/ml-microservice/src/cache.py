"""
TTL Cache for ML Predictions
In-memory cache with time-to-live expiration and bounded size.
"""
from datetime import datetime, timedelta
import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Hard cap on live entries. clear_expired() is called automatically in set()
# when this bound is reached, preventing unbounded memory growth under load.
_MAX_ENTRIES = 1000


class TTLCache:
    """In-memory cache with TTL expiration and _MAX_ENTRIES bound."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        """
        self.cache: dict = {}
        self.ttl = ttl_seconds

    def _make_key(self, data: dict) -> str:
        """Generate cache key from data dictionary."""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires']:
                return entry['value']
            # Expired — remove single stale entry
            del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value with TTL. Evicts expired entries when at capacity."""
        # Evict before inserting to keep size bounded.
        if len(self.cache) >= _MAX_ENTRIES:
            removed = self.clear_expired()
            logger.debug(f"TTLCache: evicted {removed} expired entries at capacity")
            # If still full after eviction (all entries fresh), drop oldest.
            if len(self.cache) >= _MAX_ENTRIES:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug("TTLCache: dropped oldest entry (cache full, no expired entries)")

        self.cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=self.ttl)
        }

    def delete(self, key: str) -> bool:
        """Delete a specific key."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def clear_expired(self) -> int:
        """Remove expired entries. Returns count of removed."""
        now = datetime.now()
        expired = [
            k for k, v in self.cache.items()
            if now >= v['expires']
        ]
        for k in expired:
            del self.cache[k]
        return len(expired)

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "entries": len(self.cache),
            "ttl_seconds": self.ttl,
            "max_entries": _MAX_ENTRIES,
        }

    def __len__(self) -> int:
        return len(self.cache)


# Global cache instance for predictions
prediction_cache = TTLCache(ttl_seconds=300)


def get_cached_prediction(telemetry: dict) -> Optional[dict]:
    """
    Get cached prediction if available.

    Args:
        telemetry: Dict with air_temperature, process_temperature, etc.

    Returns:
        Cached prediction or None
    """
    cache_key = prediction_cache._make_key(telemetry)
    return prediction_cache.get(cache_key)


def set_cached_prediction(telemetry: dict, prediction: dict) -> None:
    """
    Cache a prediction.

    Args:
        telemetry: Input telemetry
        prediction: ML prediction result
    """
    cache_key = prediction_cache._make_key(telemetry)
    prediction_cache.set(cache_key, prediction)


def clear_prediction_cache() -> None:
    """Clear all cached predictions."""
    prediction_cache.clear()
    logger.info("Prediction cache cleared")
