"""Define the ReadMaintenanceEventLogS3Gateway."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pyarrow.fs import FileType

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceEventLogGateway,
    ReadMaintenanceEventLogGatewayOutput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyarrow.fs import FileSystem

    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceEventLogGatewayInput,
    )

EXECUTION_ID = re.compile(r"[A-Za-z0-9-]+")
IN_PROGRESS_SUFFIX = ".inprogress"


class ReadMaintenanceEventLogS3Gateway(ReadMaintenanceEventLogGateway):
    """Read the status marker of a Spark application's rolling event log in the object store.

    Spark writes ``<base>/eventlog_v2_<id>/appstatus_<id>.inprogress`` while the application
    runs and renames it to ``appstatus_<id>`` when its context stops cleanly. Our runtime stops
    the context before it reports its result, and a job polled as failed has a driver that has
    exited, so when a result is recorded the marker is final. Only the marker is read, never
    the log itself. The file system is opened on the first read, so a component that never
    reads an event log never opens one.
    """

    def __init__(self, open_filesystem: Callable[[], FileSystem], base: str) -> None:
        """Keep the file system opener and the event log directory (``bucket/prefix``, no scheme)."""
        self._open_filesystem = open_filesystem
        self._filesystem: FileSystem | None = None
        self._base = base.rstrip("/")

    def read(
        self,
        input: ReadMaintenanceEventLogGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceEventLogGatewayOutput:
        """Return True for a finished marker, False for one in progress, None when neither exists.

        An execution id that is not letters, digits and dashes is never looked up. A storage
        error propagates.
        """
        execution_id = input.execution_id
        if not EXECUTION_ID.fullmatch(execution_id):
            return ReadMaintenanceEventLogGatewayOutput(finished=None)
        marker = f"{self._base}/eventlog_v2_{execution_id}/appstatus_{execution_id}"
        if self._filesystem is None:
            self._filesystem = self._open_filesystem()
        finished, in_progress = self._filesystem.get_file_info([marker, marker + IN_PROGRESS_SUFFIX])
        if finished.type == FileType.File:
            return ReadMaintenanceEventLogGatewayOutput(finished=True)
        if in_progress.type == FileType.File:
            return ReadMaintenanceEventLogGatewayOutput(finished=False)
        return ReadMaintenanceEventLogGatewayOutput(finished=None)
