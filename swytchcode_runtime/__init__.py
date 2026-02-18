"""Thin runtime wrapper around the Swytchcode CLI."""

from .errors import SwytchcodeError, is_swytchcode_error
from .exec import exec_ as exec

__all__ = ["exec", "SwytchcodeError", "is_swytchcode_error"]
