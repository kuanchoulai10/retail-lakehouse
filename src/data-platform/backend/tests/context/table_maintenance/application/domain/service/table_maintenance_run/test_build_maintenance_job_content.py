"""Test the content a maintenance job of each operation is built with."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    PartitionFieldInfo,
    PartitionSpecInfo,
    SpecPartitions,
)
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
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    RemoveOrphanFilesJobContent,
    RewriteDataFilesJobContent,
    RewriteManifestsJobContent,
)
from context.table_maintenance.application.domain.service.table_maintenance_run import build_maintenance_job_content
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

OPS = MaintenanceOperation
RDF = OPS.REWRITE_DATA_FILES
POLICY = MaintenancePolicyContent.platform_default()
NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
NEVER_BY_AGE = {"history.expire.max-snapshot-age-ms": "9223372036854775807"}
REGION = PartitionFieldInfo(
    field_id=1000, name="region", source_column="region", source_type="string", transform="identity"
)
EU = SpecPartitions(spec=PartitionSpecInfo(spec_id=0, fields=(REGION,)), values=(("eu",),))


def _empty() -> MaintenancePolicyContent:
    policy = POLICY
    for op in OPS.ordered():
        policy = policy_with_operation(policy, op, None)
    return policy


def test_a_compaction_takes_the_policy_options_and_the_default_size():
    """The platform default compacts to Iceberg's default target size with its two options."""
    assert build_maintenance_job_content(RDF, POLICY, {}, NOW) == RewriteDataFilesJobContent(
        target_file_size_bytes=536870912,
        options=RewriteDataFilesOptions(min_input_files=2, partial_progress_enabled=True),
    )


def test_a_compaction_takes_the_table_target_file_size():
    """The target file size is the table's ``write.target-file-size-bytes``."""
    content = build_maintenance_job_content(RDF, POLICY, {"write.target-file-size-bytes": "1000"}, NOW)
    assert isinstance(content, RewriteDataFilesJobContent)
    assert content.target_file_size_bytes == 1000


def test_a_compaction_keeps_its_partitions():
    """The partitions a plan selected are the content's."""
    content = build_maintenance_job_content(RDF, POLICY, {}, NOW, partitions=(EU,))
    assert isinstance(content, RewriteDataFilesJobContent)
    assert content.partitions == (EU,)


def test_only_a_compaction_takes_partitions():
    """No other operation is scoped to partitions."""
    with pytest.raises(ValueError, match="only rewrite_data_files"):
        build_maintenance_job_content(OPS.EXPIRE_SNAPSHOTS, POLICY, {}, NOW, partitions=(EU,))


def test_a_compaction_keeps_a_sort_strategy():
    """The policy's options are kept as they are."""
    options = RewriteDataFilesOptions(strategy=RewriteDataFilesStrategy.SORT, sort_order="id DESC", rewrite_all=True)
    target = RewriteDataFilesTarget(reducible_files=AtMost(at_most=5))
    policy = policy_with_operation(POLICY, RDF, RewriteDataFilesSpec(target=target, options=options))
    assert build_maintenance_job_content(RDF, policy, {}, NOW).options == options


def test_a_compaction_block_without_options_has_none():
    """A block without options leaves every option to the procedure."""
    target = RewriteDataFilesTarget(reducible_files=AtMost(at_most=5))
    policy = policy_with_operation(POLICY, RDF, RewriteDataFilesSpec(target=target, options=None))
    assert build_maintenance_job_content(RDF, policy, {}, NOW).options == RewriteDataFilesOptions()


def test_an_expiry_uses_the_resolved_retention():
    """Snapshot expiry runs with the platform default's age and count."""
    assert build_maintenance_job_content(OPS.EXPIRE_SNAPSHOTS, POLICY, {}, NOW) == ExpireSnapshotsJobContent(
        older_than=NOW - timedelta(days=1), retain_last=10
    )


def test_an_expiry_keeps_its_options_and_the_table_age():
    """The target's count, the table's age and the policy's options make the expiry."""
    options = ExpireSnapshotsOptions(max_concurrent_deletes=8, stream_results=True)
    spec = ExpireSnapshotsSpec(target=ExpireSnapshotsTarget(min_snapshots_to_keep=4), options=options)
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, spec)
    props = {"history.expire.max-snapshot-age-ms": str(2 * 86400 * 1000)}
    assert build_maintenance_job_content(OPS.EXPIRE_SNAPSHOTS, policy, props, NOW) == ExpireSnapshotsJobContent(
        older_than=datetime(2026, 10, 22, 12, tzinfo=UTC), retain_last=4, options=options
    )


