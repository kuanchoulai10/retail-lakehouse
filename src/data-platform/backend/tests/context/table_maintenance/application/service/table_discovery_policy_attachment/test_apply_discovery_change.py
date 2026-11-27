"""Test that every discovery policy change syncs the schedules and rescans the catalogs it affects."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
    DetachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesGatewayInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    UpdateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyService,
    DetachTableDiscoveryPolicyService,
    apply_discovery_change,
)
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_sync_discovery_schedules_gateway import (
    RecordingSyncDiscoverySchedulesGateway,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
MANAGE_ALL = ({"action": "include", "table_name_pattern": "*"},)
UNMANAGE_ALL = ({"action": "exclude", "table_name_pattern": "*"},)


def _scan(catalog: str, change_id: str) -> SendDiscoveryRequestGatewayInput:
    return SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id)


def _synced(catalogs: tuple[str, ...], removed: tuple[str, ...] = ()) -> SyncDiscoverySchedulesGatewayInput:
    return SyncDiscoverySchedulesGatewayInput(catalogs=catalogs, removed=removed)


class _World:
    """Run the update, attach and detach services on fakes, recording the schedule syncs and the scans.

    Policies ``manage-all`` (includes every table) and ``unmanage-all`` (excludes every table) exist; the
    catalogs ``iceberg``, ``lake`` and ``other`` exist, ``iceberg`` holding the namespace ``sales``.
    Each change takes the next change id, ``c1``, ``c2`` and so on.
    """

    def __init__(self) -> None:
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.catalog = FakeReadTableMetadataGateway()
        self.requests = RecordingSendDiscoveryRequestGateway()
        self.schedules = RecordingSyncDiscoverySchedulesGateway()
        self.change_ids = 0
        for catalog in ("iceberg", "lake", "other"):
            self.catalog.add_catalog(catalog)
        self.catalog.add_namespace("iceberg", "sales")
        for name, rules in (("manage-all", MANAGE_ALL), ("unmanage-all", UNMANAGE_ALL)):
            CreateTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
                CreateTableDiscoveryPolicyUseCaseInput(name=name, description="", rules=rules)
            )

    @property
    def change_id(self) -> str:
        """Return the id the latest change took."""
        return f"c{self.change_ids}"

    def _new_change_id(self) -> str:
        self.change_ids += 1
        return self.change_id

    def forget(self) -> None:
        """Forget the scans and syncs recorded so far, keeping the scheduled catalogs."""
        self.requests.calls.clear()
        self.schedules.synced.clear()

    def attach(self, policy: str, type_: str, path: tuple[str, ...]) -> AttachTableDiscoveryPolicyUseCaseOutput:
        return AttachTableDiscoveryPolicyService(
            self.policies,
            self.attachments,
            self.catalog,
            self.requests,
            self.schedules,
            clock=lambda: NOW,
            new_change_id=self._new_change_id,
        ).execute(AttachTableDiscoveryPolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def detach(self, policy: str, attachment_id: str) -> None:
        DetachTableDiscoveryPolicyService(
            self.policies, self.attachments, self.requests, self.schedules, new_change_id=self._new_change_id
        ).execute(DetachTableDiscoveryPolicyUseCaseInput(policy_name=policy, attachment_id=attachment_id))

    def update(self, name: str, rules: tuple[dict[str, Any], ...]) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        policy = self.policies.get_by_name(TableDiscoveryPolicyName(value=name))
        assert policy is not None
        return UpdateTableDiscoveryPolicyService(
            self.policies,
            self.attachments,
            self.requests,
            self.schedules,
            clock=lambda: NOW,
            new_change_id=self._new_change_id,
        ).execute(
            UpdateTableDiscoveryPolicyUseCaseInput(name=name, version=policy.version, description="", rules=rules)
        )


@pytest.fixture
def world() -> _World:
    """Provide the change services over fakes."""
    return _World()


def test_attaching_a_managing_policy_schedules_and_scans_the_catalog(world: _World) -> None:
    """A catalog that starts being scanned gets its schedule and a scan of its own change."""
    world.attach("manage-all", "catalog", ("iceberg",))

    assert world.schedules.synced == [_synced(("iceberg",))]
    assert world.schedules.scheduled == {"iceberg"}
    assert world.requests.calls == [_scan("iceberg", world.change_id)]


def test_detaching_the_last_managing_policy_rescans_and_drops_the_schedule(world: _World) -> None:
    """A catalog that stops being scanned gets one final scan, which unmanages its tables; then its schedule goes."""
    attached = world.attach("manage-all", "catalog", ("iceberg",))
    world.forget()

    world.detach("manage-all", attached.id)

    assert world.requests.calls == [_scan("iceberg", world.change_id)]
    assert world.schedules.synced == [_synced((), removed=("iceberg",))]
    assert world.schedules.scheduled == set()


def test_a_catalog_whose_final_scan_cannot_start_keeps_its_schedule(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    """Without its final scan a catalog that left keeps its schedule, whose next firing unmanages its tables."""
    attached = world.attach("manage-all", "catalog", ("iceberg",))
    world.forget()
    world.requests.failing.add("iceberg")

    with caplog.at_level(logging.WARNING):
        world.detach("manage-all", attached.id)

    assert world.attachments.list_all() == []
    assert world.schedules.synced == [_synced(())]
    assert world.schedules.scheduled == {"iceberg"}
    assert "iceberg" in caplog.text


def test_a_change_deletes_no_schedule_it_did_not_remove(world: _World) -> None:
    """A schedule of a catalog the change did not take out of the scanned set is left to the worker start."""
    world.schedules.scheduled.add("stray")

    world.attach("manage-all", "catalog", ("iceberg",))

    assert world.schedules.synced == [_synced(("iceberg",))]
    assert world.schedules.scheduled == {"iceberg", "stray"}


def test_attaching_an_exclude_only_policy_schedules_and_scans_the_catalog(world: _World) -> None:
    """A policy that excludes every table still decides the catalog's tables, so its catalog is scanned."""
    world.attach("unmanage-all", "catalog", ("iceberg",))

    assert world.schedules.synced == [_synced(("iceberg",))]
    assert world.requests.calls == [_scan("iceberg", world.change_id)]


