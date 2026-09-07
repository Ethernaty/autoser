"""Database-wide client directory and atomic, previewable CSV imports."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.vehicle import Vehicle
from app.repositories.client_repository import ClientRepository


class ClientDirectoryMixin:
    async def directory(self, *, query=None, sort="recent", activity="all", source=None, limit=20, offset=0):
        self._validate_pagination(limit=limit, offset=offset)

        def read(db):
            visits = select(func.count(Order.id)).where(Order.tenant_id == self.tenant_id, Order.client_id == Client.id).correlate(Client).scalar_subquery()
            last_visit = select(func.max(Order.created_at)).where(Order.tenant_id == self.tenant_id, Order.client_id == Client.id).correlate(Client).scalar_subquery()
            has_vehicle = exists(select(Vehicle.id).where(Vehicle.tenant_id == self.tenant_id, Vehicle.client_id == Client.id, Vehicle.archived_at.is_(None)))
            active = exists(select(Order.id).where(Order.tenant_id == self.tenant_id, Order.client_id == Client.id, Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS])))
            criteria = [Client.tenant_id == self.tenant_id, Client.deleted_at.is_(None)]
            if query:
                pattern = f"%{query.strip()[:100]}%"
                criteria.append(or_(Client.name.ilike(pattern), Client.phone.ilike(pattern), Client.email.ilike(pattern), Client.source.ilike(pattern)))
            if source:
                criteria.append(Client.source == source)
            if activity == "active":
                criteria.append(active)
            elif activity == "never":
                criteria.append(visits == 0)
            elif activity == "recent":
                criteria.append(last_visit >= datetime.now(UTC) - timedelta(days=90))
            elif activity == "inactive":
                criteria.append(or_(last_visit.is_(None), last_visit < datetime.now(UTC) - timedelta(days=90)))
            ordering = {"name": [func.lower(Client.name).asc()], "activity": [visits.desc(), last_visit.desc().nullslast()], "recent": [Client.updated_at.desc()]}[sort]
            rows = db.execute(select(Client).where(*criteria).order_by(*ordering, Client.id).limit(limit).offset(offset)).scalars().all()
            # The same WHERE clause is shared by rows and totals; pagination is never applied to totals.
            stats = db.execute(select(func.count(Client.id), func.sum(case((active, 1), else_=0)), func.sum(case((has_vehicle, 1), else_=0)), func.sum(case((visits == 0, 1), else_=0))).where(*criteria)).one()
            return [self._client_to_payload(c) for c in rows], dict(zip(["total", "active_clients", "with_vehicles", "without_orders"], [int(v or 0) for v in stats]))

        rows, summary = await self.execute_read(read)
        return [self._payload_to_client(self._mask_payload(row)) for row in rows], summary

    def _parse_client_csv(self, text):
        if len(text.encode("utf-8")) > 1024 * 1024:
            raise AppError(status_code=400, code="csv_too_large", message="CSV: не более 1 МБ")
        aliases = {"имя": "name", "фио": "name", "телефон": "phone", "почта": "email", "источник": "source", "комментарий": "comment"}
        sample = text.lstrip("\ufeff")
        delimiter = ";" if sample.splitlines() and sample.splitlines()[0].count(";") > sample.splitlines()[0].count(",") else ","
        reader = csv.DictReader(io.StringIO(sample), delimiter=delimiter)
        headers = [aliases.get(h.strip().lower(), h.strip().lower()) for h in reader.fieldnames or []]
        if "name" not in headers or "phone" not in headers or len(headers) != len(set(headers)):
            raise AppError(status_code=400, code="csv_headers", message="CSV должен содержать уникальные колонки name (имя) и phone (телефон)")
        reader.fieldnames = headers
        rows = []
        for index, row in enumerate(reader, start=2):
            if len(rows) >= 500:
                raise AppError(status_code=400, code="csv_too_many_rows", message="Не более 500 клиентов за импорт")
            try:
                if None in row:
                    raise ValueError("Количество полей не соответствует заголовку")
                normalized = {"name": self._normalize_required_string(row.get("name") or "", field="name", max_length=200), "phone": self._normalize_phone(row.get("phone") or ""), "email": self._normalize_email(row.get("email")), "source": self._normalize_optional_string(row.get("source"), max_length=120), "comment": self._normalize_optional_string(row.get("comment"), max_length=5000)}
                rows.append({"row": index, "data": normalized, "status": "ready", "message": "Готов к импорту"})
            except (AppError, ValueError) as exc:
                rows.append({"row": index, "data": {"name": row.get("name", ""), "phone": row.get("phone", "")}, "status": "invalid", "message": str(getattr(exc, "message", exc))})
        if not rows:
            raise AppError(status_code=400, code="csv_empty", message="В CSV нет клиентов")
        return rows

    def _check_import_duplicates(self, db, rows):
        phones = [r["data"]["phone"] for r in rows if r["status"] == "ready"]
        existing = {c.phone: c for c in db.execute(select(Client).where(Client.tenant_id == self.tenant_id, Client.phone.in_(phones))).scalars()}
        seen = set()
        for row in rows:
            if row["status"] != "ready":
                continue
            phone = row["data"]["phone"]
            match = existing.get(phone)
            if match or phone in seen:
                row.update(status="duplicate", message=(f"Телефон уже есть: {match.name}" if match else "Телефон повторяется в файле"))
                if match and match.deleted_at is None:
                    row["existing_client_id"] = str(match.id)
            seen.add(phone)
        return rows

    async def import_clients(self, *, csv_text, commit=False):
        rows = self._parse_client_csv(csv_text)

        def operation(db):
            checked = self._check_import_duplicates(db, rows)
            created = 0
            if commit:
                if any(r["status"] == "invalid" for r in checked):
                    raise AppError(status_code=400, code="csv_invalid_rows", message="Исправьте ошибочные строки перед импортом")
                repo = ClientRepository(db, tenant_id=self.tenant_id)
                for row in checked:
                    if row["status"] == "ready":
                        repo.create(**row["data"])
                        created += 1
            return {"rows": checked, "created": created, "ready": sum(r["status"] == "ready" for r in checked), "duplicates": sum(r["status"] == "duplicate" for r in checked), "invalid": sum(r["status"] == "invalid" for r in checked)}
        try:
            result = await (self.execute_write(operation) if commit else self.execute_read(operation))
        except IntegrityError as exc:
            raise AppError(status_code=409, code="csv_concurrent_duplicate", message="База изменилась. Обновите предпросмотр; импорт отменён целиком") from exc
        if commit:
            await self._bump_namespace_version()
        return result
