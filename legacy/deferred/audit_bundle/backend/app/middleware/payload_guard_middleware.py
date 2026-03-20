from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.exceptions import AppError


class PayloadGuardMiddleware(BaseHTTPMiddleware):
    """Reject oversized request payloads early."""

    def __init__(self, app):
        super().__init__(app)
        self._max_payload_bytes = get_settings().max_payload_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_payload_bytes:
                    error = AppError(
                        status_code=413,
                        code="payload_too_large",
                        message="Payload too large",
                        details={"max_payload_bytes": self._max_payload_bytes},
                    )
                    return JSONResponse(status_code=error.status_code, content=error.to_dict())
            except ValueError:
                pass
        return await call_next(request)
