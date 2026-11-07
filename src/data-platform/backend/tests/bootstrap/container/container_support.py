"""Share the SQLite engine and fake gateways for the composition tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from bootstrap.configs import AppSettings, DatabaseBackend, SqliteSettings
from bootstrap.container import Gateways, build_engine
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.fake_read_maintenance_job_gateway import (
    FakeReadMaintenanceJobGateway,
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
from tests.context.table_maintenance.fakes.recording_update_table_discovery_schedule_gateway import (
    RecordingUpdateTableDiscoveryScheduleGateway,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def sqlite_settings(**overrides: Any) -> AppSettings:  # noqa: ANN401
    """Return settings that use an in-memory SQLite database."""
    values: dict[str, Any] = {
        "database_backend": DatabaseBackend.SQLITE,
        "sqlite": SqliteSettings(path=":memory:"),
        **overrides,
    }
    return AppSettings.model_validate(values)


def sqlite_engine() -> Engine:
    """Return an in-memory SQLite engine with the control-plane schema."""
    engine = build_engine(sqlite_settings())
    create_schema(engine)
    return engine


def fake_gateways() -> Gateways:
    """Return a Gateways bundle made only of in-process fakes."""
    return Gateways(
        read_table_metadata=FakeReadTableMetadataGateway(),
        send_table_change=RecordingSendTableChangeGateway(),
        send_discovery_request=RecordingSendDiscoveryRequestGateway(),
        send_maintenance_result=RecordingSendMaintenanceResultGateway(),
        update_table_discovery_schedule=RecordingUpdateTableDiscoveryScheduleGateway(),
        submit_maintenance_job=RecordingSubmitMaintenanceJobGateway(),
        read_maintenance_job=FakeReadMaintenanceJobGateway(),
        delete_maintenance_job=RecordingDeleteMaintenanceJobGateway(),
    )
