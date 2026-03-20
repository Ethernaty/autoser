from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=2, max_length=200)
    tenant_slug: str | None = Field(default=None, min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_slug: str | None = Field(default=None, min_length=2, max_length=120)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: UUID


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime


class AuthTenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_expires_in: int
    refresh_expires_in: int


class AuthResponse(BaseModel):
    user: AuthUserResponse
    tenant: AuthTenantResponse
    role: str
    tokens: AuthTokenResponse


class MeResponse(BaseModel):
    user: AuthUserResponse
    tenant: AuthTenantResponse
    role: str


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    is_active: bool


class WorkspaceListResponse(BaseModel):
    active_workspace_id: UUID
    workspaces: list[WorkspaceResponse]
