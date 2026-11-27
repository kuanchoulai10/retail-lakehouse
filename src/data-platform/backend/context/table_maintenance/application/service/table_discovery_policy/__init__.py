"""Services for the table_discovery_policy group."""

from __future__ import annotations

from context.table_maintenance.application.service.table_discovery_policy.create_table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy.delete_table_discovery_policy import (
    DeleteTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy.discovery_rule_fields import (
    discovery_rule_fields,
)
from context.table_maintenance.application.service.table_discovery_policy.discovery_rules_of import (
    discovery_rules_of,
)
from context.table_maintenance.application.service.table_discovery_policy.get_table_discovery_policy import (
    GetTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy.get_table_discovery_policy_version import (  # noqa: E501
    GetTableDiscoveryPolicyVersionService,
)
from context.table_maintenance.application.service.table_discovery_policy.list_table_discovery_policies import (
    ListTableDiscoveryPoliciesService,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)
from context.table_maintenance.application.service.table_discovery_policy.update_table_discovery_policy import (
    UpdateTableDiscoveryPolicyService,
)

__all__ = [
    "CreateTableDiscoveryPolicyService",
    "DeleteTableDiscoveryPolicyService",
    "GetTableDiscoveryPolicyService",
    "GetTableDiscoveryPolicyVersionService",
    "ListTableDiscoveryPoliciesService",
    "UpdateTableDiscoveryPolicyService",
    "discovery_rule_fields",
    "discovery_rules_of",
    "table_discovery_policy_output_fields",
]
