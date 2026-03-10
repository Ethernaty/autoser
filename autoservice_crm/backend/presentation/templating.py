from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from presentation.middleware import CSRF_COOKIE_NAME
from presentation.rbac import can, normalize_role


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def has_perm(current_user, resource: str, action: str) -> bool:  # noqa: ANN001
    if current_user is None:
        return False
    role = getattr(current_user, "role", None)
    return can(role=role, resource=resource, action=action)


def has_role(current_user, *roles: str) -> bool:  # noqa: ANN001
    if current_user is None:
        return False
    role = normalize_role(getattr(current_user, "role", None))
    allowed = {normalize_role(item) for item in roles}
    return role in allowed


def csrf_token(request) -> str:  # noqa: ANN001
    state_token = getattr(getattr(request, "state", None), "csrf_token", None)
    if isinstance(state_token, str) and state_token:
        return state_token
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    return str(cookie_token) if cookie_token else ""


def csrf_input(request) -> Markup:  # noqa: ANN001
    token = escape(csrf_token(request))
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')


templates.env.globals.update(
    has_perm=has_perm,
    has_role=has_role,
    csrf_token=csrf_token,
    csrf_input=csrf_input,
)
