from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.exceptions import TenantScopeError
from app.core.tenant_scope import get_current_tenant_id
from app.core.tracing import mark_span_error, start_span
from app.models.base import BaseModel


ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepositoryTenantScoped(Generic[ModelType]):
    def __init__(self, db: Session, model: type[ModelType], tenant_id: UUID | None):
        context_tenant_id = get_current_tenant_id(required=False)
        effective_tenant_id = tenant_id or context_tenant_id

        if effective_tenant_id is None:
            raise TenantScopeError(
                code="tenant_scope_required",
                message="Tenant scope is required for repository operations",
            )

        if context_tenant_id is not None and context_tenant_id != effective_tenant_id:
            raise TenantScopeError(
                code="tenant_scope_mismatch",
                message="Repository tenant does not match request tenant scope",
                details={
                    "context_tenant_id": str(context_tenant_id),
                    "repository_tenant_id": str(effective_tenant_id),
                },
            )

        self.db = db
        self.model = model
        self.tenant_id = effective_tenant_id

        if not hasattr(self.model, "tenant_id"):
            raise TenantScopeError(
                code="invalid_tenant_model",
                message=f"Model {self.model.__name__} is not tenant-scoped",
                status_code=500,
            )

    def scoped_select(self, *criteria: Any) -> Select[Any]:
        return select(self.model).where(self.model.tenant_id == self.tenant_id, *criteria)

    def list(self, *criteria: Any) -> list[ModelType]:
        with start_span(
            f"repository.list.{self.model.__name__}",
            attributes={"tenant.id": str(self.tenant_id), "repository.model": self.model.__name__},
        ) as span:
            try:
                stmt = self.scoped_select(*criteria)
                return list(self.db.execute(stmt).scalars().all())
            except Exception as exc:
                mark_span_error(span, exc)
                raise

    def get_by_id(self, entity_id: UUID) -> ModelType | None:
        with start_span(
            f"repository.get_by_id.{self.model.__name__}",
            attributes={"tenant.id": str(self.tenant_id), "repository.model": self.model.__name__},
        ) as span:
            try:
                stmt = self.scoped_select(self.model.id == entity_id)
                return self.db.execute(stmt).scalar_one_or_none()
            except Exception as exc:
                mark_span_error(span, exc)
                raise

    def create(self, **data: Any) -> ModelType:
        payload = dict(data)
        payload_tenant_id = payload.pop("tenant_id", self.tenant_id)
        if payload_tenant_id != self.tenant_id:
            raise TenantScopeError(
                code="tenant_mismatch",
                message="Tenant mismatch in create operation",
            )

        with start_span(
            f"repository.create.{self.model.__name__}",
            attributes={"tenant.id": str(self.tenant_id), "repository.model": self.model.__name__},
        ) as span:
            try:
                entity = self.model(**payload, tenant_id=self.tenant_id)
                self.db.add(entity)
                self.db.flush()
                return entity
            except Exception as exc:
                mark_span_error(span, exc)
                raise

    def delete_by_id(self, entity_id: UUID) -> bool:
        with start_span(
            f"repository.delete_by_id.{self.model.__name__}",
            attributes={"tenant.id": str(self.tenant_id), "repository.model": self.model.__name__},
        ) as span:
            try:
                entity = self.get_by_id(entity_id)
                if entity is None:
                    return False
                self.db.delete(entity)
                self.db.flush()
                return True
            except Exception as exc:
                mark_span_error(span, exc)
                raise
