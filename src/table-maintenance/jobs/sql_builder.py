from __future__ import annotations

from typing import TYPE_CHECKING

from configs.base import JobType

if TYPE_CHECKING:
    from configs import JobSettings


def _ts(dt) -> str:
    return f"TIMESTAMP '{dt.strftime('%Y-%m-%d %H:%M:%S.%f')}'"


def _map_expr(opts: dict[str, str]) -> str:
    pairs = ", ".join(f"'{k}', '{v}'" for k, v in opts.items())
    return f"map({pairs})"


class IcebergCallBuilder:
    def __init__(self, settings: JobSettings):
        self._settings = settings

    def build_sql(self) -> str:
        settings = self._settings
        catalog = settings.catalog

        if settings.job_type == JobType.EXPIRE_SNAPSHOTS:
            return self._expire_snapshots(catalog)
        if settings.job_type == JobType.REMOVE_ORPHAN_FILES:
            return self._remove_orphan_files(catalog)
        if settings.job_type == JobType.REWRITE_DATA_FILES:
            return self._rewrite_data_files(catalog)
        if settings.job_type == JobType.REWRITE_MANIFESTS:
            return self._rewrite_manifests(catalog)

        raise ValueError(f"Unhandled job_type: {settings.job_type}")

    def _expire_snapshots(self, catalog: str) -> str:
        s = self._settings.expire_snapshots
        args = [f"table => '{s.table}'"]
        if s.older_than is not None:
            args.append(f"older_than => {_ts(s.older_than)}")
        args.append(f"retain_last => {s.retain_last}")
        if s.max_concurrent_deletes is not None:
            args.append(f"max_concurrent_deletes => {s.max_concurrent_deletes}")
        if s.stream_results:
            args.append("stream_results => true")
        return f"CALL {catalog}.system.expire_snapshots({', '.join(args)})"

    def _remove_orphan_files(self, catalog: str) -> str:
        s = self._settings.remove_orphan_files
        args = [f"table => '{s.table}'"]
        if s.older_than is not None:
            args.append(f"older_than => {_ts(s.older_than)}")
        if s.location is not None:
            args.append(f"location => '{s.location}'")
        if s.dry_run:
            args.append("dry_run => true")
        if s.max_concurrent_deletes is not None:
            args.append(f"max_concurrent_deletes => {s.max_concurrent_deletes}")
        return f"CALL {catalog}.system.remove_orphan_files({', '.join(args)})"

    def _rewrite_data_files(self, catalog: str) -> str:
        s = self._settings.rewrite_data_files
        args = [f"table => '{s.table}'"]
        args.append(f"strategy => '{s.strategy.value}'")
        if s.sort_order is not None:
            args.append(f"sort_order => '{s.sort_order}'")
        opts: dict[str, str] = {}
        if s.target_file_size_bytes is not None:
            opts["target-file-size-bytes"] = str(s.target_file_size_bytes)
        if s.min_file_size_bytes is not None:
            opts["min-file-size-bytes"] = str(s.min_file_size_bytes)
        if s.max_file_size_bytes is not None:
            opts["max-file-size-bytes"] = str(s.max_file_size_bytes)
        if s.min_input_files is not None:
            opts["min-input-files"] = str(s.min_input_files)
        if s.rewrite_all is not None:
            opts["rewrite-all"] = str(s.rewrite_all).lower()
        if s.max_concurrent_file_group_rewrites is not None:
            opts["max-concurrent-file-group-rewrites"] = str(s.max_concurrent_file_group_rewrites)
        if s.partial_progress_enabled is not None:
            opts["partial-progress.enabled"] = str(s.partial_progress_enabled).lower()
        if s.partial_progress_max_commits is not None:
            opts["partial-progress.max-commits"] = str(s.partial_progress_max_commits)
        if opts:
            args.append(f"options => {_map_expr(opts)}")
        if s.where is not None:
            args.append(f"where => '{s.where}'")
        return f"CALL {catalog}.system.rewrite_data_files({', '.join(args)})"

    def _rewrite_manifests(self, catalog: str) -> str:
        s = self._settings.rewrite_manifests
        args = [f"table => '{s.table}'"]
        args.append(f"use_caching => {'true' if s.use_caching else 'false'}")
        if s.spec_id is not None:
            args.append(f"spec_id => {s.spec_id}")
        return f"CALL {catalog}.system.rewrite_manifests({', '.join(args)})"
