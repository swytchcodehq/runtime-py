"""Errors raised by the Swytchcode runtime."""

from typing import Any


class SwytchcodeError(Exception):
    """Raised when exec() fails: spawn error, non-zero exit, or invalid JSON output."""

    def __init__(self, message: str, cause: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause is not None:
            return f"{self.message}: {self.cause}"
        return self.message


def is_swytchcode_error(exc: BaseException) -> bool:
    """Return True if exc is a SwytchcodeError."""
    return isinstance(exc, SwytchcodeError)
