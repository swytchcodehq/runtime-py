"""Errors raised by the Swytchcode runtime."""

from typing import Any


class SwytchcodeError(Exception):
    """Raised when exec() fails: spawn error, non-zero exit, or invalid JSON output."""

    def __init__(
        self,
        message: str,
        cause: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        # Structured detail parsed from the CLI's classified JSON error (stderr),
        # when available: category, retryable, suggested_action, docs_url. None for
        # spawn errors, signals, or CLI versions predating this format.
        self.details = details

    def __str__(self) -> str:
        if self.cause is not None:
            return f"{self.message}: {self.cause}"
        return self.message


def is_swytchcode_error(exc: BaseException) -> bool:
    """Return True if exc is a SwytchcodeError."""
    return isinstance(exc, SwytchcodeError)
