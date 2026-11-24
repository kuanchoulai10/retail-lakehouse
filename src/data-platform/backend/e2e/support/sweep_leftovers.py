"""Provide sweep_leftovers, which removes what an earlier run that was cut short left on the platform."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyarrow import fs

from e2e.support.drop_catalog import drop_catalog
from e2e.support.drop_table import drop_table
from e2e.support.namespace_prefix import namespace_prefix
from e2e.support.owned_names import OwnedNames
from e2e.support.queue_holder import HOLDER_SELECTOR, PODGROUPS
from e2e.support.remove_prefix import remove_prefix
from e2e.support.wait_until_unmanaged import wait_until_unmanaged

if TYPE_CHECKING:
    import re

    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support.kubernetes_api import KubernetesApi
    from e2e.support.platform_api import PlatformApi
    from e2e.support.polaris_client import PolarisClient
    from e2e.support.temporal_session import TemporalSession


def sweep_leftovers(
    *,
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.FileSystem,
    polaris: PolarisClient,
    temporal: TemporalSession[Client],
    kubernetes: KubernetesApi,
    catalog: str,
) -> list[str]:
    """Remove everything named by ``OwnedNames``, in the order a scenario's own cleanup uses, and say what went.

    Queue holders go first, since one blocks every maintenance run of its queue. Discovery policies
    go next, with the default's attachments in e2e catalogs, and each leftover table (of an e2e
    namespace or an e2e catalog) is waited on until it is unmanaged, so the platform
    plans nothing on a table being removed; then the maintenance policies and the default's
    attachments in e2e catalogs, the tables, the namespaces with their storage, the e2e catalogs and
    any catalog storage left without one. Only one e2e run uses a cluster at a time (``run.sh``
    refuses a second), so nothing swept is in use.
    """
    removed: list[str] = []
    for holder in kubernetes.list(PODGROUPS, label_selector=HOLDER_SELECTOR)["items"]:
        name = holder["metadata"]["name"]
        if OwnedNames.QUEUE_HOLDER.match(name):
            kubernetes.delete(f"{PODGROUPS}/{name}")
            removed.append(f"queue holder {name}")
    for policy in _owned_policies(platform, "discovery-policies", OwnedNames.DISCOVERY_POLICY):
        _detach_and_delete(platform, "discovery-policies", policy)
        removed.append(f"discovery policy {policy}")
    removed += _detach_from_default(platform, "discovery")
    namespaces = [
        found[0] for found in iceberg.list_namespaces() if len(found) == 1 and OwnedNames.NAMESPACE.match(found[0])
    ]
    tables = {namespace: [tuple(t) for t in iceberg.list_tables(namespace)] for namespace in namespaces}
    for namespace, identifiers in tables.items():
        for _, table in identifiers:
            wait_until_unmanaged(platform, temporal, (catalog, namespace, table))
    catalogs = [found["name"] for found in platform.get("/v1/catalogs") if OwnedNames.CATALOG.match(found["name"])]
    for found in platform.get("/v1/tables"):
        if found["catalog"] in catalogs:
            wait_until_unmanaged(platform, temporal, (found["catalog"], found["namespace"], found["table"]))
    for policy in _owned_policies(platform, "maintenance-policies", OwnedNames.MAINTENANCE_POLICY):
        _detach_and_delete(platform, "maintenance-policies", policy)
        removed.append(f"maintenance policy {policy}")
    removed += _detach_from_default(platform, "maintenance")
    for namespace, identifiers in tables.items():
        prefix = namespace_prefix(iceberg.load_namespace_properties(namespace)["location"], namespace)
        for _, table in identifiers:
            drop_table(iceberg, s3, (namespace, table))
        remove_prefix(s3, prefix)
        iceberg.drop_namespace(namespace)
        removed.append(f"namespace {namespace}")
    for name in catalogs:
        drop_catalog(polaris, name)
        remove_prefix(s3, f"{OwnedNames.CATALOGS_BUCKET}/{name}")
        removed.append(f"catalog {name}")
    selector = fs.FileSelector(OwnedNames.CATALOGS_BUCKET, allow_not_found=True)
    for left in s3.get_file_info(selector):
        if OwnedNames.CATALOG.match(left.base_name):
            remove_prefix(s3, left.path)
            removed.append(f"storage s3://{left.path}/")
    return removed


def _owned_policies(platform: PlatformApi, kind: str, pattern: re.Pattern[str]) -> list[str]:
    names = [policy["name"] for policy in platform.get(f"/v1/{kind}")["policies"]]
    return [name for name in names if pattern.match(name)]


def _detach_from_default(platform: PlatformApi, kind: str) -> list[str]:
    """Detach the default policy of ``kind`` from every target in an e2e catalog; the default itself stays."""
    gone: list[str] = []
    for attachment in platform.get(f"/v1/{kind}-policies/default/attachments")["attachments"]:
        path = attachment["target"]["path"]
        if OwnedNames.CATALOG.match(path[0]):
            platform.call("DELETE", f"/v1/{kind}-policies/default/attachments/{attachment['id']}")
            gone.append(f"default {kind} policy's attachment {attachment['id']} on {'.'.join(path)}")
    return gone


def _detach_and_delete(platform: PlatformApi, kind: str, policy: str) -> None:
    for attachment in platform.get(f"/v1/{kind}/{policy}/attachments")["attachments"]:
        platform.call("DELETE", f"/v1/{kind}/{policy}/attachments/{attachment['id']}")
    platform.call("DELETE", f"/v1/{kind}/{policy}")
