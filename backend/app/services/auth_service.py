from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.core.database import SessionLocal
from app.core.exceptions import AppError, AuthError
from app.core.uow import SqlAlchemyUnitOfWork
from app.models.membership import Membership, MembershipRole
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.services.jwt_service import JWTService, TokenPair, TokenType, get_jwt_service
from app.services.password_hasher import PasswordHasher


@dataclass
class AuthResult:
    user: User
    tenant: Tenant
    role: str
    tokens: TokenPair


@dataclass
class UserContext:
    user: User
    tenant: Tenant
    role: str


@dataclass(frozen=True)
class WorkspaceMembership:
    id: UUID
    name: str
    slug: str
    role: str
    is_active: bool


class AuthService:
    """Identity service for tenant-aware authentication."""

    def __init__(
        self,
        *,
        jwt_service: JWTService | None = None,
        password_hasher: PasswordHasher | None = None,
    ):
        self.jwt_service = jwt_service or get_jwt_service()
        self.password_hasher = password_hasher or PasswordHasher()

    def register(self, *, email: str, password: str, tenant_name: str, tenant_slug: str | None) -> AuthResult:
        normalized_email = self._normalize_email(email)
        normalized_slug = self._normalize_slug(tenant_slug) if tenant_slug else self._slugify(tenant_name)

        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            if auth_repo.get_user_by_email(normalized_email):
                raise AppError(status_code=409, code="email_exists", message="Email already registered")
            if auth_repo.get_tenant_by_slug(normalized_slug):
                raise AppError(status_code=409, code="tenant_slug_exists", message="Tenant slug already in use")

            user = auth_repo.create_user(
                email=normalized_email,
                password_hash=self.password_hasher.hash(password),
                is_active=True,
            )
            tenant = auth_repo.create_tenant(name=tenant_name.strip(), slug=normalized_slug)
            membership = auth_repo.create_membership(
                user_id=user.id,
                tenant_id=tenant.id,
                role=MembershipRole.OWNER,
            )

            tokens = self.jwt_service.issue_token_pair(
                user_id=user.id,
                tenant_id=tenant.id,
                role=membership.role.value,
                membership_version=membership.version,
            )
            return AuthResult(user=user, tenant=tenant, role=membership.role.value, tokens=tokens)

    def login(self, *, email: str, password: str, tenant_slug: str | None) -> AuthResult:
        normalized_email = self._normalize_email(email)

        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            user = auth_repo.get_user_by_email(normalized_email)
            if not user or not self.password_hasher.verify(password, user.password_hash):
                raise AuthError(code="invalid_credentials", message="Invalid credentials")
            if not user.is_active:
                raise AppError(status_code=403, code="user_inactive", message="User account is inactive")

            try:
                membership, tenant = self._resolve_membership_for_login(
                    auth_repo=auth_repo,
                    user=user,
                    tenant_slug=tenant_slug,
                )
            except AppError as exc:
                if exc.code in {"tenant_not_found", "membership_not_found", "tenant_required", "no_memberships"}:
                    raise AuthError(code="invalid_credentials", message="Invalid credentials") from exc
                raise
            if tenant.state.value != "active":
                raise AppError(status_code=403, code="tenant_inactive", message="Tenant access is restricted")

            tokens = self.jwt_service.issue_token_pair(
                user_id=user.id,
                tenant_id=tenant.id,
                role=membership.role.value,
                membership_version=membership.version,
            )
            return AuthResult(user=user, tenant=tenant, role=membership.role.value, tokens=tokens)

    def list_user_workspaces(self, *, user_id: UUID) -> list[WorkspaceMembership]:
        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            user = auth_repo.get_user_by_id(user_id)
            if not user:
                raise AuthError(code="invalid_token_subject", message="User not found")
            if not user.is_active:
                raise AppError(status_code=403, code="user_inactive", message="User account is inactive")

            memberships = auth_repo.list_memberships_for_user(user.id)
            result: list[WorkspaceMembership] = []
            for membership in memberships:
                tenant = auth_repo.get_tenant_by_id(membership.tenant_id)
                if tenant is None:
                    continue
                result.append(
                    WorkspaceMembership(
                        id=tenant.id,
                        name=tenant.name,
                        slug=tenant.slug,
                        role=membership.role.value,
                        is_active=tenant.state.value == "active",
                    )
                )

            result.sort(key=lambda item: item.name.lower())
            return result

    def switch_workspace(self, *, user_id: UUID, workspace_id: UUID) -> AuthResult:
        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            user = auth_repo.get_user_by_id(user_id)
            if not user:
                raise AuthError(code="invalid_token_subject", message="User not found")
            if not user.is_active:
                raise AppError(status_code=403, code="user_inactive", message="User account is inactive")

            membership = auth_repo.get_membership(user_id=user.id, tenant_id=workspace_id)
            if not membership:
                raise AppError(status_code=403, code="workspace_forbidden", message="User has no access to workspace")

            tenant = auth_repo.get_tenant_by_id(workspace_id)
            if tenant is None:
                raise AuthError(code="tenant_not_found", message="Tenant not found")
            if tenant.state.value != "active":
                raise AppError(status_code=403, code="tenant_inactive", message="Tenant access is restricted")

            tokens = self.jwt_service.issue_token_pair(
                user_id=user.id,
                tenant_id=tenant.id,
                role=membership.role.value,
                membership_version=membership.version,
            )
            return AuthResult(user=user, tenant=tenant, role=membership.role.value, tokens=tokens)

    def refresh(self, *, refresh_token: str) -> AuthResult:
        payload = self.jwt_service.decode(refresh_token, expected_type=TokenType.REFRESH)

        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            user = auth_repo.get_user_by_id(payload.user_id)
            if not user:
                raise AuthError(code="invalid_token_subject", message="User not found")
            if not user.is_active:
                raise AppError(status_code=403, code="user_inactive", message="User account is inactive")

            membership = auth_repo.get_membership(user_id=user.id, tenant_id=payload.tenant_uuid)
            if not membership:
                raise AuthError(code="membership_not_found", message="Membership not found")

            tenant = auth_repo.get_tenant_by_id(membership.tenant_id)
            if not tenant:
                raise AuthError(code="tenant_not_found", message="Tenant not found")
            if tenant.state.value != "active":
                raise AppError(status_code=403, code="tenant_inactive", message="Tenant access is restricted")

            self.jwt_service.revoke(payload)

            tokens = self.jwt_service.issue_token_pair(
                user_id=user.id,
                tenant_id=tenant.id,
                role=membership.role.value,
                membership_version=membership.version,
            )
            return AuthResult(user=user, tenant=tenant, role=membership.role.value, tokens=tokens)

    def me(self, *, access_token: str) -> UserContext:
        payload = self.jwt_service.decode(access_token, expected_type=TokenType.ACCESS)
        return self.me_by_scope(user_id=payload.user_id, tenant_id=payload.tenant_uuid)

    def me_by_scope(self, *, user_id: UUID, tenant_id: UUID) -> UserContext:
        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)

            user = auth_repo.get_user_by_id(user_id)
            if not user:
                raise AuthError(code="invalid_token_subject", message="User not found")
            if not user.is_active:
                raise AppError(status_code=403, code="user_inactive", message="User account is inactive")

            membership = auth_repo.get_membership(user_id=user.id, tenant_id=tenant_id)
            if not membership:
                raise AppError(status_code=403, code="tenant_mismatch", message="User has no access to tenant")

            tenant = auth_repo.get_tenant_by_id(membership.tenant_id)
            if not tenant:
                raise AuthError(code="tenant_not_found", message="Tenant not found")
            if tenant.state.value != "active":
                raise AppError(status_code=403, code="tenant_inactive", message="Tenant access is restricted")

            return UserContext(user=user, tenant=tenant, role=membership.role.value)

    def assert_membership_scope(self, *, user_id: UUID, tenant_id: UUID) -> Membership:
        with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
            if uow.session is None:
                raise RuntimeError("uow_session_missing")
            auth_repo = AuthRepository(uow.session)
            membership = auth_repo.get_membership(user_id=user_id, tenant_id=tenant_id)
            if not membership:
                raise AppError(status_code=403, code="tenant_mismatch", message="User has no access to tenant")
            return membership

    def revoke_refresh_token(self, *, refresh_token: str) -> None:
        self.jwt_service.revoke_token(refresh_token, expected_type=TokenType.REFRESH)

    def _resolve_membership_for_login(
        self,
        *,
        auth_repo: AuthRepository,
        user: User,
        tenant_slug: str | None,
    ) -> tuple[Membership, Tenant]:
        memberships = auth_repo.list_memberships_for_user(user.id)
        if not memberships:
            raise AppError(status_code=403, code="no_memberships", message="User is not assigned to any tenant")

        if tenant_slug:
            slug = self._normalize_slug(tenant_slug)
            tenant = auth_repo.get_tenant_by_slug(slug)
            if not tenant:
                raise AppError(status_code=403, code="tenant_not_found", message="Tenant not found")
            membership = auth_repo.get_membership(user_id=user.id, tenant_id=tenant.id)
            if not membership:
                raise AppError(status_code=403, code="membership_not_found", message="User has no access to tenant")
            return membership, tenant

        if len(memberships) > 1:
            raise AppError(
                status_code=400,
                code="tenant_required",
                message="tenant_slug is required for users with multiple tenants",
            )

        membership = memberships[0]
        tenant = auth_repo.get_tenant_by_id(membership.tenant_id)
        if not tenant:
            raise AuthError(code="tenant_not_found", message="Tenant not found")
        return membership, tenant

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if not normalized:
            raise AppError(status_code=400, code="invalid_email", message="Email is required")
        return normalized

    def _normalize_slug(self, slug: str) -> str:
        normalized = self._slugify(slug)
        if not normalized:
            raise AppError(status_code=400, code="invalid_slug", message="Tenant slug is invalid")
        return normalized

    @staticmethod
    def _slugify(value: str) -> str:
        base = value.strip().lower()
        base = re.sub(r"[^a-z0-9]+", "-", base)
        base = re.sub(r"-{2,}", "-", base).strip("-")
        return base
