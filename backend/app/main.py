from __future__ import annotations

import asyncio

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.controllers.auth_controller import router as auth_router
from app.controllers.audit_controller import router as audit_router
from app.controllers.client_controller import router as client_router
from app.controllers.dashboard_controller import router as dashboard_router
from app.controllers.employee_controller import legacy_router as employee_legacy_router
from app.controllers.employee_controller import router as employee_router
from app.controllers.health_controller import router as health_router
from app.controllers.vehicle_controller import router as vehicle_router
from app.controllers.work_order_controller import legacy_router as work_order_legacy_router
from app.controllers.work_order_controller import router as work_order_router
from app.controllers.workspace_controller import router as workspace_router
from app.core.cache import get_cache_backend
from app.core.config import get_settings
from app.core.database import drain_database_pool, engine
from app.core.error_handlers import register_error_handlers
from app.core.graceful_shutdown import get_shutdown_manager
from app.core.logging import configure_structured_logging
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.membership_middleware import MembershipValidationMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.structured_logging_middleware import StructuredLoggingMiddleware


settings = get_settings()
configure_structured_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Runtime order (default MVP):
# Auth -> Membership -> RateLimit -> StructuredLogging
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(MembershipValidationMiddleware)
app.add_middleware(AuthMiddleware)

if settings.enable_deferred_platform_runtime:
    from app.middleware.api_key_auth_middleware import ApiKeyAuthMiddleware

    # Runtime order extension for deferred platform APIs:
    # ApiKeyAuth -> Auth -> Membership -> RateLimit -> StructuredLogging
    app.add_middleware(ApiKeyAuthMiddleware)

if settings.enable_presentation_runtime:
    from presentation import register_presentation_public_paths
    from presentation.middleware import PresentationAuthMiddleware
    from presentation.security_middleware import PresentationSecurityMiddleware

    register_presentation_public_paths()
    # Runtime order extension for presentation:
    # PresentationSecurity -> PresentationAuth -> (...existing chain...)
    app.add_middleware(PresentationAuthMiddleware)
    app.add_middleware(PresentationSecurityMiddleware)

register_error_handlers(app)


@app.on_event("startup")
async def on_startup() -> None:
    shutdown_manager = get_shutdown_manager()
    shutdown_manager.install_signal_handlers()
    if settings.app_env in {"development", "test"}:
        from app.core.migration_guard import assert_database_schema_up_to_date

        await run_in_threadpool(assert_database_schema_up_to_date, engine)

    if settings.enable_deferred_platform_runtime:
        # Register deferred background tasks in the in-process task registry.
        from app.tasks import webhook_tasks as _webhook_tasks  # noqa: F401
        from app.core.jobs import get_job_worker

        worker = get_job_worker()
        await worker.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    shutdown_manager = get_shutdown_manager()
    await shutdown_manager.begin_shutdown()

    await shutdown_manager.wait_for_drain(settings.shutdown_drain_timeout_seconds)

    if settings.enable_deferred_platform_runtime:
        from app.core.event_stream import get_event_stream_backend
        from app.core.http_delivery_engine import get_http_delivery_engine
        from app.core.jobs import get_job_worker

        worker = get_job_worker()
        try:
            await asyncio.wait_for(worker.stop(), timeout=settings.shutdown_force_exit_timeout_seconds)
        except Exception:
            pass

        try:
            queue = worker.queue
            await asyncio.wait_for(queue.close(), timeout=5.0)
        except Exception:
            pass

        event_stream = get_event_stream_backend()
        try:
            await asyncio.wait_for(event_stream.close(), timeout=5.0)
        except Exception:
            pass

        delivery_engine = get_http_delivery_engine()
        try:
            await asyncio.wait_for(delivery_engine.close(), timeout=5.0)
        except Exception:
            pass

    cache_backend = get_cache_backend()
    try:
        await asyncio.wait_for(cache_backend.close(), timeout=5.0)
    except Exception:
        pass

    await run_in_threadpool(drain_database_pool)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(client_router)
app.include_router(vehicle_router)
app.include_router(employee_router)
app.include_router(work_order_router)
app.include_router(workspace_router)
app.include_router(dashboard_router)
app.include_router(employee_legacy_router)
app.include_router(work_order_legacy_router)

if settings.enable_deferred_platform_runtime:
    from app.controllers.api_key_controller import router as api_key_router
    from app.controllers.external_api_controller import router as external_api_router
    from app.controllers.internal_tenant_controller import router as internal_tenant_router
    from app.controllers.subscription_controller import router as subscription_router
    from app.controllers.webhook_controller import router as webhook_router

    app.include_router(api_key_router)
    app.include_router(subscription_router)
    app.include_router(webhook_router)
    app.include_router(external_api_router)
    app.include_router(internal_tenant_router)

if settings.enable_presentation_runtime:
    from fastapi.staticfiles import StaticFiles
    from presentation import router as presentation_router

    app.include_router(presentation_router)
    app.mount("/admin/static", StaticFiles(directory="presentation/static"), name="admin_static")
