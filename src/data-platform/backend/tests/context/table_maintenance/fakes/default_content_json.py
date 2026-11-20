"""Define the DEFAULT_CONTENT_JSON constant."""

from __future__ import annotations

from typing import Any

DEFAULT_CONTENT_JSON: dict[str, Any] = {
    "description": "Platform default",
    "on": {"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": 300}},
    "dry_run": False,
    "rewrite_data_files": {
        "target": {"reducible_files": {"at_most": 5}, "per": "partition"},
        "options": {"min_input_files": 2, "partial_progress_enabled": True},
    },
    "rewrite_manifests": {"target": {"small_manifests": {"at_most": 5}}, "options": None},
    "expire_snapshots": {"target": {"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400}, "options": None},
    "remove_orphan_files": {"target": {"older_than_seconds": 259200}, "options": None},
}
"""The content of the platform default policy on the wire, as the plan documents it."""
