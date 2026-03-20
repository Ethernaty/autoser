from __future__ import annotations

import logging

from starlette.concurrency import run_in_threadpool

from app.core.database import SessionLocal
from app.repositories.client_repository import ClientRepository
from app.tasks.base import TaskContext


logger = logging.getLogger("app.tasks.client_stats")


async def recalculate_client_stats_task(context: TaskContext, payload: dict[str, object]) -> None:
    """Example distributed-safe background task for tenant client statistics."""

    tenant_id = context.tenant_id

    def compute() -> tuple[int, int]:
        db = SessionLocal()
        transaction = db.begin()
        try:
            repo = ClientRepository(db=db, tenant_id=tenant_id)
            total_clients = repo.count(query=None)
            searchable_clients = repo.count(query="")
            transaction.commit()
            return total_clients, searchable_clients
        except Exception:
            transaction.rollback()
            raise
        finally:
            db.close()

    total_clients, searchable_clients = await run_in_threadpool(compute)

    logger.info(
        "recalculate_client_stats_done",
        extra={
            "task_id": str(context.task_id),
            "tenant_id": str(tenant_id),
            "total_clients": total_clients,
            "searchable_clients": searchable_clients,
            "request_id": context.request_id,
            "correlation_id": context.correlation_id,
        },
    )
