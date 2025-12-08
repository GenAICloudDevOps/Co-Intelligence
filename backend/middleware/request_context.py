import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import REQUEST_ID_HEADER

request_id_ctx = contextvars.ContextVar("request_id", default=None)


def get_request_id() -> str:
    return request_id_ctx.get() or ""


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to each request and propagate in headers."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        token = request_id_ctx.set(req_id)

        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        response.headers[REQUEST_ID_HEADER] = req_id
        return response
