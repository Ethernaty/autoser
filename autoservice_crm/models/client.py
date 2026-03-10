"""
Модель клиента.

Почему dataclass, а не просто dict:
- Автокомплит в IDE (phone, full_name — а не row["phone"])
- Типизация: mypy/pyright ловят ошибки ДО запуска
- Читаемость: сразу видно, какие поля есть у сущности
- from_row() — единственная точка маппинга из БД в объект
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Client:
    full_name: str
    phone: str
    notes: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Client":
        """Создаёт объект из sqlite3.Row."""
        if row is None:
            return None
        return cls(
            id=row["id"],
            full_name=row["full_name"],
            phone=row["phone"],
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )
