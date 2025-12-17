"""Rate limiting middleware"""
import hashlib
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from services.state_store import state_store

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

    @staticmethod
    def _hash_client_id(client_id: str) -> str:
        return hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:16]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        client_key = self._hash_client_id(client_id)
        now = time.time()

        # Prefer Redis when available (multi-replica safe); fall back to in-memory
        redis_client = await state_store.get_client()
        minute_count = None

        if redis_client is not None:
            try:
                sec_bucket = int(now)
                min_bucket = int(now // 60)
                sec_key = f"ratelimit:{client_key}:sec:{sec_bucket}"
                min_key = f"ratelimit:{client_key}:min:{min_bucket}"

                pipe = redis_client.pipeline()
                pipe.incr(sec_key)
                pipe.expire(sec_key, 2)
                pipe.incr(min_key)
                pipe.expire(min_key, 61)
                sec_count, _, minute_count, _ = await pipe.execute()

                if int(sec_count) > self.requests_per_second:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Try again in a second.",
                        headers={"Retry-After": "1"},
                    )
                if int(minute_count) > self.requests_per_minute:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Try again later.",
                        headers={"Retry-After": "60"},
                    )
            except HTTPException:
                raise
            except Exception:
                # Redis issues shouldn't take down the API
                minute_count = None
                redis_client = None

        if redis_client is None:
            # Check per-second limit
            self.second_requests[client_id] = self._clean_old_requests(
                self.second_requests[client_id], 1.0
            )
            if len(self.second_requests[client_id]) >= self.requests_per_second:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a second.", headers={"Retry-After": "1"})

            # Check per-minute limit
            self.minute_requests[client_id] = self._clean_old_requests(
                self.minute_requests[client_id], 60.0
            )
            if len(self.minute_requests[client_id]) >= self.requests_per_minute:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.", headers={"Retry-After": "60"})

            # Record request
            self.second_requests[client_id].append(now)
            self.minute_requests[client_id].append(now)
            minute_count = len(self.minute_requests[client_id])

        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - int(minute_count or 0))
        )
        
        return response
