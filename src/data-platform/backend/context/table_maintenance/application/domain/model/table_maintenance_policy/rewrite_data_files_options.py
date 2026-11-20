"""Define the RewriteDataFilesOptions value object."""

from __future__ import annotations

from pydantic import Field, PositiveInt, model_validator

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

    @model_validator(mode="after")
    def _dependent_options_have_their_switch(self) -> RewriteDataFilesOptions:
        """Refuse a sort order without the sort strategy and max commits without partial progress."""
        if self.sort_order is not None and self.strategy is not RewriteDataFilesStrategy.SORT:
            raise ValueError("sort_order needs strategy sort")
        if self.partial_progress_max_commits is not None and self.partial_progress_enabled is not True:
            raise ValueError("partial_progress_max_commits needs partial_progress_enabled true")
        return self

    def procedure_arguments(self) -> dict[str, str]:
        """Return the named procedure arguments that are set."""
        arguments: dict[str, str] = {}
        if self.strategy is not None:
            arguments["strategy"] = str(self.strategy)
        if self.sort_order is not None:
            arguments["sort_order"] = self.sort_order
        return arguments

    def procedure_options(self) -> dict[str, int | bool]:
        """Return the entries of the procedure's options map that are set, in Iceberg's spelling."""
        spelled: dict[str, int | bool | None] = {
            "min-input-files": self.min_input_files,
            "partial-progress.enabled": self.partial_progress_enabled,
            "partial-progress.max-commits": self.partial_progress_max_commits,
            "max-concurrent-file-group-rewrites": self.max_concurrent_file_group_rewrites,
            "rewrite-all": self.rewrite_all,
            "delete-file-threshold": self.delete_file_threshold,
            "remove-dangling-deletes": self.remove_dangling_deletes,
            "max-file-group-size-bytes": self.max_file_group_size_bytes,
        }
        return {key: value for key, value in spelled.items() if value is not None}
