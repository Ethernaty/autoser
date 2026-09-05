"""One tenant-scoped query for registry pages and totals over the entire selection."""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import String, and_, case, cast, exists, false, func, or_, select

from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.payment import Payment
from app.models.vehicle import Vehicle
from app.repositories.order_repository import OrderRepository


class WorkOrderRegistry(OrderRepository):
    def selection(self, *, q=None, status_scope="all", assignee_scope="all", payment_scope="all",
                  date_from=None, date_to=None, overdue=False):
        paid = (select(Payment.order_id, func.sum(Payment.amount).label("amount"))
                .where(Payment.tenant_id == self.tenant_id, Payment.voided_at.is_(None))
                .group_by(Payment.order_id).subquery())
        paid_amount = func.coalesce(paid.c.amount, 0)
        remaining = case((Order.total_amount > paid_amount, Order.total_amount - paid_amount), else_=0)
        stmt = (select(Order, paid_amount.label("paid_amount"), remaining.label("remaining_amount"))
                .outerjoin(paid, paid.c.order_id == Order.id)
                .where(Order.tenant_id == self.tenant_id,
                       *self._build_scope_criteria(status_scope=status_scope, assignee_scope=assignee_scope)))
        if q:
            # Treat wildcard characters as literal user input.
            pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            def matches(column):
                return column.ilike(pattern, escape="\\")
            stmt = stmt.where(or_(
                matches(cast(Order.order_number, String)), matches(Order.description),
                exists(select(1).where(Client.tenant_id == self.tenant_id, Client.id == Order.client_id,
                                      or_(matches(Client.name), matches(Client.phone), matches(Client.email)))),
                exists(select(1).where(Vehicle.tenant_id == self.tenant_id, Vehicle.id == Order.vehicle_id,
                                      or_(matches(Vehicle.plate_number), matches(Vehicle.make_model), matches(Vehicle.vin)))),
            ))
        if payment_scope == "unpaid":
            stmt = stmt.where(paid_amount <= 0, remaining > 0)
        elif payment_scope == "partial":
            stmt = stmt.where(paid_amount > 0, remaining > 0)
        elif payment_scope == "paid":
            stmt = stmt.where(remaining <= 0)
        elif payment_scope == "outstanding":
            stmt = stmt.where(remaining > 0, Order.status != OrderStatus.CANCELLED)
        if date_from:
            stmt = stmt.where(Order.updated_at >= date_from)
        if date_to:
            stmt = stmt.where(Order.updated_at <= date_to)
        if overdue:
            due_at = getattr(Order, "due_at", None)
            stmt = stmt.where(and_(due_at < datetime.now(UTC), Order.status.in_([OrderStatus.NEW, OrderStatus.IN_PROGRESS]))
                              if due_at is not None else false())
        return stmt

    def page(self, *, limit, offset, sort="updated_desc", **filters):
        stmt = self.selection(**filters)
        sort_expression = {
            "updated_desc": Order.updated_at.desc(), "created_desc": Order.created_at.desc(),
            "amount_desc": Order.total_amount.desc(), "amount_asc": Order.total_amount.asc(),
            "status": case((Order.status == OrderStatus.NEW, 0), (Order.status == OrderStatus.IN_PROGRESS, 1),
                           (Order.status == OrderStatus.COMPLETED_UNPAID, 2), (Order.status == OrderStatus.COMPLETED_PAID, 3), else_=4),
        }.get(sort, Order.updated_at.desc())
        return list(self.db.execute(stmt.order_by(sort_expression, Order.id).limit(limit).offset(offset)).scalars().all())

    def totals(self, **filters):
        rows = self.selection(**filters).subquery()
        active = rows.c.status != OrderStatus.CANCELLED
        def count_if(condition):
            return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)
        result = self.db.execute(select(
            func.count().label("count"),
            count_if(rows.c.status == OrderStatus.NEW).label("new_count"),
            count_if(rows.c.status == OrderStatus.IN_PROGRESS).label("in_progress_count"),
            count_if(rows.c.status.in_([OrderStatus.COMPLETED_UNPAID, OrderStatus.COMPLETED_PAID])).label("completed_count"),
            count_if(and_(active, rows.c.remaining_amount > 0)).label("unpaid_count"),
            func.coalesce(func.sum(case((active, rows.c.total_amount), else_=0)), 0).label("order_amount"),
            func.coalesce(func.sum(rows.c.paid_amount), 0).label("paid_amount"),
            func.coalesce(func.sum(case((active, rows.c.remaining_amount), else_=0)), 0).label("outstanding_amount"),
            func.coalesce(func.sum(case((~active, rows.c.paid_amount), else_=0)), 0).label("cancelled_paid_amount"),
        )).mappings().one()
        return {key: (Decimal(value).quantize(Decimal("0.01")) if key.endswith("amount") else int(value)) for key, value in result.items()}
