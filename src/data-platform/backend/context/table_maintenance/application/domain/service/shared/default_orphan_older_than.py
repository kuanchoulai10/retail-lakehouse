"""Define the DEFAULT_ORPHAN_OLDER_THAN constant."""

from __future__ import annotations

from datetime import timedelta

DEFAULT_ORPHAN_OLDER_THAN = timedelta(days=3)
"""Iceberg's own ``remove_orphan_files`` age, used when a policy leaves the operation out."""
