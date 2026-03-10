from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.graceful_shutdown import get_shutdown_manager
from app.core.tenant_scope import reset_request_scope, set_request_scope


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Initialize per-request context values shared across middleware layers."""

    EXEMPT_WHEN_DRAINING = {
        "/health",
        "/health/live",
        "/health/ready",
        "/health/deps",
        "/metrics",
    }

    JSON_CONTENT_TYPES = {"application/json", "application/merge-patch+json"}
    _ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self._max_json_depth = settings.json_max_depth
        self._forbidden_write_fields = {
            field.strip() for field in settings.forbidden_write_fields.split(",") if field.strip()
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = self._sanitize_id(request.headers.get("X-Request-ID")) or str(uuid4())
        correlation_id = self._sanitize_id(request.headers.get("X-Correlation-ID")) or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        scope_tokens = set_request_scope(
            request_id=request_id,
            correlation_id=correlation_id,
            endpoint=request.url.path,
        )

        shutdown_manager = get_shutdown_manager()
        if request.url.path not in self.EXEMPT_WHEN_DRAINING:
            try:
                await shutdown_manager.on_request_start()
            except RuntimeError:
                response = JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "server_draining",
                            "message": "Server is shutting down and not accepting new requests",
                            "details": {},
                        }
                    },
                )
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Correlation-ID"] = correlation_id
                reset_request_scope(scope_tokens)
                return response

        try:
            payload_error = await self._validate_payload_safety(request)
            if payload_error is not None:
                response = JSONResponse(status_code=payload_error["status_code"], content=payload_error["body"])
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Correlation-ID"] = correlation_id
                return response

            response = await call_next(request)
        finally:
            if request.url.path not in self.EXEMPT_WHEN_DRAINING:
                await shutdown_manager.on_request_end()
            reset_request_scope(scope_tokens)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    def _sanitize_id(self, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if self._ID_PATTERN.fullmatch(candidate):
            return candidate
        return None

    async def _validate_payload_safety(self, request: Request) -> dict[str, Any] | None:
        if request.method.upper() not in {"POST", "PUT", "PATCH"}:
            return None

        content_type = (request.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type not in self.JSON_CONTENT_TYPES:
            return None

        body = await request.body()
        request._body = body
        if not body:
            return None

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {
                "status_code": 400,
                "body": {
                    "error": {
                        "code": "invalid_json",
                        "message": "Invalid JSON payload",
                        "details": {},
                    }
                },
            }

        if self._json_depth(payload) > self._max_json_depth:
            return {
                "status_code": 400,
                "body": {
                    "error": {
                        "code": "json_depth_exceeded",
                        "message": "JSON payload nesting depth exceeded",
                        "details": {"max_depth": self._max_json_depth},
                    }
                },
            }

        forbidden = self._find_forbidden_fields(payload)
        if forbidden:
            return {
                "status_code": 400,
                "body": {
                    "error": {
                        "code": "forbidden_write_fields",
                        "message": "Payload contains forbidden fields",
                        "details": {"fields": sorted(forbidden)},
                    }
                },
            }

        return None

    def _find_forbidden_fields(self, payload: Any) -> set[str]:
        found: set[str] = set()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    key_name = str(key)
                    if key_name in self._forbidden_write_fields:
                        found.add(key_name)
                    walk(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(payload)
        return found

    def _json_depth(self, payload: Any, current: int = 0) -> int:
        if isinstance(payload, dict):
            if not payload:
                return current + 1
            return max(self._json_depth(value, current + 1) for value in payload.values())
        if isinstance(payload, list):
            if not payload:
                return current + 1
            return max(self._json_depth(value, current + 1) for value in payload)
        return current + 1