def test_opting_a_namespace_out_rescans_its_still_scanned_catalog(world: _World) -> None:
    """An excluding policy on a namespace under a managing catalog keeps the catalog scanned and rescans it."""
    world.attach("manage-all", "catalog", ("iceberg",))
    world.forget()

    world.attach("unmanage-all", "namespace", ("iceberg", "sales"))

    assert world.schedules.synced == [_synced(("iceberg",))]
    assert world.requests.calls == [_scan("iceberg", world.change_id)]


def test_a_change_rescans_only_its_own_catalog(world: _World) -> None:
    """Attaching in one catalog leaves the scans of the other scanned catalogs alone."""
    world.attach("manage-all", "catalog", ("lake",))
    world.forget()

    world.attach("manage-all", "catalog", ("iceberg",))

    assert world.schedules.synced == [_synced(("iceberg", "lake"))]
    assert world.requests.calls == [_scan("iceberg", world.change_id)]


def test_update_rescans_every_catalog_the_policy_is_attached_in(world: _World) -> None:
    """An update rescans each catalog its policy is attached in, and no other scanned catalog."""
    world.attach("unmanage-all", "catalog", ("iceberg",))
    world.attach("unmanage-all", "namespace", ("iceberg", "sales"))
    world.attach("unmanage-all", "catalog", ("lake",))
    world.attach("manage-all", "catalog", ("other",))
    world.forget()

    world.update("unmanage-all", MANAGE_ALL)

    assert world.requests.calls == [_scan("iceberg", world.change_id), _scan("lake", world.change_id)]
    assert world.schedules.synced == [_synced(("iceberg", "lake", "other"))]


def test_an_update_that_stops_managing_rescans_its_catalogs_and_keeps_them_scanned(world: _World) -> None:
    """A policy that now excludes every table still decides its catalogs: each is rescanned, none is removed."""
    world.attach("manage-all", "catalog", ("iceberg",))
    world.attach("manage-all", "catalog", ("lake",))
    world.forget()

    world.update("manage-all", UNMANAGE_ALL)

    assert world.requests.calls == [_scan("iceberg", world.change_id), _scan("lake", world.change_id)]
    assert world.schedules.synced == [_synced(("iceberg", "lake"))]
    assert world.schedules.scheduled == {"iceberg", "lake"}


