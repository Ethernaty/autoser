from __future__ import annotations

from app.core.exceptions import AppError


PERMISSION_MATRIX: dict[str, dict[str, set[str]]] = {
    "owner": {
        "*": {"*"},
    },
    "admin": {
        "clients": {"*"},
        "vehicles": {"*"},
        "orders": {"*"},
        "payments": {"*"},
        "employees": {"create", "read", "update", "delete"},
        "workspace_settings": {"read", "manage"},
        "audit": {"read"},
    },
    "manager": {
        "clients": {"create", "read", "update"},
        "vehicles": {"create", "read", "update"},
        "orders": {"create", "read", "update", "change_status", "assign", "close"},
        "payments": {"create", "read"},
        "employees": {"read"},
        "workspace_settings": {"read"},
        "audit": {"read"},
    },
    "employee": {
        "clients": {"read"},
        "vehicles": {"read"},
        "orders": {"create", "read", "update", "change_status"},
        "payments": {"create", "read"},
        "employees": {"read"},
        "workspace_settings": {"read"},
    },
}

RESOURCE_ALIASES: dict[str, str] = {
    "work_orders": "orders",
    "work-order": "orders",
    "work_order": "orders",
    "workspace.settings": "workspace_settings",
}

ACTION_ALIASES: dict[str, str] = {
    "edit": "update",
}


def check_permission(role: str, resource: str, action: str) -> None:
    """Validate role permission against resource/action matrix."""
    normalized_role = (role or "").strip().lower()
    raw_resource = (resource or "").strip().lower()
    raw_action = (action or "").strip().lower()
    normalized_resource = RESOURCE_ALIASES.get(raw_resource, raw_resource)
    normalized_action = ACTION_ALIASES.get(raw_action, raw_action)

    role_permissions = PERMISSION_MATRIX.get(normalized_role)
    if role_permissions is None:
        raise AppError(status_code=403, code="permission_denied", message="Permission denied")

    if normalized_role == "owner":
        return

    if "*" in role_permissions and "*" in role_permissions["*"]:
        return

    resource_actions = role_permissions.get(normalized_resource) or role_permissions.get("*")
    if not resource_actions:
        raise AppError(status_code=403, code="permission_denied", message="Permission denied")

    if "*" in resource_actions or normalized_action in resource_actions:
        return

    raise AppError(status_code=403, code="permission_denied", message="Permission denied")
