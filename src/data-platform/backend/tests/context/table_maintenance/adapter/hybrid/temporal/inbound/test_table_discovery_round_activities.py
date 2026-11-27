"""Test the TableDiscoveryRoundActivities."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableDiscoveryRoundActivities,
)
from context.table_maintenance.application.port.inbound.catalog_discovery import (
    ListScannedCatalogsUseCase,
    ListScannedCatalogsUseCaseInput,
    ListScannedCatalogsUseCaseOutput,
)


class _FakeListScanned(ListScannedCatalogsUseCase):
    """Return two scanned catalogs, one scanned before and one never scanned."""

    def __init__(self) -> None:
        self.requests: list[ListScannedCatalogsUseCaseInput] = []

    def execute(self, request: ListScannedCatalogsUseCaseInput) -> ListScannedCatalogsUseCaseOutput:
        self.requests.append(request)
        scanned = ListScannedCatalogsUseCaseOutput.ScannedCatalog
        return ListScannedCatalogsUseCaseOutput(
            catalogs=(
                scanned(catalog="iceberg", last_discovered_at=datetime(2026, 11, 27, tzinfo=UTC), failure=None),
                scanned(catalog="lake", last_discovered_at=None, failure=None),
            )
        )


def test_list_scanned_catalogs_returns_the_catalog_names_in_order():
    """The activity lists the scanned catalogs once and returns only their names, in the use case's order."""
    use_case = _FakeListScanned()

    names = TableDiscoveryRoundActivities(list_scanned=use_case).list_scanned_catalogs()

    assert names == ["iceberg", "lake"]
    assert use_case.requests == [ListScannedCatalogsUseCaseInput()]
