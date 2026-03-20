from __future__ import annotations

from app.core.exceptions import AppError


PERMISSION_MATRIX: dict[str, dict[str, set[str]]] = {
    "owner": {
        "*": {"*"},
    },
    "admin": {
        "clients": {"*"},
        "vehicles": {"*"},
        "work_orders": {"*"},
        "employees": {"create", "read", "update", "delete"},
    },
    "manager": {
        "clients": {"read", "update"},
        "vehicles": {"read", "update"},
        "work_orders": {"create", "read", "update"},
        "employees": {"read"},
    },
    "employee": {
        "clients": {"read"},
        "vehicles": {"read"},
        "work_orders": {"create", "read", "update"},
        "employees": {"read"},
    },
}


def check_permission(role: str, resource: str, action: str) -> None:
    """Validate role permission against resource/action matrix."""
    normalized_role = (role or "").strip().lower()
    normalized_resource = (resource or "").strip().lower()
    normalized_action = (action or "").strip().lower()

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
