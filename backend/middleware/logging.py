"""Request logging middleware"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request info
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = round((time.time() - start_time) * 1000, 2)
        status = response.status_code
        
        # Log based on status
        log_msg = f"{method} {path} - {status} - {duration}ms - {client}"
        
        if status >= 500:
            logger.error(log_msg)
        elif status >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration}ms"
        
        return response
