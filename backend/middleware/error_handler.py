"""Centralized error handling middleware"""
import logging
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ErrorResponse:
    """Standard error response format"""
    @staticmethod
    def create(status_code: int, message: str, detail: str = None, path: str = None):
        return {
            "error": True,
            "status_code": status_code,
            "message": message,
            "detail": detail,
            "path": path
        }

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            logger.warning(f"HTTP {e.status_code}: {e.detail} - {request.url.path}")
            return JSONResponse(
                status_code=e.status_code,
                content=ErrorResponse.create(e.status_code, e.detail, path=str(request.url.path))
            )
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse.create(500, "Internal server error", str(e), str(request.url.path))
            )

def handle_exception(e: Exception, context: str = "") -> dict:
    """Helper to handle exceptions consistently"""
    error_msg = f"{context}: {str(e)}" if context else str(e)
    logger.error(f"{error_msg}\n{traceback.format_exc()}")
    return {"error": True, "message": error_msg}
