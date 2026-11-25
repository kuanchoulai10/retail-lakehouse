"""Define the UnknownSettingError exception."""

from __future__ import annotations


class UnknownSettingError(ValueError):
    """A setting the role does not take, a settings file that cannot be read, or a secret written in that file."""
