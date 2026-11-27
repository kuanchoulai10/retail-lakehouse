"""Test the discovery policy use case services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    CreateTableDiscoveryPolicyUseCaseOutput,
    DeleteTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseOutput,
    GetTableDiscoveryPolicyVersionUseCaseInput,
    GetTableDiscoveryPolicyVersionUseCaseOutput,
    ListTableDiscoveryPoliciesUseCaseInput,
    ListTableDiscoveryPoliciesUseCaseOutput,
    UpdateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    DeleteTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    UpdateTableDiscoveryPolicyService,
)
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
from tests.context.table_maintenance.id_shape import IdShape

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
DP_ID = IdShape(TableDiscoveryPolicyId)


def _rule(action: str, pattern: str) -> dict[str, str]:
    return {"action": action, "table_name_pattern": pattern}


INCLUDE_ORDERS = (_rule("include", "orders_*"),)
INCLUDE_ALL_BUT_TMP = (_rule("include", "*"), _rule("exclude", "*_tmp"))


class ServiceWorld:
    """Run the discovery policy services on in-memory fakes that start empty."""

    def __init__(self) -> None:
        """Start with no policy.

        The policies fake is not linked to the attachments, so it deletes an attached policy freely and
        only the delete service's own check refuses it.
        """
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.requests = RecordingSendDiscoveryRequestGateway()
        self.schedules = RecordingSyncDiscoverySchedulesGateway()
        self.now = NOW

    def _clock(self) -> datetime:
        return self.now

    def create(
        self, name: str, rules: tuple[dict[str, str], ...] = INCLUDE_ORDERS, *, description: str = ""
    ) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create a policy."""
        return CreateTableDiscoveryPolicyService(self.policies, clock=self._clock).execute(
            CreateTableDiscoveryPolicyUseCaseInput(name=name, description=description, rules=rules)
        )

    def update(
        self, name: str, *, version: int, rules: tuple[dict[str, str], ...], description: str = ""
    ) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Revise a policy from ``version``."""
        return UpdateTableDiscoveryPolicyService(
            self.policies, self.attachments, self.requests, self.schedules, clock=self._clock
        ).execute(
            UpdateTableDiscoveryPolicyUseCaseInput(name=name, description=description, rules=rules, version=version)
        )

    def get(self, name: str) -> GetTableDiscoveryPolicyUseCaseOutput:
        """Get a policy at its current version."""
        return GetTableDiscoveryPolicyService(self.policies).execute(GetTableDiscoveryPolicyUseCaseInput(name=name))

    def get_version(self, name: str, version: int) -> GetTableDiscoveryPolicyVersionUseCaseOutput:
        """Get one stored version of a policy."""
        return GetTableDiscoveryPolicyVersionService(self.policies).execute(
            GetTableDiscoveryPolicyVersionUseCaseInput(name=name, version=version)
        )

    def delete(self, name: str) -> None:
        """Delete a policy."""
        DeleteTableDiscoveryPolicyService(self.policies, self.attachments).execute(
            DeleteTableDiscoveryPolicyUseCaseInput(name=name)
        )

    def list(self) -> ListTableDiscoveryPoliciesUseCaseOutput:
        """List the policies."""
        return ListTableDiscoveryPoliciesService(self.policies, self.attachments).execute(
            ListTableDiscoveryPoliciesUseCaseInput()
        )

    def attach(self, name: str, catalog: str) -> TableDiscoveryPolicyAttachment:
        """Attach a policy to a catalog straight through the repos (the attach use case comes later)."""
        policy = self.policies.get_by_name(TableDiscoveryPolicyName(value=name))
        assert policy is not None
        target = PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))
        return self.attachments.create(TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW))


@pytest.fixture
def world() -> ServiceWorld:
    """Provide the services over empty fakes."""
    return ServiceWorld()


def test_create_builds_the_rules_in_order_and_starts_at_version_1(world: ServiceWorld) -> None:
    """The rules sent are the policy's rules, in the order sent; the policy starts at version 1."""
    created = world.create("mine", INCLUDE_ALL_BUT_TMP, description="no temporary tables")

    assert created.version == 1
    assert DP_ID.fullmatch(created.id)
    assert (created.created_at, created.updated_at) == (NOW, NOW)
    assert (created.description, created.rules) == ("no temporary tables", INCLUDE_ALL_BUT_TMP)
    assert world.get("mine").rules == INCLUDE_ALL_BUT_TMP


def test_create_accepts_exclude_rules_only(world: ServiceWorld) -> None:
    """A policy may hold exclude rules only."""
    created = world.create("mine", (_rule("exclude", "*"),))

    assert created.rules == ({"action": "exclude", "table_name_pattern": "*"},)


def test_create_with_a_taken_name_conflicts(world: ServiceWorld) -> None:
    """A second policy may not take a name."""
    world.create("mine")
    with pytest.raises(ConflictError, match="'mine' already exists"):
        world.create("mine")


