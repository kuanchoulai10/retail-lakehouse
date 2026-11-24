"""A table's metric trend follows its current metrics once Prometheus has scraped them.

One dry-run table in a catalog of the module's own: written after it is managed, reconciled, and the
hour's trend read until its newest point holds the new count. Marked ``full``: it waits for discovery,
a reconciliation and a scrape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pytest
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import LongType, NestedField

from e2e.support import ManagedTable, OwnedNames, wait_until

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

SCHEMA = Schema(NestedField(1, "id", LongType(), required=False))
ROWS = pa.schema([pa.field("id", pa.int64())])
WAIT_SECONDS = 180
SCRAPE_SECONDS = 150


def test_the_hours_trend_shows_the_new_count(
    api: httpx.Client,
    platform: PlatformApi,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """After rows are written and the table reconciled, the newest trend point equals the current count."""
    table = ManagedTable.create(
        platform=platform,
        iceberg=owned_catalog.iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=owned_catalog.name,
        namespace=OwnedNames.namespace(suffix, "trends"),
        name="tm_e2e_trends",
        schema=SCHEMA,
        partition_spec=PartitionSpec(),
        policy=(OwnedNames.maintenance_policy(suffix, "trends"), "e2e: dry run", lambda b: {**b, "dry_run": True}),
        discovery_policy=OwnedNames.discovery_policy(suffix, "trends"),
    )
    uuid = table.wait_until_managed(platform)
    owned_catalog.iceberg.load_table(table.identifier).append(
        pa.Table.from_pylist([{"id": n} for n in range(5)], schema=ROWS)
    )
    reply = api.post(f"/v1/tables/{uuid}/reconcile")
    assert reply.status_code == 202, reply.text

    def counted() -> dict[str, Any]:
        current = platform.get(f"/v1/tables/{uuid}/metrics/current")
        if not current["metrics"] or current["metrics"]["data_records"] != 5:
            raise AssertionError(current)
        return current["metrics"]

    wait_until(counted, timeout=WAIT_SECONDS, interval=3, what=f"5 records in the metrics of {uuid}")

    def scraped() -> list[dict[str, Any]]:
        trend = platform.get(f"/v1/tables/{uuid}/metrics", range="1h")
        assert trend["time_range"] == "1h"
        records = [point["values"].get("data_records") for point in trend["points"]]
        if not [value for value in records if value is not None] or [v for v in records if v is not None][-1] != 5:
            raise AssertionError(records)
        return trend["points"]

    points = wait_until(scraped, timeout=SCRAPE_SECONDS, interval=10, what=f"the trend of {uuid} at 5 records")
    moments = [point["at"] for point in points]
    assert moments == sorted(moments)
    records = [point["values"].get("data_records") for point in points]
    first = records.index(5)
    assert all(value is None or value < 5 for value in records[:first]), records
