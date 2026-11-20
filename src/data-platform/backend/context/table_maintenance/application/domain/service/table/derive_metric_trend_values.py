"""Define the derive_metric_trend_values domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

_ENTRY_FIELDS = ("manifest_added_entries", "manifest_existing_entries", "manifest_deleted_entries")


def _average(total: float | None, manifests: float | None) -> float | None:
    if total is None or not manifests:
        return None
    return total / manifests


def derive_metric_trend_values(values: Mapping[str, float | None]) -> dict[str, float | None]:
    """Return the given values plus the average manifest size and the average entries per manifest.

    An average is None when the manifests are zero or missing, or when a total it divides is missing.
    """
    entries = [values.get(field) for field in _ENTRY_FIELDS]
    total_entries = None if any(entry is None for entry in entries) else sum(e for e in entries if e is not None)
    manifests = values.get("manifests")
    return {
        **values,
        "manifest_average_size_bytes": _average(values.get("manifests_size_bytes"), manifests),
        "manifest_average_entries": _average(total_entries, manifests),
    }
