"""Define the RewriteManifestsSettings value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)


class RewriteManifestsSettings(ValueObject):
    """Configure rewriting of small manifest files.

    ``small_manifest_bytes`` of None falls back to the table property
    ``commit.manifest.target-size-bytes``, else 8 MiB.
    """

    enabled: bool = True
    min_interval: PositiveDuration = Field(
        default=timedelta(hours=6),
        validation_alias="min_interval_seconds",
        serialization_alias="min_interval_seconds",
    )
    min_small_manifests: PositiveInt = 5
    small_manifest_bytes: PositiveInt | None = None
