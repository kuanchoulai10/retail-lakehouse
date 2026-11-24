"""Provide ManagedTable, a scenario's own Iceberg table that the platform discovers and maintains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError

from e2e.support.reconciliation_running import reconciliation_running
from e2e.support.remove_prefix import remove_prefix
from e2e.support.wait_until import wait_until

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from pyiceberg.partitioning import PartitionSpec
    from pyiceberg.schema import Schema
    from pyiceberg.table import Table
    from temporalio.client import Client

    from e2e.support.cleanup_stack import CleanupStack
    from e2e.support.platform_api import PlatformApi
    from e2e.support.temporal_session import TemporalSession

DISCOVERY_TIMEOUT_SECONDS = 900
UNMANAGE_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class ManagedTable:
    """A table in a namespace of its own, with its maintenance policy and a discovery policy that manages it.

    ``create`` makes each piece and pushes its undo on the scenario's cleanup stack. The undo runs in
    the order that keeps the platform from touching a half-removed table: detach and delete the
    discovery policy, wait until the table is unmanaged and its reconciliation stopped, detach and
    delete the maintenance policy, drop the table and remove its storage, remove the namespace's storage (S3 leaves a
    directory marker for it), drop the namespace.
    """

    catalog: str
    namespace: str
    name: str
    maintenance_policy: str
    maintenance_attachment_id: str
    discovery_policy: dict[str, Any]
    discovery_attachment_id: str

    @classmethod
    def create(
        cls,
        *,
        platform: PlatformApi,
        iceberg: Catalog,
        s3: fs.S3FileSystem,
        temporal: TemporalSession[Client],
        cleanup: CleanupStack,
        catalog: str,
        namespace: str,
        name: str,
        schema: Schema,
        partition_spec: PartitionSpec,
        policy: tuple[str, str, Callable[[dict], dict]],
        discovery_policy: str,
    ) -> ManagedTable:
        """Create the namespace, the table, both policies and their attachments, in that order."""
        iceberg.create_namespace(namespace)
        cleanup.push(f"drop namespace {namespace}", lambda: _drop_namespace(iceberg, namespace))
        location = iceberg.create_table((namespace, name), schema=schema, partition_spec=partition_spec).location()
        namespace_prefix = location.removeprefix("s3://").rstrip("/").rsplit("/", 1)[0]
        cleanup.push(f"remove s3://{namespace_prefix}/", lambda: remove_prefix(s3, namespace_prefix))
        cleanup.push(f"drop table {namespace}.{name}", lambda: _drop_table(iceberg, s3, (namespace, name)))

        policy_name, description, change = policy
        platform.create_maintenance_policy(policy_name, description, change)
        cleanup.push(
            f"delete {policy_name}", lambda: platform.call("DELETE", f"/v1/maintenance-policies/{policy_name}")
        )
        maintenance_attachment_id = platform.attach(
            "maintenance-policies", policy_name, {"type": "table", "path": [catalog, namespace, name]}
        )
        cleanup.push(
            f"detach {policy_name}",
            lambda: platform.call(
                "DELETE", f"/v1/maintenance-policies/{policy_name}/attachments/{maintenance_attachment_id}"
            ),
        )

        cleanup.push(
            f"wait until {namespace}.{name} is unmanaged",
            lambda: _wait_until_unmanaged(platform, temporal, (catalog, namespace, name)),
        )
        discovery = platform.call(
            "POST",
            "/v1/discovery-policies",
            {
                "name": discovery_policy,
                "description": f"e2e: manage the tm_e2e_* tables of {namespace}",
                "no_match_outcome": "unmanage",
                "rules": [
                    {
                        "outcome": "manage",
                        "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["tm_e2e_*"]}],
                    }
                ],
            },
        )
        cleanup.push(
            f"delete {discovery_policy}", lambda: platform.call("DELETE", f"/v1/discovery-policies/{discovery_policy}")
        )
        discovery_attachment_id = platform.attach(
            "discovery-policies", discovery_policy, {"type": "namespace", "path": [catalog, namespace]}
        )
        cleanup.push(
            f"detach {discovery_policy}",
            lambda: platform.call(
                "DELETE", f"/v1/discovery-policies/{discovery_policy}/attachments/{discovery_attachment_id}"
            ),
        )
        return cls(
            catalog=catalog,
            namespace=namespace,
            name=name,
            maintenance_policy=policy_name,
            maintenance_attachment_id=maintenance_attachment_id,
            discovery_policy=discovery,
            discovery_attachment_id=discovery_attachment_id,
        )

    @property
    def identifier(self) -> tuple[str, str]:
        """The table's identifier in the catalog."""
        return (self.namespace, self.name)

    def load(self, iceberg: Catalog) -> Table:
        """Read the table's current metadata."""
        return iceberg.load_table(self.identifier)

    def file_count(self, iceberg: Catalog) -> int:
        """Count the data and delete files of the current snapshot."""
        return self.load(iceberg).inspect.files().num_rows

    def wait_until_managed(self, platform: PlatformApi) -> str:
        """Wait until discovery manages the table, and return its uuid."""

        def managed() -> str | None:
            found = platform.table(self.catalog, self.namespace, self.name)
            return found["uuid"] if found and found["status"] == "managed" else None

        return wait_until(
            managed,
            timeout=DISCOVERY_TIMEOUT_SECONDS,
            interval=10,
            what=f"discovery of {self.namespace}.{self.name}",
        )


def _wait_until_unmanaged(
    platform: PlatformApi, temporal: TemporalSession[Client], place: tuple[str, str, str]
) -> None:
    def settled() -> bool | None:
        found = platform.table(*place)
        if found is None:
            return True
        if found["status"] == "managed" or reconciliation_running(temporal, found["uuid"]):
            raise AssertionError(f"{found['status']}, reconciliation of {found['uuid']} may still run")
        return True

    wait_until(settled, timeout=UNMANAGE_TIMEOUT_SECONDS, interval=10, what=f"{'.'.join(place)} unmanaged")


def _drop_table(iceberg: Catalog, s3: fs.S3FileSystem, identifier: tuple[str, str]) -> None:
    try:
        location = iceberg.load_table(identifier).location()
    except NoSuchTableError:
        return
    iceberg.drop_table(identifier)
    remove_prefix(s3, location.removeprefix("s3://").rstrip("/"))


def _drop_namespace(iceberg: Catalog, namespace: str) -> None:
    try:
        iceberg.drop_namespace(namespace)
    except NoSuchNamespaceError:
        return
