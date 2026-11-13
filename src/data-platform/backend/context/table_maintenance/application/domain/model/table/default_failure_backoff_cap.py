"""Define the default cap of a failing operation's cooldown backoff."""

from __future__ import annotations

from datetime import timedelta

DEFAULT_FAILURE_BACKOFF_CAP = timedelta(hours=24)
