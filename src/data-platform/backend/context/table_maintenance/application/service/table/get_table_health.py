"""Define the GetTableHealthService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.domain.service.table import (
    assess_maintenance,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableHealthUseCase,
    GetTableHealthUseCaseInput,
    GetTableHealthUseCaseOutput,
    GetTableHealthUseCaseOutputItem,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.load_catalog_table import (
    load_catalog_table,
)
from context.table_maintenance.application.service.table.raise_not_in_catalog import (
    raise_not_in_catalog,
)
from context.table_maintenance.application.service.table.table_observation_from_gateway import (
    table_observation_from_gateway,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.shared import (
        OperationAssessment,
    )
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TablesRepo,
    )

_NOT_SCHEDULED_REASONS = {
    TableStatus.DROPPED: "dropped",
    TableStatus.EXCLUDED: "excluded",
    TableStatus.PAUSED: "paused",
}


def _to_item(assessment: OperationAssessment) -> GetTableHealthUseCaseOutputItem:
    return GetTableHealthUseCaseOutputItem(
        operation=assessment.operation.value,
        verdict=assessment.verdict.value,
        measured=assessment.measured,
        threshold=assessment.threshold,
        next_eligible_at=assessment.next_eligible_at,
        qualifying_partitions=assessment.qualifying_partitions,
        size_bytes=assessment.size_bytes,
        size_source=(None if assessment.size_source is None else assessment.size_source.value),
    )


class GetTableHealthService(GetTableHealthUseCase):
    """Report the scheduler's own evaluation of a table, operation by operation."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the catalog gateway and the clock."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._clock = clock

    def execute(self, request: GetTableHealthUseCaseInput) -> GetTableHealthUseCaseOutput:
        """Assess every operation, or raise NotFoundError."""
        table, ref = load_catalog_table(self._tables_repo, request.uuid)
        gateway_observation = self._catalog_gateway.observe_table(ref)
        with translate_domain_errors():
            observation = None if gateway_observation is None else table_observation_from_gateway(gateway_observation)
        if observation is None or observation.table_uuid != table.id.value:
            raise_not_in_catalog(table)
        reason = _NOT_SCHEDULED_REASONS.get(table.status)
        settings = table.settings
        if reason is None and settings is None:
            reason = "no_settings"
        items = (
            []
            if settings is None
            else [_to_item(a) for a in assess_maintenance(table, settings, observation, self._clock()).operations]
        )
        return GetTableHealthUseCaseOutput(
            scheduled=reason is None,
            not_scheduled_reason=reason,
            operations=items,
            position_delete_files=sum(p.position_delete_file_count for p in observation.partitions),
            equality_delete_files=sum(p.equality_delete_file_count for p in observation.partitions),
        )