def test_an_expiry_clamps_a_never_by_age_property():
    """Long.MAX, Iceberg's "never by age", is clamped to 100 years instead of overflowing ``now - age``."""
    spec = ExpireSnapshotsSpec(target=ExpireSnapshotsTarget(min_snapshots_to_keep=4), options=None)
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, spec)
    content = build_maintenance_job_content(OPS.EXPIRE_SNAPSHOTS, policy, NEVER_BY_AGE, NOW)
    assert content == ExpireSnapshotsJobContent(older_than=NOW - timedelta(days=36500), retain_last=4)


def test_an_expiry_left_out_clamps_a_never_by_age_property():
    """A manual run of an absent expire block clamps the table's Long.MAX age the same way."""
    policy = policy_with_operation(POLICY, OPS.EXPIRE_SNAPSHOTS, None)
    content = build_maintenance_job_content(OPS.EXPIRE_SNAPSHOTS, policy, NEVER_BY_AGE, NOW)
    assert content == ExpireSnapshotsJobContent(older_than=NOW - timedelta(days=36500), retain_last=1)


def test_a_manifest_rewrite_keeps_its_options():
    """A manifest rewrite has the policy's options, none when it sets none."""
    assert build_maintenance_job_content(OPS.REWRITE_MANIFESTS, POLICY, {}, NOW) == RewriteManifestsJobContent()
    spec = RewriteManifestsSpec(
        target=RewriteManifestsTarget(small_manifests=AtMost(at_most=5)),
        options=RewriteManifestsOptions(use_caching=False),
    )
    policy = policy_with_operation(POLICY, OPS.REWRITE_MANIFESTS, spec)
    assert build_maintenance_job_content(OPS.REWRITE_MANIFESTS, policy, {}, NOW) == RewriteManifestsJobContent(
        options=RewriteManifestsOptions(use_caching=False)
    )


def test_an_orphan_removal_keeps_its_age_and_options():
    """Orphan removal has its target's age and its set options."""
    assert build_maintenance_job_content(OPS.REMOVE_ORPHAN_FILES, POLICY, {}, NOW) == RemoveOrphanFilesJobContent(
        older_than=NOW - timedelta(days=3)
    )
    options = RemoveOrphanFilesOptions(prefix_mismatch_mode=PrefixMismatchMode.IGNORE)
    spec = RemoveOrphanFilesSpec(target=RemoveOrphanFilesTarget(older_than=timedelta(days=2)), options=options)
    policy = policy_with_operation(POLICY, OPS.REMOVE_ORPHAN_FILES, spec)
    assert build_maintenance_job_content(OPS.REMOVE_ORPHAN_FILES, policy, {}, NOW) == RemoveOrphanFilesJobContent(
        older_than=NOW - timedelta(days=2), options=options
    )


def test_an_operation_the_policy_leaves_out_runs_with_the_platform_defaults():
    """A manual run of an operation the policy leaves out runs with what the platform decides."""
    empty = _empty()
    assert build_maintenance_job_content(RDF, empty, {}, NOW) == RewriteDataFilesJobContent(
        target_file_size_bytes=536870912
    )
    assert build_maintenance_job_content(OPS.REWRITE_MANIFESTS, empty, {}, NOW) == RewriteManifestsJobContent()
    expiry = build_maintenance_job_content(
        OPS.EXPIRE_SNAPSHOTS, empty, {"history.expire.min-snapshots-to-keep": "3"}, NOW
    )
    assert expiry == ExpireSnapshotsJobContent(older_than=NOW - timedelta(days=5), retain_last=3)
    assert build_maintenance_job_content(OPS.REMOVE_ORPHAN_FILES, empty, {}, NOW) == RemoveOrphanFilesJobContent(
        older_than=NOW - timedelta(days=3)
    )


def test_a_naive_time_is_refused():
    """A naive time names no instant."""
    with pytest.raises(ValueError, match="timezone-aware"):
        build_maintenance_job_content(RDF, POLICY, {}, datetime(2026, 1, 1))  # noqa: DTZ001
