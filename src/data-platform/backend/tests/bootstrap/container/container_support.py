"""Share the SQLite engine and fake gateways for the composition tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bootstrap.configs import ApiSettings, EventConsumerSettings, WorkerSettings
from bootstrap.container import Gateways, build_engine, build_platform_settings
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from tests.context.table_maintenance.fakes.fake_read_maintenance_job_gateway import (
    FakeReadMaintenanceJobGateway,
)
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.recording_delete_maintenance_job_gateway import (
    RecordingDeleteMaintenanceJobGateway,
)
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_send_maintenance_result_gateway import (
    RecordingSendMaintenanceResultGateway,
)
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)
from tests.context.table_maintenance.fakes.recording_submit_maintenance_job_gateway import (
    RecordingSubmitMaintenanceJobGateway,
)
from tests.context.table_maintenance.fakes.recording_sync_discovery_schedules_gateway import (
    RecordingSyncDiscoverySchedulesGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_processes_gateway import (
    ScriptedReadMaintenanceJobProcessesGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_table_metric_history_gateway import (
    ScriptedReadTableMetricHistoryGateway,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.domain.model.shared import PlatformSettings

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


IN_MEMORY_SQLITE: dict[str, Any] = {"backend": "sqlite", "sqlite": {"path": ":memory:"}}


def sqlite_settings(**overrides: Any) -> WorkerSettings:  # noqa: ANN401
    """Return worker settings that use an in-memory SQLite database."""
    return WorkerSettings.model_validate({"database": IN_MEMORY_SQLITE, **overrides})


def sqlite_api_settings(**overrides: Any) -> ApiSettings:  # noqa: ANN401
    """Return API settings that use an in-memory SQLite database."""
    return ApiSettings.model_validate({"database": IN_MEMORY_SQLITE, **overrides})


def sqlite_event_consumer_settings(**overrides: Any) -> EventConsumerSettings:  # noqa: ANN401
    """Return event consumer settings that use an in-memory SQLite database."""
    return EventConsumerSettings.model_validate({"database": IN_MEMORY_SQLITE, **overrides})


def sqlite_engine() -> Engine:
    """Return an in-memory SQLite engine with the control-plane schema."""
    engine = build_engine(sqlite_settings().database)
    create_schema(engine)
    return engine


def fake_gateways() -> Gateways:
    """Return a Gateways bundle made only of in-process fakes."""
    return Gateways(
        read_table_metadata=FakeReadTableMetadataGateway(),
        send_table_change=RecordingSendTableChangeGateway(),
        send_discovery_request=RecordingSendDiscoveryRequestGateway(),
        sync_discovery_schedules=RecordingSyncDiscoverySchedulesGateway(),
        send_maintenance_result=RecordingSendMaintenanceResultGateway(),
        submit_maintenance_job=RecordingSubmitMaintenanceJobGateway(),
        read_maintenance_job=FakeReadMaintenanceJobGateway(),
        delete_maintenance_job=RecordingDeleteMaintenanceJobGateway(),
        read_maintenance_job_processes=ScriptedReadMaintenanceJobProcessesGateway(),
        read_maintenance_job_evidence=ScriptedReadMaintenanceJobEvidenceGateway(),
        read_maintenance_event_log=ScriptedReadMaintenanceEventLogGateway(),
        read_table_metric_history=ScriptedReadTableMetricHistoryGateway(),
    )


def platform_settings() -> PlatformSettings:
    """Return the platform settings a composition test hands to ``build_use_cases``."""
    return build_platform_settings(sqlite_settings())
