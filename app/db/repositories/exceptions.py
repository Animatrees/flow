from app.services.exceptions import (
    ConflictError as ServiceConflictError,
)
from app.services.exceptions import (
    EmailAlreadyExistsError as ServiceEmailAlreadyExistsError,
)
from app.services.exceptions import (
    ProjectNotFoundError as ServiceProjectNotFoundError,
)
from app.services.exceptions import (
    RepositoryError as ServiceRepositoryError,
)
from app.services.exceptions import (
    UsernameAlreadyExistsError as ServiceUsernameAlreadyExistsError,
)
from app.services.exceptions import (
    UserNotFoundError as ServiceUserNotFoundError,
)


class RepositoryError(ServiceRepositoryError):
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


class UserNotFoundError(ServiceUserNotFoundError, RepositoryError):
    """Raised when a referenced user does not exist."""

    def __init__(self, message: str = "User was not found.") -> None:
        super().__init__(message)


class ProjectNotFoundError(ServiceProjectNotFoundError, RepositoryError):
    """Raised when a referenced project does not exist."""

    def __init__(self, message: str = "Project was not found.") -> None:
        super().__init__(message)
