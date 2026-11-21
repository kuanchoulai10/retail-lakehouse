"""Define the checked_policy_name function."""

from __future__ import annotations

import re

from shared_kernel import any_prefixed_id_pattern

_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_PREFIXED_ID = any_prefixed_id_pattern()


def checked_policy_name(value: str) -> str:
    """Return ``value`` when it is a valid policy name, else raise ``ValueError``.

    A policy name is 1 to 64 letters, digits, ``_`` or ``-``, and never shaped like a prefixed id
    (``mp-…`` or any other prefix, ADR 0011), so a name in a URL or a record can never be mistaken
    for an id. Every kind of policy name checks its value with this one rule.
    """
    if _PATTERN.fullmatch(value) is None:
        raise ValueError("policy name must be 1 to 64 letters, digits, underscores or hyphens")
    if _PREFIXED_ID.fullmatch(value) is not None:
        raise ValueError(
            "policy name must not look like a prefixed id (<prefix>-<26 base32 characters>); choose another name"
        )
    return value
