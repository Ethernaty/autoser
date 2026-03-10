from __future__ import annotations

from fastapi import Depends

from app.core.permissions import check_permission
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
        return context
