from __future__ import annotations

from typing import List

from models.client import Client
from repositories.client_repo import ClientRepository
from services.errors import NotFoundError
from services.validators import (
    normalize_optional_text,
    normalize_phone,
    require_non_empty,
    validate_id,
)


class ClientService:
    def __init__(self, repo: ClientRepository | None = None):
        self.repo = repo or ClientRepository()

    def list_clients(self, search: str = "") -> List[Client]:
        return self.repo.get_all((search or "").strip())

    def get_client(self, client_id: int) -> Client:
        client = self.repo.get_by_id(validate_id(client_id, "Клиент"))
        if not client:
            raise NotFoundError("Клиент не найден.")
        return client

    def create_client(self, *, full_name: str, phone: str, notes: str = "") -> Client:
        client = Client(
            full_name=require_non_empty(full_name, "ФИО"),
            phone=normalize_phone(phone),
            notes=normalize_optional_text(notes),
        )
        return self.repo.create(client)

    def update_client(self, client_id: int, *, full_name: str, phone: str, notes: str = "") -> Client:
        client = self.get_client(client_id)
        client.full_name = require_non_empty(full_name, "ФИО")
        client.phone = normalize_phone(phone)
        client.notes = normalize_optional_text(notes)
        return self.repo.update(client)

    def delete_client(self, client_id: int) -> None:
        self.get_client(client_id)
        self.repo.delete(client_id)
