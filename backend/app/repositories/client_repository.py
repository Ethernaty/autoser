from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.repositories.base import BaseRepositoryTenantScoped


class ClientRepository(BaseRepositoryTenantScoped[Client]):
    """Data-access layer for tenant-scoped clients."""

    ALLOWED_UPDATE_FIELDS = {"name", "phone", "email", "source", "comment"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=Client, tenant_id=tenant_id)

    def get_by_phone(self, phone: str) -> Client | None:
        """Return client by normalized phone within current tenant."""
        stmt = self.scoped_select(Client.phone == phone, Client.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, entity_id: UUID) -> Client | None:
        stmt = self.scoped_select(Client.id == entity_id, Client.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_ids(self, ids: list[UUID]) -> list[Client]:
        if not ids:
            return []
        stmt = self.scoped_select(Client.id.in_(ids), Client.deleted_at.is_(None))
        return list(self.db.execute(stmt).scalars().all())

    def search(self, query: str, limit: int = 50, offset: int = 0) -> list[Client]:
        """Search clients by name, phone, email and source."""
        pattern = f"%{query}%"
        stmt = (
            self.scoped_select(
                Client.deleted_at.is_(None),
                or_(
                    Client.name.ilike(pattern),
                    Client.phone.ilike(pattern),
                    Client.email.ilike(pattern),
                    Client.source.ilike(pattern),
                )
            )
            .order_by(Client.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def paginate(self, limit: int, offset: int) -> list[Client]:
        """List clients using limit/offset pagination."""
        stmt = (
            self.scoped_select(Client.deleted_at.is_(None))
            .order_by(Client.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def update(self, client_id: UUID, **updates: object) -> Client | None:
        """Update client fields and flush session."""
        client = self.get_by_id(client_id)
        if client is None:
            return None
        for key, value in updates.items():
            if key not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(client, key, value)
        self.db.flush()
        self.db.refresh(client)
        return client

    def exists_by_phone(self, phone: str, exclude_client_id: UUID | None = None) -> bool:
        """Check if a phone already exists within tenant scope."""
        criteria: list[object] = [Client.phone == phone, Client.deleted_at.is_(None)]
        if exclude_client_id is not None:
            criteria.append(Client.id != exclude_client_id)
        stmt: Select[tuple[int]] = select(func.count()).select_from(Client).where(
            Client.tenant_id == self.tenant_id,
            *criteria,
        )
        total = self.db.execute(stmt).scalar_one()
        return total > 0

    def count(self, query: str | None = None) -> int:
        """Count clients in tenant scope with optional search query."""
        stmt = select(func.count()).select_from(Client).where(
            Client.tenant_id == self.tenant_id,
            Client.deleted_at.is_(None),
        )
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Client.name.ilike(pattern),
                    Client.phone.ilike(pattern),
                    Client.email.ilike(pattern),
                    Client.source.ilike(pattern),
                )
            )
        return int(self.db.execute(stmt).scalar_one())

    def soft_delete_by_id(self, entity_id: UUID, *, deleted_at) -> bool:
        client = self.get_by_id(entity_id)
        if client is None:
            return False
        client.deleted_at = deleted_at
        self.db.flush()
        return True

    def bulk_create(self, payloads: list[dict[str, object]]) -> list[Client]:
        clients: list[Client] = []
        for payload in payloads:
            clients.append(self.create(**payload))
        self.db.flush()
        return clients

    def get_fields(self, client_id: UUID, fields: set[str]) -> dict[str, object] | None:
        client = self.get_by_id(client_id)
        if client is None:
            return None
        return {field: getattr(client, field) for field in fields if hasattr(client, field)}
