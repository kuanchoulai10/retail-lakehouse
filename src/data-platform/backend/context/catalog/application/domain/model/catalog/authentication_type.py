"""Define the AuthenticationType enumeration."""

from __future__ import annotations

from enum import StrEnum


class AuthenticationType(StrEnum):
    """Name how the catalog service authenticates to a remote catalog service."""

    OAUTH = "OAUTH"
    BEARER = "BEARER"
    SIGV4 = "SIGV4"
    IMPLICIT = "IMPLICIT"
