"""Validation of the prefix of a prefixed id."""

from __future__ import annotations

import re

_PREFIX = re.compile(r"[a-z]{2,8}")


def checked_prefix(prefix: str) -> str:
    """Return ``prefix`` when it is 2 to 8 lowercase ASCII letters, else raise ``ValueError``."""
    if not _PREFIX.fullmatch(prefix):
        raise ValueError(f"prefix must be 2 to 8 lowercase letters, got {prefix!r}")
    return prefix
