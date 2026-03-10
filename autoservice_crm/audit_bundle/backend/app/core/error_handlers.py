from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import AppError, DatabaseAppError, ValidationAppError
from app.core.prometheus_metrics import get_metrics_registry


def _error_payload(*, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    """Attach unified API error handlers."""
    metrics = get_metrics_registry()
    logger = logging.getLogger("app.error")

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        metrics.increment_app_error(source="app", code=exc.code)
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        metrics.increment_app_error(source="validation", code="validation_error")
        error = ValidationAppError(
            code="validation_error",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        metrics.increment_app_error(source="db", code="integrity_error")
        logger.exception("Integrity error", exc_info=exc)
        error = DatabaseAppError(
            code="db_integrity_error",
            status_code=409,
            message="Database integrity violation",
            details={},
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        metrics.increment_app_error(source="db", code="sqlalchemy_error")
        logger.exception("SQLAlchemy error", exc_info=exc)
        error = DatabaseAppError(
            code="db_error",
            status_code=503,
            message="Database operation failed",
            details={},
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        metrics.increment_app_error(source="http", code="http_error")
        details = exc.detail if isinstance(exc.detail, dict) else {"reason": exc.detail}
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code="http_error", message="HTTP error", details=details),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        metrics.increment_app_error(source="app", code="internal_server_error")
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="internal_server_error",
                message="Internal server error",
                details={},
            ),
        )
