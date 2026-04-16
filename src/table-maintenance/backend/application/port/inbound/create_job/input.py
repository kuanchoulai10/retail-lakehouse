from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateJobInput:
    """Input for the CreateJob use case."""

    job_type: str
    catalog: str

    expire_snapshots: dict | None = None
    remove_orphan_files: dict | None = None
    rewrite_data_files: dict | None = None
    rewrite_manifests: dict | None = None

    cron: str | None = None
    enabled: bool = False
