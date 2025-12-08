"""Request logging middleware"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import REQUEST_ID_HEADER, get_logger
from middleware.request_context import get_request_id

logger = get_logger("api")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"
        
        response = await call_next(request)
        
        duration = round((time.time() - start_time) * 1000, 2)
        status = response.status_code
        req_id = get_request_id()
        
        logger.info(
            "request",
            extra={
                "request_id": req_id,
                "method": method,
                "path": path,
                "status_code": status,
                "duration_ms": duration,
                "client": client,
            },
        )
        
        response.headers["X-Response-Time"] = f"{duration}ms"
        if req_id:
            response.headers[REQUEST_ID_HEADER] = req_id
        
        return response
