from __future__ import annotations

from fastapi import Depends

from app.core.exceptions import AppError
from app.core.permissions import check_permission
from app.core.request_context import ExternalAuthContext, get_external_auth_context
from app.services.api_key_service import ApiKeyService


class RequireExternalScope:
    """Scope guard for external API routes (API key scopes or JWT RBAC)."""

    RBAC_RESOURCE_MAP = {
        "clients": "clients",
        "orders": "work_orders",
    }

    RBAC_ACTION_MAP = {
        "read": "read",
        "write": "create",
    }

    def __init__(self, resource: str, action: str):
        self.resource = resource.strip().lower()
        self.action = action.strip().lower()

    def __call__(self, context: ExternalAuthContext = Depends(get_external_auth_context)) -> ExternalAuthContext:
        if context.auth_type == "api_key":
            required_scope = f"{self.resource}:{self.action}"
            if not ApiKeyService.has_scope(scopes=context.scopes, required_scope=required_scope):
                raise AppError(
                    status_code=403,
                    code="api_key_scope_denied",
                    message="API key scope denied",
                    details={"required_scope": required_scope},
                )
            return context

        mapped_resource = self.RBAC_RESOURCE_MAP.get(self.resource, self.resource)
        mapped_action = self.RBAC_ACTION_MAP.get(self.action, self.action)
        if not context.role:
            raise AppError(status_code=403, code="permission_denied", message="Permission denied")
        check_permission(role=context.role, resource=mapped_resource, action=mapped_action)
        return context
