from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_alembic_config():
    from alembic.config import Config as AlembicConfig

    root = get_project_root()
    config = AlembicConfig(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    return config


def get_migration_head_revision() -> str:
    from alembic.script import ScriptDirectory

    config = get_alembic_config()
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if not heads:
        raise RuntimeError("alembic_head_missing")
    if len(heads) != 1:
        raise RuntimeError("multiple_alembic_heads")
    return str(heads[0])


def get_database_revision(engine: Engine) -> str | None:
    query = text("SELECT version_num FROM alembic_version")
    try:
        with engine.connect() as connection:
            rows = [str(row[0]) for row in connection.execute(query).fetchall() if row and row[0] is not None]
    except SQLAlchemyError:
        return None

    if not rows:
        return None
    if len(rows) != 1:
        raise RuntimeError("multiple_database_alembic_versions")
    return rows[0]


def assert_database_schema_up_to_date(engine: Engine) -> None:
    current = get_database_revision(engine)
    head = get_migration_head_revision()
    if current != head:
        raise RuntimeError(
            f"database_schema_mismatch current={current or 'none'} head={head}; run migration upgrade before startup"
        )
