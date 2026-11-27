"""Provide OwnedCatalog, a catalog a scenario creates through the platform and drops when it ends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyarrow import fs

from e2e.support.drop_catalog import CONTENT_GRANTS, drop_catalog
from e2e.support.owned_names import OwnedNames
from e2e.support.remove_prefix import remove_prefix

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyiceberg.catalog import Catalog

    from e2e.support.cleanup_stack import CleanupStack
    from e2e.support.platform_api import PlatformApi
    from e2e.support.polaris_client import PolarisClient

_STORAGE_KEYS = ("storage_type", "endpoint", "sts_endpoint", "path_style_access")
E2E_ROLE = "tm_e2e"
_EXISTS = 409


@dataclass(frozen=True)
class OwnedCatalog:
    """A catalog of the scenario's own, so its schedule, scans and defaults are the scenario's alone.

    Its storage is ``s3://<CATALOGS_BUCKET>/<name>``, beside the platform's. Its undo drops it
    (``drop_catalog`` grants back what ``revoke_reads`` took first), then removes that prefix.
    """

    name: str
    iceberg: Catalog

    @classmethod
    def create(
        cls,
        *,
        platform: PlatformApi,
        polaris: PolarisClient,
        s3: fs.FileSystem,
        cleanup: CleanupStack,
        platform_catalog: str,
        name: str,
        load_iceberg: Callable[[str], Catalog],
    ) -> OwnedCatalog:
        """Create catalog ``name`` with the platform catalog's storage settings, and push its undo."""
        stored = platform.get(f"/v1/catalogs/{platform_catalog}")["storage_config"]
        base = f"s3://{OwnedNames.CATALOGS_BUCKET}/{name}"
        if s3.get_file_info(OwnedNames.CATALOGS_BUCKET).type == fs.FileType.NotFound:
            s3.create_dir(OwnedNames.CATALOGS_BUCKET)
        prefix = f"{OwnedNames.CATALOGS_BUCKET}/{name}"
        cleanup.push(f"remove s3://{prefix}/", lambda: remove_prefix(s3, prefix))
        cleanup.push(f"drop catalog {name}", lambda: drop_catalog(polaris, name))
        storage = {key: stored[key] for key in _STORAGE_KEYS} | {"allowed_locations": [base]}
        platform.call(
            "POST",
            "/v1/catalogs",
            {"name": name, "type": "INTERNAL", "default_base_location": base, "storage_config": storage},
        )
        return cls(name=name, iceberg=load_iceberg(name))

    def revoke_reads(self, polaris: PolarisClient) -> None:
        """Take the content grants from ``catalog_admin``, so the platform can no longer read the catalog."""
        self._change_reads(polaris, "POST", "revoking")

    def restore_reads(self, polaris: PolarisClient) -> None:
        """Give ``catalog_admin`` the content grants back, so the platform can read the catalog again."""
        self._change_reads(polaris, "PUT", "granting")

    def keep_e2e_writes(self, polaris: PolarisClient) -> None:
        """Give the e2e principal content grants of its own here, so ``revoke_reads`` blinds only the platform.

        Both principals reach a catalog created through the API by ``catalog_admin`` (through
        ``service_admin``). Catalog role ``tm_e2e`` gets ``CATALOG_MANAGE_CONTENT`` and goes to principal
        role ``tm_e2e``, which only the e2e principal holds (``e2e.setup_principal``); one already there
        is kept. ``drop_catalog`` removes the role with the catalog.
        """
        roles = f"/catalogs/{self.name}/catalog-roles"
        content = {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}
        steps = (
            ("POST", roles, {"catalogRole": {"name": E2E_ROLE}}),
            ("PUT", f"{roles}/{E2E_ROLE}/grants", content),
            ("PUT", f"/principal-roles/{E2E_ROLE}/catalog-roles/{self.name}", {"catalogRole": {"name": E2E_ROLE}}),
        )
        for method, path, body in steps:
            reply = polaris.management(method, path, body)
            if method == "POST" and reply.status_code == _EXISTS:
                continue
            assert reply.is_success, f"{method} {path} answered {reply.status_code}: {reply.text}"

    def _change_reads(self, polaris: PolarisClient, method: str, doing: str) -> None:
        for privilege in CONTENT_GRANTS:
            reply = polaris.management(
                method,
                f"/catalogs/{self.name}/catalog-roles/catalog_admin/grants",
                {"grant": {"type": "catalog", "privilege": privilege}},
            )
            assert reply.is_success, f"{doing} {privilege} on {self.name} answered {reply.status_code}: {reply.text}"
