"""Inbound ports for the table_discovery_policy_attachment group."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.attach_table_discovery_policy import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCase,
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.detach_table_discovery_policy import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCase,
    DetachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.list_table_discovery_policy_attachments import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsUseCase,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.sync_discovery_schedules import (  # noqa: E501
    SyncDiscoverySchedulesUseCase,
    SyncDiscoverySchedulesUseCaseInput,
    SyncDiscoverySchedulesUseCaseOutput,
)

__all__ = [
    "AttachTableDiscoveryPolicyUseCase",
    "AttachTableDiscoveryPolicyUseCaseInput",
    "AttachTableDiscoveryPolicyUseCaseOutput",
    "DetachTableDiscoveryPolicyUseCase",
    "DetachTableDiscoveryPolicyUseCaseInput",
    "DetachTableDiscoveryPolicyUseCaseOutput",
    "ListTableDiscoveryPolicyAttachmentsUseCase",
    "ListTableDiscoveryPolicyAttachmentsUseCaseInput",
    "ListTableDiscoveryPolicyAttachmentsUseCaseOutput",
    "SyncDiscoverySchedulesUseCase",
    "SyncDiscoverySchedulesUseCaseInput",
    "SyncDiscoverySchedulesUseCaseOutput",
]
