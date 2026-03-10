from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = ["PERMISSION_MATRIX", "check_permission", "SqlAlchemyUnitOfWork"]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "PERMISSION_MATRIX": ("app.core.permissions", "PERMISSION_MATRIX"),
    "check_permission": ("app.core.permissions", "check_permission"),
    "SqlAlchemyUnitOfWork": ("app.core.uow", "SqlAlchemyUnitOfWork"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
