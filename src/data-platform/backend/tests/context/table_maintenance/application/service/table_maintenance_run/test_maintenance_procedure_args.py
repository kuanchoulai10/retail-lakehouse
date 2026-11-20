"""Test the Iceberg procedure arguments of each maintenance operation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtMost,
    ExpireSnapshotsOptions,
    ExpireSnapshotsSpec,
    ExpireSnapshotsTarget,
    MaintenancePolicyContent,
    PrefixMismatchMode,
    RemoveOrphanFilesOptions,
    RemoveOrphanFilesSpec,
    RemoveOrphanFilesTarget,
    RewriteDataFilesOptions,
    RewriteDataFilesSpec,
    RewriteDataFilesStrategy,
    RewriteDataFilesTarget,
    RewriteManifestsOptions,
    RewriteManifestsSpec,
    RewriteManifestsTarget,
)
from context.table_maintenance.application.service.table_maintenance_run import maintenance_procedure_args
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

OPS = MaintenanceOperation
RDF = OPS.REWRITE_DATA_FILES
POLICY = MaintenancePolicyContent.platform_default()
NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def _compaction(options: RewriteDataFilesOptions | None) -> MaintenancePolicyContent:
    target = RewriteDataFilesTarget(reducible_files=AtMost(at_most=5))
    return policy_with_operation(POLICY, RDF, RewriteDataFilesSpec(target=target, options=options))


def test_rewrite_args_carry_the_options_map():
    """The platform default compacts to the resolved size with its two options in Iceberg's spelling."""
    args = maintenance_procedure_args(RDF, POLICY, {}, NOW)
    assert args == {
        "options": {"target-file-size-bytes": 536870912, "min-input-files": 2, "partial-progress.enabled": True}
    }


def test_rewrite_args_take_the_table_target_file_size():
    """The target file size is the table's ``write.target-file-size-bytes``."""
    args = maintenance_procedure_args(RDF, POLICY, {"write.target-file-size-bytes": "1000"}, NOW)
    assert args["options"]["target-file-size-bytes"] == 1000


def test_rewrite_args_with_sort_strategy():
    """The strategy and the sort order are top-level arguments, the rest stays in the options map."""
    options = RewriteDataFilesOptions(
        strategy=RewriteDataFilesStrategy.SORT,
        sort_order="id DESC",
        partial_progress_enabled=True,
        partial_progress_max_commits=3,
        rewrite_all=True,
        max_file_group_size_bytes=1024,
    )
    assert maintenance_procedure_args(RDF, _compaction(options), {}, NOW) == {
        "strategy": "sort",
        "sort_order": "id DESC",
        "options": {
            "target-file-size-bytes": 536870912,
            "partial-progress.enabled": True,
            "partial-progress.max-commits": 3,
            "rewrite-all": True,
            "max-file-group-size-bytes": 1024,
        },
    }


def test_rewrite_args_without_options_carry_only_the_size():
    """A block without options leaves every option to the procedure."""
    assert maintenance_procedure_args(RDF, _compaction(None), {}, NOW) == {
        "options": {"target-file-size-bytes": 536870912}
    }


def test_expire_args_use_the_resolved_retention():
    """Snapshot expiry runs with the platform default's age and count."""
    assert maintenance_procedure_args(OPS.EXPIRE_SNAPSHOTS, POLICY, {}, NOW) == {
        "older_than": (NOW - timedelta(days=1)).isoformat(),
        "retain_last": 10,
    }


def test_expire_args_carry_their_options():
    """The set options of snapshot expiry are added beside the retention."""
    spec = ExpireSnapshotsSpec(
        target=ExpireSnapshotsTarget(min_snapshots_to_keep=4),
        options=ExpireSnapshotsOptions(max_concurrent_deletes=8, stream_results=True),
    )
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, spec)
    props = {"history.expire.max-snapshot-age-ms": str(2 * 86400 * 1000)}
    assert maintenance_procedure_args(OPS.EXPIRE_SNAPSHOTS, policy, props, NOW) == {
        "older_than": "2026-10-22T12:00:00+00:00",
        "retain_last": 4,
        "max_concurrent_deletes": 8,
        "stream_results": True,
    }


