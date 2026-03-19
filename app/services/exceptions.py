class ServiceError(Exception):
    """Base class for service-layer errors."""


class ConflictError(ServiceError):
    """Raised when a business operation violates a uniqueness constraint."""


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


class UsernameAlreadyExistsError(ConflictError):
    """Raised when a username is already in use."""

    def __init__(self, message: str = "Username is already taken.") -> None:
        super().__init__(message)


class EmailAlreadyExistsError(ConflictError):
    """Raised when an email is already in use."""

    def __init__(self, message: str = "Email is already taken.") -> None:
        super().__init__(message)
