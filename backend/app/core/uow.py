from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.core.runtime_guards import pop_uow_depth, push_uow_depth


class UnitOfWork(Protocol):
    session: Session

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass
class SqlAlchemyUnitOfWork:
    """Transactional unit-of-work for sync SQLAlchemy session."""

    session_factory: sessionmaker[Session] = SessionLocal
    session: Session | None = None
    _transaction = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        push_uow_depth()
        self.session = self.session_factory()
        self._transaction = self.session.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session is None or self._transaction is None:
            pop_uow_depth()
            return
        if exc_type is None:
            self._transaction.commit()
        else:
            self._transaction.rollback()
        self.session.close()
        self.session = None
        self._transaction = None
        pop_uow_depth()

    def commit(self) -> None:
        if self._transaction is not None:
            self._transaction.commit()

    def rollback(self) -> None:
        if self._transaction is not None:
            self._transaction.rollback()

    def close(self) -> None:
        if self.session is not None:
            if self._transaction is not None and self._transaction.is_active:
                self._transaction.rollback()
            self.session.close()
            self.session = None
            self._transaction = None
        pop_uow_depth()
