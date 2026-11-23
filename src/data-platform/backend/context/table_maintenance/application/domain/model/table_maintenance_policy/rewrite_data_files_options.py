"""Define the RewriteDataFilesOptions value object."""

from __future__ import annotations

from typing import Any

from pydantic import Field, PositiveInt, SerializerFunctionWrapHandler, model_serializer, model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_strategy import (
    RewriteDataFilesStrategy,
)


class RewriteDataFilesOptions(ValueObject):
    """A curated subset of Iceberg's ``rewrite_data_files`` arguments; an unset one is left to the procedure.

    The where clause and the target file size belong to the target and the platform, so they are no options.
    """

    strategy: RewriteDataFilesStrategy | None = None
    sort_order: str | None = Field(default=None, min_length=1, max_length=1000)
    min_input_files: PositiveInt | None = None
    partial_progress_enabled: bool | None = None
    partial_progress_max_commits: PositiveInt | None = None
    max_concurrent_file_group_rewrites: PositiveInt | None = None
    rewrite_all: bool | None = None
    delete_file_threshold: PositiveInt | None = None
    remove_dangling_deletes: bool | None = None
    max_file_group_size_bytes: PositiveInt | None = None

    @model_serializer(mode="wrap")
    def _leave_unset_out(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Write only the options that are set, so an unset one stays left to the procedure."""
        return {key: value for key, value in handler(self).items() if value is not None}

    @model_validator(mode="after")
    def _dependent_options_have_their_switch(self) -> RewriteDataFilesOptions:
        """Refuse a sort order without the sort strategy and max commits without partial progress."""
        if self.sort_order is not None and self.strategy is not RewriteDataFilesStrategy.SORT:
            raise ValueError("sort_order needs strategy sort")
        if self.partial_progress_max_commits is not None and self.partial_progress_enabled is not True:
            raise ValueError("partial_progress_max_commits needs partial_progress_enabled true")
        return self
