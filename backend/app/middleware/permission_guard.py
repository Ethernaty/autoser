from __future__ import annotations

from fastapi import Depends

from app.core.permissions import check_permission
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.repositories.membership_repository import MembershipRepository
from app.core.request_context import UserRequestContext, get_current_user_context


class RequirePermission:
    """FastAPI dependency guard for RBAC checks."""

    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    def __call__(self, context: UserRequestContext = Depends(get_current_user_context)) -> UserRequestContext:
        check_permission(
            role=context.role,
            resource=self.resource,
            action=self.action,
        )
        if self.resource == "payments" and self.action != "read" and context.role not in {"owner", "admin"}:
            with SessionLocal.begin() as db:
                membership = MembershipRepository(db).get_for_user_and_tenant(
                    user_id=context.user_id, tenant_id=context.tenant_id
                )
                if membership is None or not membership.is_active or not membership.can_accept_payments:
                    raise AppError(status_code=403, code="payment_permission_required", message="Payment access is disabled")
        return context