def test_a_failed_schedule_sync_still_saves_and_rescans(world: _World, caplog: pytest.LogCaptureFixture) -> None:
    """A sync that fails is logged; the change is stored and its scan is started."""
    world.schedules.failing = True

    with caplog.at_level(logging.ERROR):
        out = world.attach("manage-all", "catalog", ("iceberg",))

    assert [a.id.value for a in world.attachments.list_all()] == [out.id]
    assert world.requests.calls == [_scan("iceberg", world.change_id)]
    assert "could not sync the discovery schedules" in caplog.text


def test_a_failed_rescan_is_logged_and_the_change_answers(world: _World, caplog: pytest.LogCaptureFixture) -> None:
    """A scan that cannot start is logged, the other catalogs are still scanned and the schedules synced."""
    world.attach("unmanage-all", "catalog", ("iceberg",))
    world.attach("unmanage-all", "catalog", ("lake",))
    world.forget()
    world.requests.failing.add("iceberg")

    with caplog.at_level(logging.ERROR):
        out = world.update("unmanage-all", MANAGE_ALL)

    assert out.version == 2
    assert world.requests.calls == [_scan("lake", world.change_id)]
    assert world.schedules.synced == [_synced(("iceberg", "lake"))]
    assert "could not start discovery in catalog iceberg" in caplog.text


def test_a_refused_update_neither_syncs_nor_rescans(world: _World) -> None:
    """An update with no rule saves nothing, syncs nothing and scans nothing."""
    world.attach("manage-all", "catalog", ("iceberg",))
    world.forget()

    with pytest.raises(ValidationError, match="at least one rule"):
        world.update("manage-all", ())

    assert world.schedules.synced == []
    assert world.requests.calls == []


def test_a_refused_attach_neither_syncs_nor_rescans(world: _World) -> None:
    """An attach to a target that does not exist syncs nothing and scans nothing."""
    with pytest.raises(NotFoundError):
        world.attach("manage-all", "catalog", ("ghost",))

    assert world.schedules.synced == []
    assert world.requests.calls == []


def test_each_change_has_its_own_change_id(world: _World) -> None:
    """Two changes in a row start scans under two change ids, so the later never joins the earlier's run."""
    world.attach("manage-all", "catalog", ("iceberg",))
    world.attach("unmanage-all", "namespace", ("iceberg", "sales"))

    assert world.requests.calls == [_scan("iceberg", "c1"), _scan("iceberg", "c2")]


def _apply(world: _World, change: Any, affected: Any) -> str:  # noqa: ANN401
    return apply_discovery_change(
        world.policies,
        world.attachments,
        world.requests,
        world.schedules,
        change,
        affected_catalogs=affected,
        change_id="c9",
    )


def test_a_failed_read_after_the_change_is_logged_and_the_change_answers(
    world: _World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When the scanned catalogs cannot be read back, nothing is scanned or synced and the change still answers."""

    def change() -> str:
        def broken() -> list[Any]:
            msg = "database is gone"
            raise RuntimeError(msg)

        monkeypatch.setattr(world.attachments, "list_all", broken)
        return "done"

    with caplog.at_level(logging.ERROR):
        assert _apply(world, change, lambda: {"iceberg"}) == "done"

    assert (world.requests.calls, world.schedules.synced) == ([], [])
    assert "could not work out what discovery policy change c9 affects" in caplog.text


def test_failed_affected_catalogs_are_logged_and_the_change_answers(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    """When the affected catalogs cannot be worked out, nothing is scanned or synced and the change still answers."""

    def affected() -> set[str]:
        msg = "database is gone"
        raise RuntimeError(msg)

    with caplog.at_level(logging.ERROR):
        assert _apply(world, lambda: "done", affected) == "done"

    assert (world.requests.calls, world.schedules.synced) == ([], [])
    assert "could not work out what discovery policy change c9 affects" in caplog.text


def test_a_catalog_that_left_but_was_not_affected_is_neither_scanned_nor_warned_about(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    """Only an affected catalog whose final scan failed is warned about; one the change did not affect is not."""
    attached = world.attach("manage-all", "catalog", ("iceberg",))
    world.forget()

    with caplog.at_level(logging.WARNING):
        _apply(world, lambda: world.attachments.delete(world.attachments.list_all()[0].id), set)

    assert attached.id not in [a.id.value for a in world.attachments.list_all()]
    assert world.requests.calls == []
    assert world.schedules.synced == [_synced(())]
    assert "keeping the discovery schedule" not in caplog.text
