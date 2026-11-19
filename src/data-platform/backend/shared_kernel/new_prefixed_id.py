"""Mint a new prefixed id from the clock and the system random source."""

from __future__ import annotations

import uuid

from shared_kernel._checked_prefix import checked_prefix
from shared_kernel._crockford import encode_128_bits


def new_prefixed_id(prefix: str) -> str:
    """Return ``<prefix>-<26 characters>`` for a fresh UUIDv7 (``uuid.uuid7()``)."""
    return f"{checked_prefix(prefix)}-{encode_128_bits(uuid.uuid7().int)}"
