from __future__ import annotations

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import get_settings
from app.core.exceptions import TenantScopeError
from app.core.prometheus_metrics import get_metrics_registry
from app.core.runtime_guards import assert_sync_db_call_safe
from app.core.tenant_scope import get_current_endpoint, get_current_tenant_id
from app.models.base import Base, TenantScopedMixin


settings = get_settings()
slow_query_logger = logging.getLogger("app.db.slow_query")


class TenantGuardedSession(Session):
    """Session enforcing sync/tenant safety guards."""

    def begin(self, *args, **kwargs):  # type: ignore[override]
        assert_sync_db_call_safe()
        if self.in_transaction():
            raise RuntimeError("nested_transaction_detected")
        return super().begin(*args, **kwargs)

    def execute(self, *args, **kwargs):  # type: ignore[override]
        assert_sync_db_call_safe()
        return super().execute(*args, **kwargs)


engine: Engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_timeout=settings.db_pool_timeout_seconds,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=TenantGuardedSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    autobegin=False,
)


TENANT_SCOPED_TABLES = {
    mapper.local_table.name
    for mapper in Base.registry.mappers
    if isinstance(mapper.class_, type) and issubclass(mapper.class_, TenantScopedMixin)
}


def _statement_targets_tenant_scope(orm_execute_state) -> bool:  # noqa: ANN001
    bind_mapper = getattr(orm_execute_state, "bind_mapper", None)
    if bind_mapper is not None:
        cls = getattr(bind_mapper, "class_", None)
        if isinstance(cls, type) and issubclass(cls, TenantScopedMixin):
            return True

    statement = orm_execute_state.statement
    descriptions = getattr(statement, "column_descriptions", []) or []
    for description in descriptions:
        entity = description.get("entity")
        if isinstance(entity, type) and issubclass(entity, TenantScopedMixin):
            return True

    try:
        froms = statement.get_final_froms()
    except Exception:
        return False

    for from_clause in froms:
        table_name = getattr(from_clause, "name", None)
        if isinstance(table_name, str) and table_name in TENANT_SCOPED_TABLES:
            return True
    return False


@event.listens_for(TenantGuardedSession, "do_orm_execute")
def enforce_tenant_scope(orm_execute_state) -> None:  # noqa: ANN001
    if orm_execute_state.is_column_load or orm_execute_state.is_relationship_load:
        # relationship/column loads still inherit criteria from parent query
        pass

    has_tenant_scope = _statement_targets_tenant_scope(orm_execute_state)
    current_tenant_id = get_current_tenant_id(required=False)

    if has_tenant_scope and current_tenant_id is None:
        raise TenantScopeError(
            code="tenant_scope_required",
            message="Tenant scope is required for tenant-scoped query execution",
        )

    if not has_tenant_scope or current_tenant_id is None:
        return

    statement = orm_execute_state.statement
    if orm_execute_state.is_select:
        orm_execute_state.statement = statement.options(
            with_loader_criteria(
                TenantScopedMixin,
                lambda cls: cls.tenant_id == current_tenant_id,
                include_aliases=True,
            )
        )
        return

    if orm_execute_state.is_update or orm_execute_state.is_delete:
        bind_mapper = getattr(orm_execute_state, "bind_mapper", None)
        cls = getattr(bind_mapper, "class_", None) if bind_mapper is not None else None
        if isinstance(cls, type) and issubclass(cls, TenantScopedMixin):
            orm_execute_state.statement = statement.where(cls.tenant_id == current_tenant_id)


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn: Connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())
    conn.info.setdefault("query_statement", []).append(statement)
    conn.info.setdefault("query_parameters", []).append(parameters)


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn: Connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
    start_stack = conn.info.get("query_start_time", None)
    statement_stack = conn.info.get("query_statement", None)
    parameter_stack = conn.info.get("query_parameters", None)
    if not start_stack:
        return

    started_at = start_stack.pop()
    stmt = statement_stack.pop() if statement_stack else statement or ""
    params = parameter_stack.pop() if parameter_stack else parameters

    duration_seconds = max(0.0, time.perf_counter() - started_at)
    duration_ms = duration_seconds * 1000.0
    get_metrics_registry().observe_db_query(statement=stmt or "", duration_seconds=duration_seconds)

    if duration_ms >= settings.slow_query_threshold_ms:
        slow_query_logger.warning(
            "slow_query_detected",
            extra={
                "tenant_id": str(get_current_tenant_id(required=False)) if get_current_tenant_id(required=False) else None,
                "path": get_current_endpoint(),
                "duration_ms": round(duration_ms, 3),
                "sql": str(stmt)[:2000],
                "params": repr(params)[:1000],
            },
        )


@event.listens_for(Engine, "handle_error")
def handle_db_error(context) -> None:  # noqa: ANN001
    get_metrics_registry().increment_app_error(source="db", code="query_failed")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    transaction = db.begin()
    try:
        yield db
        transaction.commit()
    except Exception:
        transaction.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_context() -> Generator[Session, None, None]:
    db = SessionLocal()
    transaction = db.begin()
    try:
        yield db
        transaction.commit()
    except Exception:
        transaction.rollback()
        raise
    finally:
        db.close()


def check_database_health() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_current_alembic_revision() -> str | None:
    query = text("SELECT version_num FROM alembic_version")
    with engine.connect() as connection:
        result = connection.execute(query)
        rows = [str(row[0]) for row in result.fetchall() if row and row[0] is not None]

    if not rows:
        return None
    if len(rows) != 1:
        raise RuntimeError("multiple_alembic_heads_in_database")
    return rows[0]


def drain_database_pool() -> None:
    engine.dispose()
