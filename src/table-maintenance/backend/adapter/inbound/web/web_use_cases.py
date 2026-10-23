"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.inbound.discovery.get_discovery_settings import (
        GetDiscoverySettingsUseCase,
    )
    from application.port.inbound.discovery.sync_discovered_tables import (
        SyncDiscoveredTablesUseCase,
    )
    from application.port.inbound.discovery.update_discovery_settings import (
        UpdateDiscoverySettingsUseCase,
    )
    from application.port.inbound.discovery_rule.create_discovery_rule import (
        CreateDiscoveryRuleUseCase,
    )
    from application.port.inbound.discovery_rule.delete_discovery_rule import (
        DeleteDiscoveryRuleUseCase,
    )
    from application.port.inbound.discovery_rule.list_discovery_rules import (
        ListDiscoveryRulesUseCase,
    )
    from application.port.inbound.discovery_rule.update_discovery_rule import (
        UpdateDiscoveryRuleUseCase,
    )
    from application.port.inbound.maintenance_run.get_maintenance_run import (
        GetMaintenanceRunUseCase,
    )
    from application.port.inbound.maintenance_run.list_maintenance_runs import (
        ListMaintenanceRunsUseCase,
    )
    from application.port.inbound.maintenance_run.process_maintenance_callback import (
        ProcessMaintenanceCallbackUseCase,
    )
    from application.port.inbound.managed_table.exclude_managed_table import (
        ExcludeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.get_managed_table import (
        GetManagedTableUseCase,
    )
    from application.port.inbound.managed_table.include_managed_table import (
        IncludeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.list_managed_tables import (
        ListManagedTablesUseCase,
    )
    from application.port.inbound.managed_table.pause_managed_table import (
        PauseManagedTableUseCase,
    )
    from application.port.inbound.managed_table.reset_managed_table_selection import (
        ResetManagedTableSelectionUseCase,
    )
    from application.port.inbound.managed_table.resume_managed_table import (
        ResumeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.trigger_maintenance import (
        TriggerMaintenanceUseCase,
    )
    from application.port.inbound.managed_table.update_managed_table_settings import (
        UpdateManagedTableSettingsUseCase,
    )
    from application.port.inbound.policy_template.create_policy_template import (
        CreatePolicyTemplateUseCase,
    )
    from application.port.inbound.policy_template.delete_policy_template import (
        DeletePolicyTemplateUseCase,
    )
    from application.port.inbound.policy_template.get_policy_template import (
        GetPolicyTemplateUseCase,
    )
    from application.port.inbound.policy_template.list_policy_templates import (
        ListPolicyTemplatesUseCase,
    )
    from application.port.inbound.policy_template.update_policy_template import (
        UpdatePolicyTemplateUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every use case the web API calls; the composition root builds it."""

    create_discovery_rule: CreateDiscoveryRuleUseCase
    list_discovery_rules: ListDiscoveryRulesUseCase
    update_discovery_rule: UpdateDiscoveryRuleUseCase
    delete_discovery_rule: DeleteDiscoveryRuleUseCase
    get_discovery_settings: GetDiscoverySettingsUseCase
    update_discovery_settings: UpdateDiscoverySettingsUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    create_policy_template: CreatePolicyTemplateUseCase
    list_policy_templates: ListPolicyTemplatesUseCase
    get_policy_template: GetPolicyTemplateUseCase
    update_policy_template: UpdatePolicyTemplateUseCase
    delete_policy_template: DeletePolicyTemplateUseCase
    list_managed_tables: ListManagedTablesUseCase
    get_managed_table: GetManagedTableUseCase
    update_managed_table_settings: UpdateManagedTableSettingsUseCase
    pause_managed_table: PauseManagedTableUseCase
    resume_managed_table: ResumeManagedTableUseCase
    reset_managed_table_selection: ResetManagedTableSelectionUseCase
    include_managed_table: IncludeManagedTableUseCase
    exclude_managed_table: ExcludeManagedTableUseCase
    trigger_maintenance: TriggerMaintenanceUseCase
    list_maintenance_runs: ListMaintenanceRunsUseCase
    get_maintenance_run: GetMaintenanceRunUseCase
    process_maintenance_callback: ProcessMaintenanceCallbackUseCase