@pytest.mark.parametrize(
    ("rules", "message"),
    [
        ((), "at least one rule"),
        ((_rule("manage", "*"),), "manage"),
        ((_rule("include", ""),), "must not be empty"),
        (({"action": "include"},), "table_name_pattern"),
        (({"table_name_pattern": "*"},), "action"),
        (({"action": "include", "table_name_pattern": "*", "outcome": "manage"},), "outcome"),
    ],
)
def test_create_refuses_bad_rules(world: ServiceWorld, rules: tuple[dict[str, str], ...], message: str) -> None:
    """No rule, an unknown action, an empty pattern, a missing or an unknown field is a validation error."""
    with pytest.raises(ValidationError, match=message):
        world.create("mine", rules)
    assert world.list().items == ()


def test_create_refuses_a_bad_name(world: ServiceWorld) -> None:
    """A name shaped like an id is a validation error."""
    with pytest.raises(ValidationError):
        world.create("dp-00000000000000000000000001")


def test_update_replaces_the_rules_and_bumps_the_version(world: ServiceWorld) -> None:
    """A revision holds the rules and description sent; the version increments."""
    world.create("mine")
    world.now = LATER

    updated = world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP, description="second")

    assert updated.version == 2
    assert (updated.created_at, updated.updated_at) == (NOW, LATER)
    assert (updated.description, updated.rules) == ("second", INCLUDE_ALL_BUT_TMP)
    assert world.get("mine").rules == INCLUDE_ALL_BUT_TMP


def test_update_with_bad_rules_is_refused(world: ServiceWorld) -> None:
    """A revision with no rule is a validation error, and nothing is saved."""
    world.create("mine")
    with pytest.raises(ValidationError, match="at least one rule"):
        world.update("mine", version=1, rules=())
    assert world.get("mine").version == 1


def test_update_from_a_stale_version_conflicts(world: ServiceWorld) -> None:
    """An update from a version below or above the current one is a conflict, and nothing is saved."""
    world.create("mine")
    world.update("mine", version=1, rules=INCLUDE_ORDERS)

    with pytest.raises(ConflictError, match="is at version 2, not 1"):
        world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)
    with pytest.raises(ConflictError, match="is at version 2, not 3"):
        world.update("mine", version=3, rules=INCLUDE_ALL_BUT_TMP)
    current = world.get("mine")
    assert (current.version, current.rules) == (2, INCLUDE_ORDERS)


def test_update_rescans_the_catalogs_it_is_attached_in(world: ServiceWorld) -> None:
    """Once saved, each catalog the policy is attached in is scanned again and the schedules are synced."""
    world.create("mine")
    world.attach("mine", "prod")

    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)

    assert [request.catalog for request in world.requests.calls] == ["prod"]
    assert world.schedules.synced[-1].catalogs == ("prod",)


def test_update_of_an_unknown_policy_is_not_found(world: ServiceWorld) -> None:
    """An update of a name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.update("missing", version=1, rules=INCLUDE_ORDERS)


def test_delete_of_an_attached_policy_conflicts(world: ServiceWorld) -> None:
    """A policy is not deleted while it is attached; detached, it is."""
    world.create("mine")
    attachment = world.attach("mine", "prod")

    with pytest.raises(ConflictError, match="policy mine is still attached to a catalog, namespace or table"):
        world.delete("mine")
    assert world.get("mine").version == 1

    world.attachments.delete(attachment.id)
    world.delete("mine")
    with pytest.raises(NotFoundError):
        world.get("mine")
    with pytest.raises(NotFoundError):
        world.get_version("mine", 1)


def test_delete_of_an_unknown_policy_is_not_found(world: ServiceWorld) -> None:
    """A delete of a name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.delete("missing")


def test_a_version_stays_readable_after_an_update(world: ServiceWorld) -> None:
    """Each version keeps the description, rules and time it was written with; one never written is not found."""
    created = world.create("mine", INCLUDE_ORDERS, description="first")
    world.now = LATER
    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP, description="second")

    first = world.get_version("mine", 1)
    assert (first.id, first.name, first.version) == (created.id, "mine", 1)
    assert (first.description, first.rules, first.created_at) == ("first", INCLUDE_ORDERS, NOW)
    second = world.get_version("mine", 2)
    assert (second.description, second.rules, second.created_at) == ("second", INCLUDE_ALL_BUT_TMP, LATER)
    for version in (0, 3):
        with pytest.raises(NotFoundError, match=f"has no version {version}"):
            world.get_version("mine", version)


def test_get_refuses_an_unknown_name(world: ServiceWorld) -> None:
    """A name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.get("missing")


def test_list_counts_attachments_by_name(world: ServiceWorld) -> None:
    """The policies come by name, each with how many targets it is attached to."""
    world.create("zeta", INCLUDE_ALL_BUT_TMP)
    world.create("alpha")
    world.attach("zeta", "prod")
    world.attach("zeta", "dev")

    listed = world.list().items

    assert [(p.name, p.attachment_count) for p in listed] == [("alpha", 0), ("zeta", 2)]
    assert listed[1].rules == world.get("zeta").rules
