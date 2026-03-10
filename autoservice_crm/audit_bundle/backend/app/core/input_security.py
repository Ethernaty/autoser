from __future__ import annotations

import html
import re
from uuid import UUID

from app.core.exceptions import AppError


_SQLI_PATTERNS = (
    r"--",
    r";",
    r"/\*",
    r"\*/",
    r"\bunion\b",
    r"\bdrop\b",
    r"\binsert\b",
    r"\bdelete\b",
    r"\bupdate\b",
    r"\bselect\b.+\bfrom\b",
)

_SQLI_RE = re.compile("|".join(_SQLI_PATTERNS), flags=re.IGNORECASE)


def sanitize_text(value: str, *, max_length: int | None = None) -> str:
    """Trim, escape control chars and normalize text payload."""
    normalized = value.strip().replace("\x00", "")
    normalized = html.escape(normalized, quote=False)
    if max_length is not None:
        normalized = normalized[:max_length]
    return normalized


def guard_against_sqli(value: str) -> str:
    """
    Block suspicious SQL fragments in user-provided free-text filters.

    Queries are still executed with SQLAlchemy parameters; this guard is an additional hardening layer.
    """
    normalized = value.strip()
    if not normalized:
        return normalized
    if _SQLI_RE.search(normalized):
        raise AppError(status_code=400, code="invalid_query", message="Invalid search query")
    return normalized


def validate_uuid(value: str, *, field: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}") from exc
