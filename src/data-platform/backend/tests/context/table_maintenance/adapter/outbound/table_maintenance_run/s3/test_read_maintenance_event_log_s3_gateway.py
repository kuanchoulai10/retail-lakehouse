"""Test the gateway that reads whether a maintenance attempt's Spark event log finished."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from pyarrow.fs import LocalFileSystem

from context.table_maintenance.adapter.outbound.table_maintenance_run.s3 import (
    ReadMaintenanceEventLogS3Gateway,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceEventLogGatewayInput,
)

if TYPE_CHECKING:
    from pathlib import Path

APP_ID = "spark-0123abcd"


def _log_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "spark-event-logs" / f"eventlog_v2_{APP_ID}"
    directory.mkdir(parents=True)
    (directory / f"events_1_{APP_ID}.zstd").write_bytes(b"x")
    return directory


def _read(tmp_path: Path, execution_id: str = APP_ID) -> bool | None:
    gateway = ReadMaintenanceEventLogS3Gateway(LocalFileSystem, f"{tmp_path}/spark-event-logs")
    return gateway.read(ReadMaintenanceEventLogGatewayInput(execution_id=execution_id)).finished


def test_finished_marker_reads_true(tmp_path: Path):
    """The renamed status marker means the event log finished."""
    (_log_dir(tmp_path) / f"appstatus_{APP_ID}").write_bytes(b"")
    assert _read(tmp_path) is True


def test_in_progress_marker_reads_false(tmp_path: Path):
    """A status marker still in progress means the event log was left open."""
    (_log_dir(tmp_path) / f"appstatus_{APP_ID}.inprogress").write_bytes(b"")
    assert _read(tmp_path) is False


def test_no_marker_reads_none(tmp_path: Path):
    """No status marker, or no log directory, reads as unknown."""
    assert _read(tmp_path) is None
    _log_dir(tmp_path)
    assert _read(tmp_path) is None


def test_odd_execution_id_reads_none():
    """An execution id with characters outside letters, digits and dashes reads as unknown without a lookup."""
    filesystem = MagicMock(name="filesystem")
    gateway = ReadMaintenanceEventLogS3Gateway(lambda: filesystem, "spark-event-logs")
    for odd in ("../etc", "a/b", "", "spark 1"):
        assert gateway.read(ReadMaintenanceEventLogGatewayInput(execution_id=odd)).finished is None
    assert filesystem.mock_calls == []


def test_file_system_is_opened_on_first_read_and_once(tmp_path: Path):
    """The file system is opened only when an event log is first read, then reused."""
    opened: list[LocalFileSystem] = []

    def open_filesystem() -> LocalFileSystem:
        opened.append(LocalFileSystem())
        return opened[-1]

    gateway = ReadMaintenanceEventLogS3Gateway(open_filesystem, f"{tmp_path}/spark-event-logs")
    assert opened == []
    for _ in range(2):
        gateway.read(ReadMaintenanceEventLogGatewayInput(execution_id=APP_ID))
    assert len(opened) == 1
