#!/usr/bin/env python3
"""Error handling module for QGit.

This module provides a centralized error handling system with custom exceptions
for different types of Git operations and QGit functionality.
"""

from typing import Any, Optional


class QGitError(Exception):
    """Base exception class for all QGit errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class GitOperationError(QGitError):
    """Base class for Git operation errors."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        error_output: Optional[str] = None,
    ):
        self.command = command
        self.error_output = error_output
        details = {"command": command, "error_output": error_output}
        super().__init__(message, details)


class GitCommandError(GitOperationError):
    """Error raised when a Git command fails."""

    def __init__(self, command: str, error_message: str):
        super().__init__(
            message=f"Git command failed: {command}\nError: {error_message}",
            command=command,
            error_output=error_message,
        )


class GitConfigError(GitOperationError):
    """Error raised when there are Git configuration issues."""

    pass


class GitRepositoryError(GitOperationError):
    """Error raised when there are repository-related issues."""

    pass


class GitStateError(GitOperationError):
    """Error raised when the repository is in an invalid state."""

    pass


class GitNetworkError(GitOperationError):
    """Error raised when there are network-related issues with Git operations."""

    pass


class FileOperationError(QGitError):
    """Error raised when file operations fail."""

    def __init__(
        self,
        message: str,
        filepath: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        self.filepath = filepath
        self.operation = operation
        details = {"filepath": filepath, "operation": operation}
        super().__init__(message, details)


class ConfigurationError(QGitError):
    """Error raised when there are QGit configuration issues."""

    pass


class ValidationError(QGitError):
    """Error raised when input validation fails."""

    pass


class ResourceError(QGitError):
    """Error raised when there are resource-related issues."""

    pass


def format_error(error: Exception) -> str:
    """Format an error for display to the user.

    Args:
        error: The exception to format

    Returns:
        A formatted error message string
    """
    if isinstance(error, GitOperationError):
        message = f"❌ {error.message}"
        if error.command:
            message += f"\n📎 Command: {error.command}"
        if error.error_output:
            message += f"\n💡 Details: {error.error_output}"
        return message

    elif isinstance(error, FileOperationError):
        message = f"❌ {error.message}"
        if error.filepath:
            message += f"\n📄 File: {error.filepath}"
        if error.operation:
            message += f"\n🔧 Operation: {error.operation}"
        return message

    elif isinstance(error, QGitError):
        message = f"❌ {error.message}"
        if error.details:
            message += f"\n💡 Details: {error.details}"
        return message

    return f"❌ {str(error)}"
