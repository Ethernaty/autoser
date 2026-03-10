from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.membership import Membership, MembershipRole
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


class AuthRepository:
    """Aggregate repository for auth and identity operations."""

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)
        self.membership_repo = MembershipRepository(db)

    def get_user_by_email(self, email: str) -> User | None:
        return self.user_repo.get_by_email(email)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.user_repo.get_by_id(user_id)

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        return self.tenant_repo.get_by_slug(slug)

    def get_tenant_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self.tenant_repo.get_by_id(tenant_id)

    def get_membership(self, *, user_id: UUID, tenant_id: UUID) -> Membership | None:
        return self.membership_repo.get_for_user_and_tenant(user_id=user_id, tenant_id=tenant_id)

    def list_memberships_for_user(self, user_id: UUID) -> list[Membership]:
        return self.membership_repo.list_for_user(user_id)

    def create_user(self, *, email: str, password_hash: str, is_active: bool = True) -> User:
        return self.user_repo.create(email=email, password_hash=password_hash, is_active=is_active)

    def create_tenant(self, *, name: str, slug: str) -> Tenant:
        return self.tenant_repo.create(name=name, slug=slug)

    def create_membership(self, *, user_id: UUID, tenant_id: UUID, role: MembershipRole) -> Membership:
        return self.membership_repo.create(user_id=user_id, tenant_id=tenant_id, role=role)

    def update_membership_role(self, *, user_id: UUID, tenant_id: UUID, role: MembershipRole) -> Membership | None:
        return self.membership_repo.update_role(user_id=user_id, tenant_id=tenant_id, role=role)
