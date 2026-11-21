"""Define the ListScannedCatalogsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    scanned_catalogs,
)
from context.table_maintenance.application.port.inbound.catalog_discovery import (
    ListScannedCatalogsUseCase,
    ListScannedCatalogsUseCaseInput,
    ListScannedCatalogsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
        CatalogDiscovery,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class ListScannedCatalogsService(ListScannedCatalogsUseCase):
    """List the catalogs a managing discovery policy is attached in, with each one's scan state."""

    def __init__(
        self,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        policies_repo: TableDiscoveryPoliciesRepo,
        discoveries_repo: CatalogDiscoveriesRepo,
    ) -> None:
        """Bind the attachments, the policies and the catalog discoveries."""
        self._attachments_repo = attachments_repo
        self._policies_repo = policies_repo
        self._discoveries_repo = discoveries_repo

    def execute(self, request: ListScannedCatalogsUseCaseInput) -> ListScannedCatalogsUseCaseOutput:  # noqa: ARG002
        """Return each scanned catalog by name, with its last completed scan and its current failure.

        A catalog not yet scanned has neither. A catalog's record outlives its scanning: a catalog
        no managing policy is attached in any more is not listed, whatever it recorded.
        """
        attachments = self._attachments_repo.list_all()
        policy_ids = list({a.policy_id for a in attachments})
        policies = {p.id: p for p in self._policies_repo.get_many(policy_ids)}
        discoveries = {d.catalog: d for d in self._discoveries_repo.list_all()}
        return ListScannedCatalogsUseCaseOutput(
            catalogs=tuple(
                _scanned_catalog(catalog, discoveries.get(catalog))
                for catalog in scanned_catalogs(attachments, policies)
            )
        )


def _scanned_catalog(
    catalog: str, discovery: CatalogDiscovery | None
) -> ListScannedCatalogsUseCaseOutput.ScannedCatalog:
    if discovery is None:
        return ListScannedCatalogsUseCaseOutput.ScannedCatalog(catalog=catalog, last_discovered_at=None, failure=None)
    failure = discovery.current_failure
    return ListScannedCatalogsUseCaseOutput.ScannedCatalog(
        catalog=catalog,
        last_discovered_at=discovery.last_discovered_at,
        failure=None
        if failure is None
        else ListScannedCatalogsUseCaseOutput.Failure(
            reason=failure.reason.value, detail=failure.detail, failed_at=failure.failed_at
        ),
    )
