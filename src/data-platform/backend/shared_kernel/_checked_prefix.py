"""Validation of the prefix of a prefixed id."""

from __future__ import annotations

from shared_kernel._prefix_pattern import PREFIX_PATTERN


def checked_prefix(prefix: str) -> str:
    """Return ``prefix`` when it is 2 to 8 lowercase ASCII letters, else raise ``ValueError``."""
    if not PREFIX_PATTERN.fullmatch(prefix):
        raise ValueError(f"prefix must be 2 to 8 lowercase letters, got {prefix!r}")
    return prefix
