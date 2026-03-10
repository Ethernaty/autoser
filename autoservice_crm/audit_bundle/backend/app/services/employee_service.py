from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import get_cache_backend
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.membership_cache import invalidate_membership_cache_async
from app.core.serialization import JsonSerializer
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.services.base_service import BaseService
from app.services.idempotency_service import IdempotencyDecision, IdempotencyService
from app.services.password_hasher import PasswordHasher


@dataclass(frozen=True)
class EmployeeRecord:
    user_id: UUID
    tenant_id: UUID
    email: str
    role: MembershipRole
    is_active: bool
    version: int
    created_at: datetime


class EmployeeService(BaseService):
    """Tenant-scoped employee management service."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=JsonSerializer(),
            cache_backend=get_cache_backend(),
        )
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self.password_hasher = password_hasher or PasswordHasher()
        self.idempotency_service = IdempotencyService(self)

    async def list_employees_paginated(
        self,
        *,
        limit: int,
        offset: int,
        query: str | None = None,
        role: str | None = None,
    ) -> list[EmployeeRecord]:
        self._validate_pagination(limit=limit, offset=offset)
        normalized_query = self._normalize_query(query)
        normalized_role = self._normalize_role_nullable(role)

        def read_op(db: Session) -> list[EmployeeRecord]:
            stmt = (
                select(User, Membership)
                .join(Membership, Membership.user_id == User.id)
                .where(Membership.tenant_id == self.tenant_id)
                .order_by(User.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            if normalized_query:
                pattern = f"%{normalized_query}%"
                stmt = stmt.where(
                    or_(
                        User.email.ilike(pattern),
                        cast(User.id, String).ilike(pattern),
                    )
                )
            if normalized_role is not None:
                stmt = stmt.where(Membership.role == normalized_role)

            rows = db.execute(stmt).all()
            result: list[EmployeeRecord] = []
            for user, membership in rows:
                result.append(
                    EmployeeRecord(
                        user_id=user.id,
                        tenant_id=membership.tenant_id,
                        email=user.email,
                        role=membership.role,
                        is_active=bool(user.is_active),
                        version=int(membership.version),
                        created_at=user.created_at,
                    )
                )
            return result

        return await self.execute_read(read_op)

    async def count_employees(self, *, query: str | None = None, role: str | None = None) -> int:
        normalized_query = self._normalize_query(query)
        normalized_role = self._normalize_role_nullable(role)

        def read_op(db: Session) -> int:
            stmt = select(func.count()).select_from(Membership).join(User, Membership.user_id == User.id).where(
                Membership.tenant_id == self.tenant_id
            )
            if normalized_query:
                pattern = f"%{normalized_query}%"
                stmt = stmt.where(
                    or_(
                        User.email.ilike(pattern),
                        cast(User.id, String).ilike(pattern),
                    )
                )
            if normalized_role is not None:
                stmt = stmt.where(Membership.role == normalized_role)

            total = db.execute(stmt).scalar_one()
            return int(total)

        return await self.execute_read(read_op)

    async def get_employee(self, *, user_id: UUID) -> EmployeeRecord:
        def read_op(db: Session) -> EmployeeRecord:
            membership, user = self._get_membership_and_user(db=db, user_id=user_id)
            if membership is None or user is None:
                raise AppError(status_code=404, code="employee_not_found", message="Employee not found")
            return EmployeeRecord(
                user_id=user.id,
                tenant_id=membership.tenant_id,
                email=user.email,
                role=membership.role,
                is_active=bool(user.is_active),
                version=int(membership.version),
                created_at=user.created_at,
            )

        return await self.execute_read(read_op)

    async def create_employee(
        self,
        *,
        email: str,
        password: str,
        role: str,
        idempotency_key: str | None = None,
    ) -> EmployeeRecord:
        normalized_email = self._normalize_email(email)
        normalized_password = self._normalize_password(password)
        normalized_role = self._normalize_role(role)

        idempotency_decision: IdempotencyDecision | None = None
        if idempotency_key and idempotency_key.strip() and self.actor_user_id is not None:
            payload_hash = self.idempotency_service.build_request_hash(
                {
                    "email": normalized_email,
                    "role": normalized_role.value,
                }
            )
            idempotency_decision = await self.idempotency_service.begin(
                tenant_id=self.tenant_id,
                actor_id=self.actor_user_id,
                route="POST:/users",
                key=idempotency_key.strip()[:128],
                request_hash=payload_hash,
            )
            if not idempotency_decision.proceed:
                if not isinstance(idempotency_decision.response_payload, dict):
                    raise AppError(status_code=503, code="idempotency_invalid_payload", message="Invalid idempotency payload")
                return EmployeeRecord(
                    user_id=idempotency_decision.response_payload["user_id"],
                    tenant_id=idempotency_decision.response_payload["tenant_id"],
                    email=idempotency_decision.response_payload["email"],
                    role=MembershipRole(idempotency_decision.response_payload["role"]),
                    is_active=bool(idempotency_decision.response_payload["is_active"]),
                    version=int(idempotency_decision.response_payload["version"]),
                    created_at=idempotency_decision.response_payload["created_at"],
                )

        def write_op(db: Session) -> EmployeeRecord:
            auth_repo = AuthRepository(db)
            existing_user = auth_repo.get_user_by_email(normalized_email)

            if existing_user is not None:
                existing_membership = auth_repo.get_membership(user_id=existing_user.id, tenant_id=self.tenant_id)
                if existing_membership is not None:
                    raise AppError(status_code=409, code="employee_exists", message="Employee already exists")

                membership = auth_repo.create_membership(
                    user_id=existing_user.id,
                    tenant_id=self.tenant_id,
                    role=normalized_role,
                )
                if not existing_user.is_active:
                    existing_user.is_active = True

                return EmployeeRecord(
                    user_id=existing_user.id,
                    tenant_id=membership.tenant_id,
                    email=existing_user.email,
                    role=membership.role,
                    is_active=bool(existing_user.is_active),
                    version=int(membership.version),
                    created_at=existing_user.created_at,
                )

            password_hash = self.password_hasher.hash(normalized_password)
            user = auth_repo.create_user(email=normalized_email, password_hash=password_hash, is_active=True)
            membership = auth_repo.create_membership(user_id=user.id, tenant_id=self.tenant_id, role=normalized_role)

            return EmployeeRecord(
                user_id=user.id,
                tenant_id=membership.tenant_id,
                email=user.email,
                role=membership.role,
                is_active=bool(user.is_active),
                version=int(membership.version),
                created_at=user.created_at,
            )

        try:
            created = await self.execute_write(write_op, idempotent=False)
        except Exception:
            if idempotency_decision and idempotency_decision.record_id is not None:
                await self._safe_mark_idempotency_failed(idempotency_decision.record_id)
            raise

        if idempotency_decision and idempotency_decision.record_id is not None:
            await self.idempotency_service.mark_succeeded(
                tenant_id=self.tenant_id,
                record_id=idempotency_decision.record_id,
                response_payload=self.to_payload(created),
            )
        await invalidate_membership_cache_async(tenant_id=self.tenant_id, user_id=created.user_id)
        return created

    async def _safe_mark_idempotency_failed(self, record_id: UUID) -> None:
        try:
            await self.idempotency_service.mark_failed(tenant_id=self.tenant_id, record_id=record_id)
        except Exception:
            return

    async def update_employee(
        self,
        *,
        user_id: UUID,
        email: str | None = None,
        password: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> EmployeeRecord:
        normalized_email = self._normalize_email(email) if email is not None else None
        normalized_password = self._normalize_password(password) if password is not None else None
        normalized_role = self._normalize_role(role) if role is not None else None

        if normalized_email is None and normalized_password is None and normalized_role is None and is_active is None:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> EmployeeRecord:
            membership, user = self._get_membership_and_user(db=db, user_id=user_id)
            if membership is None or user is None:
                raise AppError(status_code=404, code="employee_not_found", message="Employee not found")

            if normalized_email is not None and normalized_email != user.email:
                auth_repo = AuthRepository(db)
                existing_user = auth_repo.get_user_by_email(normalized_email)
                if existing_user is not None and existing_user.id != user.id:
                    raise AppError(status_code=409, code="email_already_exists", message="Email already exists")
                user.email = normalized_email

            if normalized_password is not None:
                user.password_hash = self.password_hasher.hash(normalized_password)

            if normalized_role is not None:
                membership.role = normalized_role

            if is_active is not None:
                user.is_active = bool(is_active)

            db.flush()
            return EmployeeRecord(
                user_id=user.id,
                tenant_id=membership.tenant_id,
                email=user.email,
                role=membership.role,
                is_active=bool(user.is_active),
                version=int(membership.version),
                created_at=user.created_at,
            )

        updated = await self.execute_write(write_op, idempotent=False)
        await invalidate_membership_cache_async(tenant_id=self.tenant_id, user_id=updated.user_id)
        return updated

    async def delete_employee(self, *, user_id: UUID) -> None:
        def write_op(db: Session) -> tuple[UUID, MembershipRole]:
            membership, _user = self._get_membership_and_user(db=db, user_id=user_id)
            if membership is None:
                raise AppError(status_code=404, code="employee_not_found", message="Employee not found")

            if membership.role == MembershipRole.OWNER:
                owners_count = int(
                    db.execute(
                        select(func.count())
                        .select_from(Membership)
                        .where(
                            Membership.tenant_id == self.tenant_id,
                            Membership.role == MembershipRole.OWNER,
                        )
                    ).scalar_one()
                )
                if owners_count <= 1:
                    raise AppError(
                        status_code=400,
                        code="last_owner_delete_forbidden",
                        message="Cannot remove the last owner",
                    )

            db.execute(
                delete(Membership).where(
                    Membership.tenant_id == self.tenant_id,
                    Membership.user_id == user_id,
                )
            )
            return user_id, membership.role

        deleted_user_id, _deleted_role = await self.execute_write(write_op, idempotent=False)
        await invalidate_membership_cache_async(tenant_id=self.tenant_id, user_id=deleted_user_id)

    @staticmethod
    def _normalize_query(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized[:120] if normalized else None

    @staticmethod
    def _normalize_password(value: str) -> str:
        normalized = (value or "").strip()
        if len(normalized) < 8 or len(normalized) > 128:
            raise AppError(status_code=400, code="invalid_password", message="Password must be 8-128 characters")
        return normalized

    @staticmethod
    def _normalize_email(value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise AppError(status_code=400, code="invalid_email", message="Email is required")
        try:
            validated = validate_email(candidate, check_deliverability=False)
        except EmailNotValidError as exc:
            raise AppError(status_code=400, code="invalid_email", message="Invalid email") from exc
        return validated.normalized

    @staticmethod
    def _normalize_role(value: str | MembershipRole) -> MembershipRole:
        raw = value.value if isinstance(value, MembershipRole) else str(value)
        candidate = raw.strip().lower()
        try:
            return MembershipRole(candidate)
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_role", message="Invalid role") from exc

    @staticmethod
    def _normalize_role_nullable(value: str | None) -> MembershipRole | None:
        if value is None or not value.strip():
            return None
        return EmployeeService._normalize_role(value)

    @staticmethod
    def _validate_pagination(*, limit: int, offset: int) -> None:
        if limit <= 0 or limit > 100 or offset < 0:
            raise AppError(
                status_code=400,
                code="invalid_pagination",
                message="Pagination must satisfy 0 < limit <= 100 and offset >= 0",
            )

    def _get_membership_and_user(self, *, db: Session, user_id: UUID) -> tuple[Membership | None, User | None]:
        stmt = (
            select(Membership, User)
            .join(User, Membership.user_id == User.id)
            .where(
                Membership.tenant_id == self.tenant_id,
                Membership.user_id == user_id,
            )
        )
        row = db.execute(stmt).first()
        if row is None:
            return None, None
        membership, user = row
        return membership, user

    @staticmethod
    def to_payload(employee: EmployeeRecord) -> dict[str, Any]:
        return {
            "user_id": employee.user_id,
            "tenant_id": employee.tenant_id,
            "email": employee.email,
            "role": employee.role.value,
            "is_active": employee.is_active,
            "version": employee.version,
            "created_at": employee.created_at,
        }
