"""
Rate Limiter for ML API
Simple in-memory rate limiting by client IP
"""
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using sliding window."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get real IP behind proxy
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.client.host if request.client else 'unknown'
    
    def check(self, request: Request) -> str:
        """
        Check if request is allowed. Returns client_id if allowed.
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        client_id = self._get_client_id(request)
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window)
        
        # Clean old requests outside window
        self.requests[client_id] = [
            t for t in self.requests[client_id] 
            if t > window_start
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window}s"
            )
        
        # Add current request
        self.requests[client_id].append(now)
        return client_id
    
    def get_status(self, request: Request) -> dict:
        """Get rate limit status for client."""
        client_id = self._get_client_id(request)
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window)
        
        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id] 
            if t > window_start
        ]
        
        used = len(self.requests[client_id])
        remaining = max(0, self.max_requests - used)
        
        return {
            "client_id": client_id,
            "used": used,
            "remaining": remaining,
            "limit": self.max_requests,
            "window_seconds": self.window
        }
    
    def reset(self, client_id: str = None) -> None:
        """Reset rate limit for specific client or all."""
        if client_id:
            if client_id in self.requests:
                del self.requests[client_id]
        else:
            self.requests.clear()


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_rate_limit(request: Request) -> str:
    """
    Check rate limit for request.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        client_id if allowed
    
    Raises:
        HTTPException: If limit exceeded
    """
    return rate_limiter.check(request)


def get_rate_status(request: Request) -> dict:
    """Get current rate limit status."""
    return rate_limiter.get_status(request)