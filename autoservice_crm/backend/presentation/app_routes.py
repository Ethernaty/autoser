from __future__ import annotations

from fastapi import APIRouter

from presentation.routes.crm_app import router as crm_app_router
from presentation.routes.forbidden import router as forbidden_router
from presentation.routes.operator_ui import router as operator_ui_router


router = APIRouter()
router.include_router(forbidden_router)
router.include_router(operator_ui_router)
router.include_router(crm_app_router)
