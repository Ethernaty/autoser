from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DB_DIR / "autoservice.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name   TEXT    NOT NULL,
                phone       TEXT    NOT NULL,
                notes       TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS vehicles (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id      INTEGER NOT NULL,
                make           TEXT    NOT NULL,
                model          TEXT    NOT NULL,
                vin            TEXT    DEFAULT '',
                license_plate  TEXT    DEFAULT '',
                year           INTEGER,
                created_at     TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employees (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name       TEXT    NOT NULL,
                commission_pct  INTEGER NOT NULL DEFAULT 40,
                created_at      TEXT    DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS work_orders (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id     INTEGER NOT NULL,
                vehicle_id    INTEGER NOT NULL,
                status        TEXT    NOT NULL DEFAULT 'accepted',
                notes         TEXT    DEFAULT '',
                total_amount  REAL    DEFAULT 0,
                created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (client_id)  REFERENCES clients(id)  ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS work_items (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id  INTEGER NOT NULL,
                name           TEXT    NOT NULL,
                price          REAL    NOT NULL DEFAULT 0,
                employee_id    INTEGER,
                created_at     TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id)   REFERENCES employees(id)   ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_vehicles_client ON vehicles(client_id);
            CREATE INDEX IF NOT EXISTS idx_orders_client ON work_orders(client_id);
            CREATE INDEX IF NOT EXISTS idx_orders_vehicle ON work_orders(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON work_orders(status);
            CREATE INDEX IF NOT EXISTS idx_items_order ON work_items(work_order_id);
            CREATE INDEX IF NOT EXISTS idx_items_employee ON work_items(employee_id);

            CREATE TRIGGER IF NOT EXISTS trg_work_items_insert_total
            AFTER INSERT ON work_items
            BEGIN
                UPDATE work_orders
                SET total_amount = COALESCE(
                    (SELECT SUM(price) FROM work_items WHERE work_order_id = NEW.work_order_id), 0
                )
                WHERE id = NEW.work_order_id;
            END;

            CREATE TRIGGER IF NOT EXISTS trg_work_items_update_total
            AFTER UPDATE OF price, work_order_id ON work_items
            BEGIN
                UPDATE work_orders
                SET total_amount = COALESCE(
                    (SELECT SUM(price) FROM work_items WHERE work_order_id = OLD.work_order_id), 0
                )
                WHERE id = OLD.work_order_id;

                UPDATE work_orders
                SET total_amount = COALESCE(
                    (SELECT SUM(price) FROM work_items WHERE work_order_id = NEW.work_order_id), 0
                )
                WHERE id = NEW.work_order_id;
            END;

            CREATE TRIGGER IF NOT EXISTS trg_work_items_delete_total
            AFTER DELETE ON work_items
            BEGIN
                UPDATE work_orders
                SET total_amount = COALESCE(
                    (SELECT SUM(price) FROM work_items WHERE work_order_id = OLD.work_order_id), 0
                )
                WHERE id = OLD.work_order_id;
            END;
            """
        )

        # Lightweight schema migration for existing installations.
        _ensure_column(conn, "vehicles", "vin", "TEXT DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin)")
