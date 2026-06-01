"""
Groq API Client for LLM Chat
Provides chat interface to Groq LLM for AI assistant functionality.

Caching: identical (messages, tools, temperature) requests are cached in-memory
with a 10-minute TTL. Cache key is a SHA-256 hash of the JSON-serialized inputs.
Skipped automatically when `tools` are provided (tool calls are stateful and
should not be replayed).
"""
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

from cachetools import TTLCache
from groq import Groq

from core.config import settings

logger = logging.getLogger(__name__)

# Response cache — identical user questions → skip LLM call entirely
GROQ_CACHE_SIZE = 256
GROQ_CACHE_TTL = 600  # 10 minutes
_groq_cache: TTLCache = TTLCache(maxsize=GROQ_CACHE_SIZE, ttl=GROQ_CACHE_TTL)
_groq_hits = 0
_groq_misses = 0


def _cache_key(messages: List[Dict], temperature: float) -> str:
    """Deterministic SHA-256 key from messages + temperature."""
    payload = json.dumps(
        {"messages": messages, "temperature": round(temperature, 4)},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def groq_cache_stats() -> dict:
    total = _groq_hits + _groq_misses
    hit_rate = (_groq_hits / total) if total else 0.0
    return {
        "size": len(_groq_cache),
        "max_size": GROQ_CACHE_SIZE,
        "ttl_seconds": GROQ_CACHE_TTL,
        "hits": _groq_hits,
        "misses": _groq_misses,
        "hit_rate": round(hit_rate, 4),
    }


def clear_groq_cache() -> None:
    _groq_cache.clear()
    logger.info("Groq response cache cleared.")


class GroqClient:
    """Wrapper for Groq API calls."""

    def __init__(self):
        api_key = getattr(settings, "groq_api_key", None) or getattr(settings, "GROQ_API_KEY", None)
        if not api_key:
            raise ValueError("GROQ_API_KEY not configured")
        self.client = Groq(api_key=api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Send chat request to Groq.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            tools: Optional list of tool definitions
            temperature: Response creativity (0-1)

        Returns:
            Groq response dict
        """
        global _groq_hits, _groq_misses

        # Skip cache when tools are involved — tool calls have side effects
        # and may depend on live state. Only cache pure text responses.
        use_cache = not tools and temperature <= 0.3
        cache_key = None
        if use_cache:
            cache_key = _cache_key(messages, temperature)
            cached = _groq_cache.get(cache_key)
            if cached is not None:
                _groq_hits += 1
                return cached
            _groq_misses += 1

        try:
            params = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**params)
            result = response.model_dump()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

        if use_cache and cache_key is not None:
            _groq_cache[cache_key] = result
        return result


_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
