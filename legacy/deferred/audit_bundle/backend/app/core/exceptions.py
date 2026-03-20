from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class AuthError(AppError):
    def __init__(self, *, code: str, message: str, status_code: int = 401, details: dict[str, Any] | None = None):
        super().__init__(status_code=status_code, code=code, message=message, details=details or {})


class ValidationAppError(AppError):
    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(status_code=422, code=code, message=message, details=details or {})


class DatabaseAppError(AppError):
    def __init__(self, *, code: str, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        super().__init__(status_code=status_code, code=code, message=message, details=details or {})


class TenantScopeError(AppError):
    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None, status_code: int = 403):
        super().__init__(status_code=status_code, code=code, message=message, details=details or {})


class CrossTenantDataViolation(AppError):
    def __init__(self, *, code: str = "cross_tenant_data_violation", message: str = "Cross-tenant data violation detected", details: dict[str, Any] | None = None):
        super().__init__(status_code=403, code=code, message=message, details=details or {})


class SecurityPolicyError(AppError):
    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None, status_code: int = 400):
        super().__init__(status_code=status_code, code=code, message=message, details=details or {})
