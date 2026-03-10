from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import Any, Protocol

TaskFunc = Callable[..., Any]


@dataclass(frozen=True)
class TaskDefinition:
    name: str
    func: TaskFunc
    max_retries: int
    retry_base_delay_seconds: float


class TaskRegistryProtocol(Protocol):
    def register(self, *, name: str, func: TaskFunc, max_retries: int, retry_base_delay_seconds: float) -> TaskDefinition:
        ...

    def get(self, task_name: str) -> TaskDefinition | None:
        ...


class TaskRegistry(TaskRegistryProtocol):
    """In-process task registry with decorator API."""

    def __init__(self):
        self._tasks: dict[str, TaskDefinition] = {}

    def register(self, *, name: str, func: TaskFunc, max_retries: int, retry_base_delay_seconds: float) -> TaskDefinition:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' is already registered")
        definition = TaskDefinition(
            name=name,
            func=func,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
        )
        self._tasks[name] = definition
        return definition

    def get(self, task_name: str) -> TaskDefinition | None:
        return self._tasks.get(task_name)

    def task(
        self,
        name: str | None = None,
        *,
        max_retries: int = 3,
        retry_base_delay_seconds: float = 1.0,
    ) -> Callable[[TaskFunc], TaskFunc]:
        """Decorator used to register a task."""

        def decorator(func: TaskFunc) -> TaskFunc:
            task_name = name or func.__name__
            self.register(
                name=task_name,
                func=func,
                max_retries=max_retries,
                retry_base_delay_seconds=retry_base_delay_seconds,
            )
            return func

        return decorator


default_task_registry = TaskRegistry()


def task(
    name: str | None = None,
    *,
    max_retries: int = 3,
    retry_base_delay_seconds: float = 1.0,
) -> Callable[[TaskFunc], TaskFunc]:
    """Global task decorator for default registry."""
    return default_task_registry.task(
        name=name,
        max_retries=max_retries,
        retry_base_delay_seconds=retry_base_delay_seconds,
    )
