"""Rate limiting middleware"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, requests_per_second: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.minute_requests = defaultdict(list)
        self.second_requests = defaultdict(list)
    
    def _clean_old_requests(self, requests: list, window: float) -> list:
        """Remove requests older than window"""
        now = time.time()
        return [t for t in requests if now - t < window]
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        now = time.time()
        
        # Check per-second limit
        self.second_requests[client_id] = self._clean_old_requests(
            self.second_requests[client_id], 1.0
        )
        if len(self.second_requests[client_id]) >= self.requests_per_second:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a second.")
        
        # Check per-minute limit
        self.minute_requests[client_id] = self._clean_old_requests(
            self.minute_requests[client_id], 60.0
        )
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        
        # Record request
        self.second_requests[client_id].append(now)
        self.minute_requests[client_id].append(now)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.minute_requests[client_id])
        )
        
        return response
