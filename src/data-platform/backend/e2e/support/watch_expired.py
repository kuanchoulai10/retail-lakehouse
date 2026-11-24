"""Provide WatchExpired, raised when a Kubernetes watch's resource version is too old to resume from."""

from __future__ import annotations


class WatchExpired(Exception):  # noqa: N818
    """The API server answered 410 Gone on a watch: list again and watch from the new version."""
