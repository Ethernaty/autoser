from __future__ import annotations

from fastapi import APIRouter

from presentation.routes.auth import router as auth_router
from presentation.routes.dashboard import router as dashboard_router
from presentation.routes.forbidden import router as forbidden_router
from presentation.routes.monitoring import router as monitoring_router
from presentation.routes.subscriptions import router as subscriptions_router
from presentation.routes.system import router as system_router
from presentation.routes.tenants import router as tenants_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(forbidden_router)
router.include_router(dashboard_router)
router.include_router(tenants_router)
router.include_router(subscriptions_router)
router.include_router(monitoring_router)
router.include_router(system_router)
