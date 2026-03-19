class ServiceError(Exception):
    """Base class for service-layer errors."""


class NotFoundError(ServiceError):
    """Raised when an object cannot be found."""


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found."""

    def __init__(self, message: str = "User was not found.") -> None:
        super().__init__(message)


class InvalidCredentialsError(ServiceError):
    """Raised when login credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid username or password.",
    ) -> None:
        super().__init__(message)
