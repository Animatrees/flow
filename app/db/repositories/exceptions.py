from app.services.exceptions import (
    ConflictError as ServiceConflictError,
)
from app.services.exceptions import (
    EmailAlreadyExistsError as ServiceEmailAlreadyExistsError,
)
from app.services.exceptions import (
    UsernameAlreadyExistsError as ServiceUsernameAlreadyExistsError,
)


class RepositoryError(Exception):
    """Base class for repository-layer errors."""


class ConflictError(ServiceConflictError, RepositoryError):
    """Raised when a repository operation violates a DB constraint."""


class UsernameAlreadyExistsError(
    ServiceUsernameAlreadyExistsError,
    ConflictError,
):
    """Raised when a username is already in use."""

    def __init__(self, message: str = "Username is already taken.") -> None:
        super().__init__(message)


class EmailAlreadyExistsError(
    ServiceEmailAlreadyExistsError,
    ConflictError,
):
    """Raised when an email is already in use."""

    def __init__(self, message: str = "Email is already taken.") -> None:
        super().__init__(message)
