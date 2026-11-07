"""Define the PermissionDeniedError exception."""

from __future__ import annotations


class PermissionDeniedError(Exception):
    """Signal that the catalog refused the operation for lack of privileges."""
