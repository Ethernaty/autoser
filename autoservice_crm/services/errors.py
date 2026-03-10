class DomainError(Exception):
    """Base class for domain and business-rule errors."""


class ValidationError(DomainError):
    """Raised when user-provided data is invalid."""


class NotFoundError(DomainError):
    """Raised when requested entity does not exist."""


class BusinessRuleError(DomainError):
    """Raised when operation violates a business rule."""


class ExternalServiceError(DomainError):
    """Raised when external integration is unavailable or invalid."""
