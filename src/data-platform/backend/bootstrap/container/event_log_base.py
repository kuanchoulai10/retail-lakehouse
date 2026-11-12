"""Provide the event_log_base function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings

S3A_PREFIX = "s3a://"


def event_log_base(settings: AppSettings) -> str:
    """Return the Spark event log directory as ``bucket/prefix``, without its scheme and trailing slash."""
    return settings.spark.event_log_dir.removeprefix(S3A_PREFIX).rstrip("/")
