"""Define the table_observation_from_gateway function."""

from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.observation.manifest_stats import ManifestStats
from application.domain.model.observation.partition_field_info import (
    PartitionFieldInfo,
)
from application.domain.model.observation.partition_spec_info import (
    PartitionSpecInfo,
)
from application.domain.model.observation.partition_stats import PartitionStats
from application.domain.model.observation.snapshot_info import SnapshotInfo
from application.domain.model.observation.table_observation import TableObservation
from application.port.outbound.table.read_table_metadata import (
    TableMetadataObservation,
)


def _utc(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def table_observation_from_gateway(
    observation: TableMetadataObservation,
) -> TableObservation:
    """Convert the gateway's primitive observation into the domain observation.

    ``committed_at`` is parsed to an aware UTC datetime. Raise ``ValueError`` when
    an item is missing a key or carries a malformed value.
    """
    try:
        return TableObservation(
            table_uuid=observation.table_uuid,
            properties=dict(observation.properties),
            current_snapshot_id=observation.current_snapshot_id,
            specs=tuple(
                PartitionSpecInfo(
                    spec_id=spec["spec_id"],
                    fields=tuple(
                        PartitionFieldInfo(
                            field_id=f["field_id"],
                            name=f["name"],
                            source_column=f["source_column"],
                            source_type=f["source_type"],
                            transform=f["transform"],
                        )
                        for f in spec["fields"]
                    ),
                )
                for spec in observation.specs
            ),
            partitions=tuple(
                PartitionStats(
                    spec_id=p["spec_id"],
                    values=tuple(p["values"]),
                    data_file_count=p["data_file_count"],
                    position_delete_file_count=p["position_delete_file_count"],
                    equality_delete_file_count=p["equality_delete_file_count"],
                    total_data_file_size_bytes=p["total_data_file_size_bytes"],
                )
                for p in observation.partitions
            ),
            manifests=tuple(
                ManifestStats(length_bytes=m["length_bytes"])
                for m in observation.manifests
            ),
            snapshots=tuple(
                SnapshotInfo(
                    snapshot_id=s["snapshot_id"], committed_at=_utc(s["committed_at"])
                )
                for s in observation.snapshots
            ),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"malformed table observation: {exc!r}") from exc
