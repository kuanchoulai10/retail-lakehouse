from enum import StrEnum

from pydantic import BaseModel


class Strategy(StrEnum):
    BINPACK = "binpack"
    SORT = "sort"
    ZORDER = "zorder"


class RewriteDataFilesConfig(BaseModel):
    table: str | None = None
    strategy: Strategy = Strategy.BINPACK
    sort_order: str | None = None
    where: str | None = None
    target_file_size_bytes: int | None = None
    min_file_size_bytes: int | None = None
    max_file_size_bytes: int | None = None
    min_input_files: int | None = None
    rewrite_all: bool | None = None
    max_concurrent_file_group_rewrites: int | None = None
    partial_progress_enabled: bool | None = None
    partial_progress_max_commits: int | None = None
