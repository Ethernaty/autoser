from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDenied(Exception):
    resource: str
    action: str


ROLE_PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "owner": {"*": {"*"}},
    "admin": {
        "clients": {"*"},
        "work_orders": {"*"},
        "employees": {"create", "read", "update", "delete"},
        "admin_panel": {"*"},
    },
    "manager": {
        "clients": {"read", "update"},
        "work_orders": {"create", "read", "update"},
        "employees": {"read"},
    },
    "employee": {
        "clients": {"read"},
        "work_orders": {"create", "read", "update"},
        "employees": {"read"},
    },
}


ADMIN_PANEL_ROLES = {"owner", "admin"}
APP_PANEL_ROLES = {"owner", "admin", "manager", "employee"}


def normalize_role(role: str | None) -> str:
    return (role or "").strip().lower()


def is_known_role(role: str | None) -> bool:
    return normalize_role(role) in ROLE_PERMISSIONS


def can(role: str | None, resource: str, action: str) -> bool:
    normalized_role = normalize_role(role)
    normalized_resource = (resource or "").strip().lower()
    normalized_action = (action or "").strip().lower()

    role_permissions = ROLE_PERMISSIONS.get(normalized_role)
    if not role_permissions:
        return False

    if "*" in role_permissions and "*" in role_permissions["*"]:
        return True

    resource_actions = role_permissions.get(normalized_resource) or role_permissions.get("*")
    if not resource_actions:
        return False

    return "*" in resource_actions or normalized_action in resource_actions


def ensure_permission(role: str | None, resource: str, action: str) -> None:
    if can(role=role, resource=resource, action=action):
        return
    raise PermissionDenied(resource=resource, action=action)


def allowed_roles_for_path(path: str) -> set[str] | None:
    if path.startswith("/admin") and not path.startswith("/admin/auth") and not path.startswith("/admin/static"):
        return ADMIN_PANEL_ROLES
    if path.startswith("/app"):
        return APP_PANEL_ROLES
    return None
