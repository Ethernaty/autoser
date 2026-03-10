from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.tenant_scope import tenant_scope_context
from app.tasks.base import TaskContext
from app.tasks.idempotency import TaskIdempotencyStore
from app.tasks.retry import TaskRetryPolicy, run_with_task_retry


TaskHandler = Callable[[TaskContext, dict[str, Any]], Awaitable[None]]


class TaskWorker:
    """Distributed-ready task worker skeleton with retries and idempotency."""

    def __init__(
        self,
        *,
        idempotency_store: TaskIdempotencyStore,
        logger: logging.Logger | None = None,
    ) -> None:
        self._idempotency_store = idempotency_store
        self._logger = logger or logging.getLogger("app.tasks.worker")

    async def run(
        self,
        *,
        task_name: str,
        context: TaskContext,
        payload: dict[str, Any],
        handler: TaskHandler,
        retry_policy: TaskRetryPolicy | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        retry = retry_policy or TaskRetryPolicy()

        if idempotency_key is not None:
            reserved = await self._idempotency_store.reserve(key=idempotency_key)
            if not reserved:
                self._logger.info(
                    "task_skip_duplicate",
                    extra={
                        "task_name": task_name,
                        "task_id": str(context.task_id),
                        "tenant_id": str(context.tenant_id),
                        "idempotency_key": idempotency_key,
                    },
                )
                return

        async def operation() -> None:
            with tenant_scope_context(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                role=context.role,
            ):
                await handler(context, payload)

        await run_with_task_retry(operation, policy=retry)

        if idempotency_key is not None:
            await self._idempotency_store.mark_done(key=idempotency_key)

        self._logger.info(
            "task_completed",
            extra={
                "task_name": task_name,
                "task_id": str(context.task_id),
                "tenant_id": str(context.tenant_id),
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )
