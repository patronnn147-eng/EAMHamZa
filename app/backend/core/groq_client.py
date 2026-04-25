"""
Groq API Client for LLM Chat
Provides chat interface to Groq LLM for AI assistant functionality
"""
import logging
from typing import List, Dict, Any, Optional

from groq import Groq

from core.config import settings

logger = logging.getLogger(__name__)


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
            return response.model_dump()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client