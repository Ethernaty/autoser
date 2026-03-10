from __future__ import annotations

import secrets

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AppError


def require_internal_service_auth(request: Request) -> None:
    """Validate internal service auth header for control-plane endpoints."""
    settings = get_settings()
    expected_header = settings.internal_service_auth_header.strip()
    provided = request.headers.get(expected_header)

    if provided is None:
        raise AppError(
            status_code=401,
            code="internal_auth_missing",
            message="Internal service authentication header is required",
        )

    if not secrets.compare_digest(provided, settings.internal_service_auth_key):
        raise AppError(
            status_code=401,
            code="internal_auth_invalid",
            message="Invalid internal service authentication header",
        )
