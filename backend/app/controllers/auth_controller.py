from __future__ import annotations

from fastapi import APIRouter, Depends

from app.controllers.schemas.auth_schemas import (
    AuthResponse,
    AuthTenantResponse,
    AuthTokenResponse,
    AuthUserResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceSwitchRequest,
)
from app.core.request_context import UserRequestContext, get_current_user_context
from app.services.auth_service import AuthResult, AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service() -> AuthService:
    return AuthService()


def _to_auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        user=AuthUserResponse.model_validate(result.user),
        tenant=AuthTenantResponse.model_validate(result.tenant),
        role=result.role,
        tokens=AuthTokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token,
            token_type=result.tokens.token_type,
            access_expires_in=result.tokens.access_expires_in,
            refresh_expires_in=result.tokens.refresh_expires_in,
        ),
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> AuthResponse:
    result = service.register(
        email=str(payload.email),
        password=payload.password,
        tenant_name=payload.tenant_name,
        tenant_slug=payload.tenant_slug,
    )
    return _to_auth_response(result)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> AuthResponse:
    result = service.login(
        email=str(payload.email),
        password=payload.password,
        tenant_slug=payload.tenant_slug,
    )
    return _to_auth_response(result)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> AuthTokenResponse:
    result = service.refresh(refresh_token=payload.refresh_token)
    return AuthTokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        token_type=result.tokens.token_type,
        access_expires_in=result.tokens.access_expires_in,
        refresh_expires_in=result.tokens.refresh_expires_in,
    )


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, service: AuthService = Depends(get_auth_service)) -> None:
    service.revoke_refresh_token(refresh_token=payload.refresh_token)


@router.get("/me", response_model=MeResponse)
def me(
    context: UserRequestContext = Depends(get_current_user_context),
    service: AuthService = Depends(get_auth_service),
) -> MeResponse:
    service.assert_membership_scope(user_id=context.user_id, tenant_id=context.tenant_id)
    profile = service.me_by_scope(user_id=context.user_id, tenant_id=context.tenant_id)
    return MeResponse(
        user=AuthUserResponse.model_validate(profile.user),
        tenant=AuthTenantResponse.model_validate(profile.tenant),
        role=context.role,
    )


@router.get("/workspaces", response_model=WorkspaceListResponse)
def workspaces(
    context: UserRequestContext = Depends(get_current_user_context),
    service: AuthService = Depends(get_auth_service),
) -> WorkspaceListResponse:
    items = service.list_user_workspaces(user_id=context.user_id)
    return WorkspaceListResponse(
        active_workspace_id=context.tenant_id,
        workspaces=[
            WorkspaceResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                role=item.role,
                is_active=item.is_active,
            )
            for item in items
        ],
    )


@router.post("/switch-workspace", response_model=AuthResponse)
def switch_workspace(
    payload: WorkspaceSwitchRequest,
    context: UserRequestContext = Depends(get_current_user_context),
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    result = service.switch_workspace(user_id=context.user_id, workspace_id=payload.workspace_id)
    return _to_auth_response(result)
