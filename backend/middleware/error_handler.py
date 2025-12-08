import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette import status
from core.logging import REQUEST_ID_HEADER
from middleware.request_context import get_request_id

logger = logging.getLogger("api")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Return consistent error envelopes and log unexpected exceptions."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            req_id = get_request_id()
            logger.exception("Unhandled exception", extra={"request_id": req_id, "path": request.url.path})
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "message": "Internal server error",
                        "request_id": req_id,
                    }
                },
                headers={REQUEST_ID_HEADER: req_id},
            )
