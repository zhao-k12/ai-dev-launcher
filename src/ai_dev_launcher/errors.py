"""Application-specific errors."""


class LauncherError(Exception):
    """Base class for expected, user-facing errors."""


class ConfigurationError(LauncherError):
    """Raised when configuration cannot be loaded or validated."""


class ProjectAlreadyExistsError(LauncherError):
    """Raised when a project name is already registered."""


class ProjectNotFoundError(LauncherError):
    """Raised when a registered project cannot be found."""


class PreparationError(LauncherError):
    """Raised when project preparation cannot complete safely."""


class LaunchError(LauncherError):
    """Raised when a development environment cannot be launched."""
