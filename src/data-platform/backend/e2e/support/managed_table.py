"""Provide ManagedTable, a scenario's own Iceberg table that the platform discovers and maintains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pyiceberg.exceptions import NoSuchNamespaceError

from e2e.support.drop_table import drop_table
from e2e.support.namespace_prefix import namespace_prefix
from e2e.support.remove_prefix import remove_prefix
from e2e.support.wait_until import wait_until
from e2e.support.wait_until_unmanaged import wait_until_unmanaged

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
INCLUDE_E2E_TABLES = {"action": "include", "table_name_pattern": "tm_e2e_*"}


@dataclass(frozen=True)
class ManagedTable:
    """A table in a namespace of its own, with its maintenance policy and a discovery policy that manages it.

    ``create`` makes each piece and pushes its undo on the scenario's cleanup stack. The undo runs in
    the order that keeps the platform from touching a half-removed table: detach and delete the
    discovery policy, wait until the table is unmanaged and its reconciliation stopped, detach and
    delete the maintenance policy, drop the table and remove its storage, remove the namespace's storage (S3 leaves a
    directory marker for it), drop the namespace. The namespace's storage is its own ``location``, refused when it is
    not the namespace's directory (``namespace_prefix``), since it is removed recursively.
    """

    catalog: str
    namespace: str
    name: str
    maintenance_policy: str
    discovery_policy: dict[str, Any]

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
        """Create the namespace, the table and both policies, and attach them, in that order.

        The maintenance policy is attached to the table and the discovery policy to the namespace; each
        undo detaches by that place.
        """
        iceberg.create_namespace(namespace)
        cleanup.push(f"drop namespace {namespace}", lambda: _drop_namespace(iceberg, namespace))
        prefix = namespace_prefix(iceberg.load_namespace_properties(namespace)["location"], namespace)
        cleanup.push(f"remove s3://{prefix}/", lambda: remove_prefix(s3, prefix))
        iceberg.create_table((namespace, name), schema=schema, partition_spec=partition_spec)
        cleanup.push(f"drop table {namespace}.{name}", lambda: drop_table(iceberg, s3, (namespace, name)))

        policy_name, description, change = policy
        platform.create_maintenance_policy(policy_name, description, change)
        cleanup.push(
            f"delete {policy_name}", lambda: platform.call("DELETE", f"/v1/maintenance-policies/{policy_name}")
        )
        on_table = {"type": "table", "path": [catalog, namespace, name]}
        platform.attach("maintenance", policy_name, on_table)
        cleanup.push(f"detach {policy_name}", lambda: platform.detach("maintenance", policy_name, on_table))

        cleanup.push(
            f"wait until {namespace}.{name} is unmanaged",
            lambda: wait_until_unmanaged(platform, temporal, (catalog, namespace, name)),
        )
        discovery = platform.call(
            "POST",
            "/v1/discovery-policies",
            {
                "name": discovery_policy,
                "description": f"e2e: manage the tm_e2e_* tables of {namespace}",
                "rules": [INCLUDE_E2E_TABLES],
            },
        )
        cleanup.push(
            f"delete {discovery_policy}", lambda: platform.call("DELETE", f"/v1/discovery-policies/{discovery_policy}")
        )
        assert discovery["rules"] == [INCLUDE_E2E_TABLES], f"{discovery_policy} holds {discovery['rules']}"
        on_namespace = {"type": "namespace", "path": [catalog, namespace]}
        platform.attach("discovery", discovery_policy, on_namespace)
        cleanup.push(f"detach {discovery_policy}", lambda: platform.detach("discovery", discovery_policy, on_namespace))
        return cls(
            catalog=catalog,
            namespace=namespace,
            name=name,
            maintenance_policy=policy_name,
            discovery_policy=discovery,
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


def _drop_namespace(iceberg: Catalog, namespace: str) -> None:
    try:
        iceberg.drop_namespace(namespace)
    except NoSuchNamespaceError:
        return
