"""Test the discovery policy use case services."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
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
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
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
    EnsureDefaultTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    UpdateTableDiscoveryPolicyService,
)
from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
DR_ID = prefixed_id_pattern("dr")
DP_ID = prefixed_id_pattern("dp")


def _rule(glob: str = "orders_*", *, outcome: str = "manage", **extra: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "outcome": outcome,
        "conditions": [{"attribute": "table_name", "operator": "glob", "values": [glob]}],
        **extra,
    }


def _content(*rules: dict[str, Any], no_match_outcome: str = "unmanage", description: str = "") -> dict[str, Any]:
    return {"description": description, "no_match_outcome": no_match_outcome, "rules": list(rules)}


def one_rule() -> dict[str, Any]:
    """Return content with one managing rule sent without an id."""
    return _content(_rule())


def content_with_rule_id(rule_id: str) -> dict[str, Any]:
    """Return content whose one rule names ``rule_id``."""
    return _content(_rule(id=rule_id))


class ServiceWorld:
    """Run the discovery policy services on in-memory fakes seeded with the default policy."""

    def __init__(self) -> None:
        """Seed the default.

        The policies fake is not linked to the attachments, so it deletes an attached policy freely and
        only the delete service's own check refuses it.
        """
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.now = NOW
        EnsureDefaultTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableDiscoveryPolicyUseCaseInput()
        )

    def _clock(self) -> datetime:
        return self.now

    def create(self, name: str, content: dict[str, Any]) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create a policy."""
        return CreateTableDiscoveryPolicyService(self.policies, clock=self._clock).execute(
            CreateTableDiscoveryPolicyUseCaseInput(name=name, content=content)
        )

    def update(self, name: str, *, version: int, content: dict[str, Any]) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace a policy's content from ``version``."""
        return UpdateTableDiscoveryPolicyService(self.policies, clock=self._clock).execute(
            UpdateTableDiscoveryPolicyUseCaseInput(name=name, content=content, version=version)
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
    """Provide the services over fakes holding only the default policy."""
    return ServiceWorld()


def _rule_ids(content: dict[str, Any]) -> list[str]:
    return [rule["id"] for rule in content["rules"]]


def test_create_mints_rule_ids_and_starts_at_version_1(world: ServiceWorld) -> None:
    """Every rule sent without an id (absent or null) gets a fresh ``dr-`` id; the policy starts at version 1."""
    created = world.create("mine", _content(_rule("a_*"), _rule("b_*", id=None)))

    assert created.version == 1
    assert DP_ID.fullmatch(created.id)
    assert created.is_default is False
    assert (created.created_at, created.updated_at) == (NOW, NOW)
    ids = _rule_ids(created.content)
    assert all(DR_ID.fullmatch(rule_id) for rule_id in ids)
    assert len(set(ids)) == 2
    assert _rule_ids(world.get("mine").content) == ids


def test_create_refuses_any_rule_id_it_did_not_mint(world: ServiceWorld) -> None:
    """A create may name no rule id, however well-formed, and stores nothing."""
    with pytest.raises(ValidationError, match="unknown discovery rule id dr-00000000000000000000000001"):
        world.create("mine", content_with_rule_id("dr-00000000000000000000000001"))
    with pytest.raises(NotFoundError):
        world.get("mine")


def test_create_with_a_taken_name_conflicts(world: ServiceWorld) -> None:
    """A second policy may not take a name, the default's included."""
    world.create("mine", one_rule())
    with pytest.raises(ConflictError, match="'mine' already exists"):
        world.create("mine", one_rule())
    with pytest.raises(ConflictError, match="'default' already exists"):
        world.create("default", one_rule())


def test_create_refuses_a_bad_name_or_bad_content(world: ServiceWorld) -> None:
    """A name shaped like an id, a rule without conditions or an empty rule id is a validation error."""
    with pytest.raises(ValidationError):
        world.create("dp-00000000000000000000000001", one_rule())
    with pytest.raises(ValidationError, match="at least one condition"):
        world.create("mine", _content({"outcome": "manage", "conditions": []}))
    with pytest.raises(ValidationError, match="a rule id is a dr- id or absent"):
        world.create("mine", content_with_rule_id(""))
    assert [p.name for p in world.list().items] == ["default"]


def test_update_keeps_the_ids_it_was_sent_and_bumps_the_version(world: ServiceWorld) -> None:
    """A rule sent with its id keeps it; a rule sent without one gets a new id; the version increments."""
    created = world.create("mine", one_rule())
    kept = _rule_ids(created.content)[0]
    world.now = LATER

    updated = world.update("mine", version=1, content=_content(_rule("x_*"), _rule("orders_*", id=kept)))

    assert updated.version == 2
    assert (updated.created_at, updated.updated_at) == (NOW, LATER)
    minted, second = _rule_ids(updated.content)
    assert second == kept
    assert DR_ID.fullmatch(minted)
    assert minted != kept
    assert world.get("mine").content == updated.content


def test_update_with_another_policys_rule_id_is_refused(world: ServiceWorld) -> None:
    """A rule id the policy's current version does not hold is refused, and nothing is saved."""
    world.create("mine", one_rule())
    other = world.create("other", one_rule())
    with pytest.raises(ValidationError, match="unknown discovery rule id"):
        world.update("mine", version=1, content=content_with_rule_id(other.content["rules"][0]["id"]))
    assert world.get("mine").version == 1


def test_update_from_a_stale_version_conflicts(world: ServiceWorld) -> None:
    """An update from a version below or above the current one is a conflict, and nothing is saved."""
    world.create("mine", one_rule())
    world.update("mine", version=1, content=one_rule())

    with pytest.raises(ConflictError, match="is at version 2, not 1"):
        world.update("mine", version=1, content=_content(_rule("stale_*")))
    with pytest.raises(ConflictError, match="is at version 2, not 3"):
        world.update("mine", version=3, content=_content(_rule("stale_*")))
    current = world.get("mine")
    assert current.version == 2
    assert current.content["rules"][0]["conditions"][0]["values"] == ["orders_*"]


def test_update_of_the_default_conflicts(world: ServiceWorld) -> None:
    """The default is fixed: an update is a conflict and it stays at version 1."""
    with pytest.raises(ConflictError, match="the default discovery policy cannot be changed"):
        world.update("default", version=1, content=one_rule())
    assert world.get("default").version == 1


def test_update_of_an_unknown_policy_is_not_found(world: ServiceWorld) -> None:
    """An update of a name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.update("missing", version=1, content=one_rule())


def test_delete_of_the_default_or_an_attached_policy_conflicts(world: ServiceWorld) -> None:
    """The default is never deleted, and a policy is not deleted while it is attached; detached, it is."""
    with pytest.raises(ConflictError, match="the default discovery policy cannot be deleted"):
        world.delete("default")
    world.create("mine", one_rule())
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
    """Each version keeps the content it was written with and when; a version never written is not found."""
    created = world.create("mine", _content(_rule(), description="first"))
    world.now = LATER
    updated = world.update("mine", version=1, content=_content(_rule("x_*"), description="second"))

    first = world.get_version("mine", 1)
    assert (first.id, first.name, first.is_default, first.version) == (created.id, "mine", False, 1)
    assert first.content == created.content
    assert first.created_at == NOW
    second = world.get_version("mine", 2)
    assert (second.content, second.created_at) == (updated.content, LATER)
    for version in (0, 3):
        with pytest.raises(NotFoundError, match=f"has no version {version}"):
            world.get_version("mine", version)


def test_get_answers_the_default_and_refuses_an_unknown_name(world: ServiceWorld) -> None:
    """The default reads as the default; a name no policy has is not found."""
    default = world.get("default")
    assert (default.is_default, default.version, default.content["rules"]) == (True, 1, [])
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.get("missing")


def test_list_counts_attachments(world: ServiceWorld) -> None:
    """The default comes first, then the others by name, each with how many targets it is attached to."""
    world.create("zeta", one_rule())
    world.create("alpha", one_rule())
    world.attach("zeta", "prod")
    world.attach("zeta", "dev")
    world.attach("default", "lab")

    listed = world.list().items

    assert [(p.name, p.is_default, p.attachment_count) for p in listed] == [
        ("default", True, 1),
        ("alpha", False, 0),
        ("zeta", False, 2),
    ]
    assert listed[2].content == world.get("zeta").content