def test_manifest_args_carry_their_options():
    """A manifest rewrite passes ``use_caching`` only when it is set."""
    assert maintenance_procedure_args(OPS.REWRITE_MANIFESTS, POLICY, {}, NOW) == {}
    spec = RewriteManifestsSpec(
        target=RewriteManifestsTarget(small_manifests=AtMost(at_most=5)),
        options=RewriteManifestsOptions(use_caching=False),
    )
    policy = policy_with_operation(POLICY, OPS.REWRITE_MANIFESTS, spec)
    assert maintenance_procedure_args(OPS.REWRITE_MANIFESTS, policy, {}, NOW) == {"use_caching": False}


def test_orphan_args_carry_prefix_mismatch_mode():
    """Orphan removal passes its age and its set options."""
    assert maintenance_procedure_args(OPS.REMOVE_ORPHAN_FILES, POLICY, {}, NOW) == {
        "older_than": "2026-10-21T12:00:00+00:00"
    }
    spec = RemoveOrphanFilesSpec(
        target=RemoveOrphanFilesTarget(older_than=timedelta(days=2)),
        options=RemoveOrphanFilesOptions(prefix_mismatch_mode=PrefixMismatchMode.IGNORE),
    )
    policy = policy_with_operation(POLICY, OPS.REMOVE_ORPHAN_FILES, spec)
    assert maintenance_procedure_args(OPS.REMOVE_ORPHAN_FILES, policy, {}, NOW) == {
        "older_than": "2026-10-22T12:00:00+00:00",
        "prefix_mismatch_mode": "IGNORE",
    }


def test_args_of_an_absent_block_use_defaults():
    """A manual run of an operation the policy leaves out runs with what the platform decides."""
    empty = POLICY
    for op in OPS.ordered():
        empty = policy_with_operation(empty, op, None)
    assert maintenance_procedure_args(RDF, empty, {}, NOW) == {"options": {"target-file-size-bytes": 536870912}}
    assert maintenance_procedure_args(OPS.REWRITE_MANIFESTS, empty, {}, NOW) == {}
    assert maintenance_procedure_args(
        OPS.EXPIRE_SNAPSHOTS, empty, {"history.expire.min-snapshots-to-keep": "3"}, NOW
    ) == {"older_than": (NOW - timedelta(days=5)).isoformat(), "retain_last": 3}
    assert maintenance_procedure_args(OPS.REMOVE_ORPHAN_FILES, empty, {}, NOW) == {
        "older_than": (NOW - timedelta(days=3)).isoformat()
    }


def test_procedure_args_need_an_aware_time():
    """A naive time is rejected."""
    with pytest.raises(ValueError, match="timezone-aware"):
        maintenance_procedure_args(RDF, POLICY, {}, datetime(2026, 1, 1))  # noqa: DTZ001


NEVER_BY_AGE = {"history.expire.max-snapshot-age-ms": "9223372036854775807"}


def test_expire_args_clamp_a_never_by_age_property():
    """Long.MAX, Iceberg's "never by age", is clamped to 100 years instead of overflowing ``now - age``."""
    spec = ExpireSnapshotsSpec(target=ExpireSnapshotsTarget(min_snapshots_to_keep=4), options=None)
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, spec)
    assert maintenance_procedure_args(OPS.EXPIRE_SNAPSHOTS, policy, NEVER_BY_AGE, NOW) == {
        "older_than": (NOW - timedelta(days=36500)).isoformat(),
        "retain_last": 4,
    }


def test_expire_args_of_an_absent_block_clamp_a_never_by_age_property():
    """A manual run of an absent expire block clamps the table's Long.MAX age the same way."""
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, None)
    assert maintenance_procedure_args(OPS.EXPIRE_SNAPSHOTS, policy, NEVER_BY_AGE, NOW) == {
        "older_than": (NOW - timedelta(days=36500)).isoformat(),
        "retain_last": 1,
    }
