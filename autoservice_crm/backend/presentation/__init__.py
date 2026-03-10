from __future__ import annotations

from fastapi import APIRouter

from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.membership_middleware import MembershipValidationMiddleware
from presentation.app_routes import router as app_routes_router
from presentation.routes import router as presentation_routes_router


ADMIN_PREFIX = "/admin"
APP_PREFIX = "/app"
ADMIN_LOGIN_PATH = f"{ADMIN_PREFIX}/auth/login"
ADMIN_LOGOUT_PATH = f"{ADMIN_PREFIX}/auth/logout"


admin_router = APIRouter(prefix=ADMIN_PREFIX, include_in_schema=False)
admin_router.include_router(presentation_routes_router)

app_router = APIRouter(prefix=APP_PREFIX, include_in_schema=False)
app_router.include_router(app_routes_router)

router = APIRouter(include_in_schema=False)
router.include_router(admin_router)
router.include_router(app_router)


def register_presentation_public_paths() -> None:
    public_paths = {ADMIN_LOGIN_PATH, ADMIN_LOGOUT_PATH}
    AuthMiddleware.PUBLIC_PATHS.update(public_paths)
    MembershipValidationMiddleware.PUBLIC_PATHS.update(public_paths)
