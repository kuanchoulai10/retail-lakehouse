"""Provide unique_suffix, which keeps one run's names apart from another's."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def unique_suffix(token_hex: Callable[[int], str] = secrets.token_hex) -> str:
    """Return 8 lowercase hex characters, valid in Iceberg, Polaris and Kubernetes names."""
    return token_hex(4)
