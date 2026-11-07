"""Define the spark_application_name function."""

from __future__ import annotations

_CODES: dict[str, str] = {
    "rewrite_data_files": "rdf",
    "rewrite_manifests": "rm",
    "expire_snapshots": "es",
    "remove_orphan_files": "rof",
}


def spark_application_name(run_id: str, operation: str, attempt: int) -> str:
    """Build a deterministic DNS-1123 label naming one Spark application attempt."""
    if attempt < 1:
        msg = f"attempt must be >= 1, got {attempt}"
        raise ValueError(msg)
    if operation not in _CODES:
        msg = f"unknown maintenance operation {operation!r}"
        raise ValueError(msg)
    short_id = "".join(c for c in run_id.lower() if c.isalnum())[:20]
    return f"tm-{_CODES[operation]}-{short_id}-a{attempt}"
