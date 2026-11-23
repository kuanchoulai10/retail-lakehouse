"""Define the ProcessTableHintService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableManagementChange,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.port.inbound.table import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
    ProcessTableHintUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
    TableMetadataRef,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.apply_discovery_to_known_table import (
    apply_discovery_to_known_table,
)
from context.table_maintenance.application.service.table.discovery_decider import DiscoveryDecider
from context.table_maintenance.application.service.table.last_commit_of import last_commit_of
from context.table_maintenance.application.service.table.register_discovered_table import (
    register_discovered_table,
)
from context.table_maintenance.application.service.table.table_hint_action import (
    TableHintAction,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        DiscoveryDecision,
    )
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendDiscoveryRequestGateway,
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class ProcessTableHintService(ProcessTableHintUseCase):
    """React to a catalog event naming a namespace or one table."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        discovery_policies_repo: TableDiscoveryPoliciesRepo,
        discovery_attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        discovery_request_gateway: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._discovery_policies_repo = discovery_policies_repo
        self._discovery_attachments_repo = discovery_attachments_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._discovery_request_gateway = discovery_request_gateway
        self._clock = clock

    def execute(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        """Handle the hint; ``event_type`` does not change the behaviour.

        A hint naming one table applies the same steps as a discovery pass to that
        table: an unknown one is registered (managed or unmanaged), a known one is
        renamed and decided again, by its nearest discovery policy, read from the attachments
        on that one table's walk. A table in a catalog nothing manages is registered as the
        default decides, unmanaged, and sent nothing. A table that ends up newly managed is
        signalled ``managed``, and one already managed ``updated``.
        Either way the table's newest commit is read from the catalog, so a
        commit event moves its last commit.
        """
        if request.table is None:
            return self._request_discovery(request)
        found = self._catalog_gateway.load_table(TableMetadataRef(request.catalog, request.namespace, request.table))
        if found is None:
            return self._handle_missing(request)
        with translate_domain_errors():
            action = self._handle_found(found)
        return ProcessTableHintUseCaseOutput(action=action.value)

    def _request_discovery(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(request.catalog, request.namespace))
        return ProcessTableHintUseCaseOutput(action=TableHintAction.DISCOVERY_REQUESTED.value)

    def _handle_missing(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        name = TableName(catalog=request.catalog, namespace=request.namespace, table=request.table or "")
        if self._tables_repo.find_by_name(name) is None:
            return ProcessTableHintUseCaseOutput(action=TableHintAction.IGNORED.value)
        self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(request.catalog, None))
        return ProcessTableHintUseCaseOutput(action=TableHintAction.DISCOVERY_REQUESTED.value)

    def _handle_found(self, found: TableMetadata) -> TableHintAction:
        now = self._clock()
        table = self._tables_repo.get(TableId(found.table_uuid))
        if table is not None and table.status == TableStatus.DROPPED:
            return TableHintAction.IGNORED
        name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
        decision = DiscoveryDecider.for_table(
            name, found.table_uuid, self._discovery_attachments_repo, self._discovery_policies_repo
        ).decide(name, found.table_uuid)
        if table is None:
            return self._register(found, name, decision, now)
        outcome = apply_discovery_to_known_table(
            table,
            name,
            decision,
            self._tables_repo,
            self._table_change_gateway,
            TableChange.UPDATED,
            now,
            last_committed_at=last_commit_of(found),
        )
        if outcome.change == TableManagementChange.MANAGED:
            return TableHintAction.MANAGED
        if outcome.change == TableManagementChange.UNMANAGED:
            return TableHintAction.UNMANAGED
        if outcome.renamed:
            return TableHintAction.RENAMED
        return TableHintAction.SIGNALLED if outcome.signalled else TableHintAction.IGNORED

    def _register(
        self, found: TableMetadata, name: TableName, decision: DiscoveryDecision, now: datetime
    ) -> TableHintAction:
        stale = self._tables_repo.find_by_name(name)
        register_discovered_table(found, decision, self._tables_repo, self._table_change_gateway, now)
        if stale is not None:
            self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(found.catalog, None))
        return TableHintAction.REGISTERED
