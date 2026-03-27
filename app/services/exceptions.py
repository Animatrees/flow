class ServiceError(Exception):
    """Base class for service-layer errors."""


class RepositoryError(ServiceError):
    """Base class for repository-related errors."""


class DomainValidationError(ServiceError):
    """Raised when a business operation violates domain validation rules."""


class ConflictError(ServiceError):
    """Raised when a business operation violates a uniqueness constraint."""


class NotFoundError(ServiceError):
    """Raised when an object cannot be found."""


class AccessDeniedError(ServiceError):
    """Raised when the user cannot access a resource or action."""


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found."""

    def __init__(self, message: str = "User was not found.") -> None:
        super().__init__(message)


class ProjectNotFoundError(NotFoundError):
    """Raised when a project cannot be found."""

    def __init__(self, message: str = "Project was not found.") -> None:
        super().__init__(message)


class DocumentNotFoundError(NotFoundError):
    """Raised when a document cannot be found."""

    def __init__(self, message: str = "Document was not found.") -> None:
        super().__init__(message)


class InvalidProjectDatesError(DomainValidationError):
    """Raised when project dates violate domain constraints."""

    def __init__(
        self,
        message: str = "Project end date must be greater than or equal to the start date.",
    ) -> None:
        super().__init__(message)


class DocumentTooLargeError(DomainValidationError):
    """Raised when a document exceeds the configured size limit."""

    def __init__(self, message: str = "Document exceeds the maximum allowed size.") -> None:
        super().__init__(message)


class UnsupportedDocumentTypeError(DomainValidationError):
    """Raised when a document type is not allowed."""

    def __init__(self, message: str = "Document type is not supported.") -> None:
        super().__init__(message)


class InvalidCredentialsError(ServiceError):
    """Raised when login credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid username or password.",
    ) -> None:
        super().__init__(message)


class DocumentStorageError(ServiceError):
    """Raised when a document file operation fails."""

    def __init__(self, message: str = "Document storage operation failed.") -> None:
        super().__init__(message)


class InvalidTokenError(ServiceError):
    """Raised when a token is invalid."""

    def __init__(
        self,
        message: str = "Invalid token",
    ) -> None:
        super().__init__(message)


class PermissionDeniedError(AccessDeniedError):
    """Raised when the user doesn't have sufficient permissions."""

    def __init__(
        self,
        message: str = "You do not have sufficient permissions to perform this action.",
    ) -> None:
        super().__init__(message)


class ProjectAccessDeniedError(AccessDeniedError):
    """Raised when the user doesn't have access to the project."""

    def __init__(
        self,
        message: str = "You do not have access to this project.",
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


class ProjectMemberAlreadyExistsError(ConflictError):
    """Raised when the user already has project access."""

    def __init__(self, message: str = "User is already a member of this project.") -> None:
        super().__init__(message)
