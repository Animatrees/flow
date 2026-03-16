class ServiceError(Exception):
    """Base class for service-layer errors."""


class NotFoundError(ServiceError):
    """Raised when an object cannot be found."""
