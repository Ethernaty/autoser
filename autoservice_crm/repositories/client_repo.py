from contextlib import closing
from typing import List, Optional

from database.connection import get_connection
from models.client import Client


class ClientRepository:
    def get_all(self, search: str = "") -> List[Client]:
        with closing(get_connection()) as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    """
                    SELECT * FROM clients
                    WHERE full_name LIKE ? OR phone LIKE ?
                    ORDER BY full_name
                    """,
                    (like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM clients ORDER BY full_name"
                ).fetchall()
        return [Client.from_row(r) for r in rows]

    def get_by_id(self, client_id: int) -> Optional[Client]:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?",
                (client_id,),
            ).fetchone()
        return Client.from_row(row)

    def create(self, client: Client) -> Client:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                "INSERT INTO clients (full_name, phone, notes) VALUES (?, ?, ?)",
                (client.full_name, client.phone, client.notes),
            )
            client.id = cursor.lastrowid
            conn.commit()
        return client

    def update(self, client: Client) -> Client:
        with closing(get_connection()) as conn:
            conn.execute(
                "UPDATE clients SET full_name=?, phone=?, notes=? WHERE id=?",
                (client.full_name, client.phone, client.notes, client.id),
            )
            conn.commit()
        return client

    def delete(self, client_id: int) -> None:
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
