"""Define the ReplaceTableDiscoveryRulesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    ReplaceTableDiscoveryRulesUseCase,
    ReplaceTableDiscoveryRulesUseCaseInput,
    ReplaceTableDiscoveryRulesUseCaseOutput,
    ReplaceTableDiscoveryRulesUseCaseOutputItem,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_rules.table_discovery_rule_from_request import (
    table_discovery_rule_from_request,
)
from context.table_maintenance.application.service.table_discovery_rules.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from context.table_maintenance.application.port.outbound.table import (
        SendDiscoveryRequestGateway,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_rules import (
        TableDiscoveryRulesRepo,
    )


class ReplaceTableDiscoveryRulesService(ReplaceTableDiscoveryRulesUseCase):
    """Replace the whole discovery rule list, then discover tables in every covered catalog."""

    def __init__(  # noqa: PLR0913
        self,
        rules_repo: TableDiscoveryRulesRepo,
        discovery_request_gateway: SendDiscoveryRequestGateway,
        catalog_names: Sequence[str],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repo, the discovery gateway, the covered catalogs, the clock and the id generator."""
        self._rules_repo = rules_repo
        self._discovery_request_gateway = discovery_request_gateway
        self._catalog_names = tuple(catalog_names)
        self._clock = clock
        self._new_id = new_id

    def execute(self, request: ReplaceTableDiscoveryRulesUseCaseInput) -> ReplaceTableDiscoveryRulesUseCaseOutput:
        """Save the list when ``version`` is the current one, then start one discovery run per covered catalog.

        A rule without an id gets a new one. An invalid list (equal priorities, an
        unknown action, an empty glob list) raises ValidationError and a stale
        version ConflictError; either way nothing is saved and nothing discovered.
        The discovery runs are started after the save commits and not waited for.
        """
        now = self._clock()
        rules = self._rules_repo.get_rules()
        with translate_domain_errors():
            candidates = [
                table_discovery_rule_from_request(item, item.id or self._new_id(), now) for item in request.rules
            ]
            rules.replace(candidates, request.version, now)
            self._rules_repo.save(rules)
        for catalog in self._catalog_names:
            self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(catalog, None))
        return ReplaceTableDiscoveryRulesUseCaseOutput(
            version=rules.version,
            rules=[
                ReplaceTableDiscoveryRulesUseCaseOutputItem(**table_discovery_rule_output_fields(r))
                for r in rules.rules
            ],
        )
