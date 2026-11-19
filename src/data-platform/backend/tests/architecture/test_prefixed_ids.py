"""Guard test: every id type of the project says whether it is prefixed, and with which prefix (docs/adr/0011).

Every ``EntityId`` subclass in a context is in exactly one of three lists:

- ``EXPECTED_PREFIXES``, class name to the prefix its ``PREFIX`` declares;
- ``UNPREFIXED``, ids that are never prefixed: the table maintenance ``TableId`` (the Iceberg table UUID) and
  ``CatalogDiscoveryId`` (the catalog name), and every catalog context id (Polaris is its source of truth);
- ``PENDING``, ids that will get a prefix but do not have it yet. A name here may not exist yet. Each task of the
  prefixed-id plan moved its rows from ``PENDING`` to ``EXPECTED_PREFIXES``, so ``PENDING`` is empty now.

Every context is walked, not one by name, so a new context's ids must be listed too. Prefixes are unique across
``EXPECTED_PREFIXES`` and across every id type of the project that declares one.
"""

from __future__ import annotations

import importlib
from collections import Counter
from typing import TYPE_CHECKING, ClassVar

from base import EntityId
from tests.architecture.boundaries import PROJECT_PACKAGES
from tests.architecture.contexts import BACKEND, CONTEXT_ROOT

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from collections.abc import Set as AbstractSet

EXPECTED_PREFIXES: dict[str, str] = {
    "TableDiscoveryRulesId": "dp",
    "TableDiscoveryRuleId": "dr",
    "TableMaintenanceRunId": "mr",
    "TableReconciliationId": "rc",
    "CompactionRoundId": "cr",
    "CompactionCandidateId": "cc",
    "TableMaintenancePolicyAttachmentId": "pa",
    "TableMaintenancePolicyId": "mp",
}
UNPREFIXED: frozenset[str] = frozenset(
    {
        "TableId",
        "CatalogDiscoveryId",
        "CatalogId",
        "NamespaceId",
        "GenericTableId",
        "ViewId",
    }
)
PENDING: frozenset[str] = frozenset()


def prefix_violations(
    id_types: Iterable[type[EntityId]],
    expected: Mapping[str, str],
    unprefixed: AbstractSet[str],
    pending: AbstractSet[str],
) -> list[str]:
    """Return one line per id type that breaks the prefix rules of the module docstring."""
    id_types = list(id_types)
    lists: dict[str, AbstractSet[str]] = {
        "EXPECTED_PREFIXES": set(expected),
        "UNPREFIXED": unprefixed,
        "PENDING": pending,
    }
    violations = [line for id_type in id_types for line in _listing_violations(id_type, expected, lists)]
    known = {id_type.__name__ for id_type in id_types}
    violations.extend(
        f"{list_name} names {name}, which is no id type"
        for list_name in ("EXPECTED_PREFIXES", "UNPREFIXED")
        for name in sorted(lists[list_name])
        if name not in known
    )
    violations.extend(_shared_prefixes("EXPECTED_PREFIXES gives the prefix {!r} to more than one id type", expected))
    declared = {id_type.__name__: id_type.PREFIX for id_type in id_types if id_type.PREFIX is not None}
    violations.extend(_shared_prefixes("the prefix {!r} is declared by more than one id type", declared))
    return violations


def _listing_violations(
    id_type: type[EntityId], expected: Mapping[str, str], lists: Mapping[str, AbstractSet[str]]
) -> list[str]:
    """Return what is wrong with how ``id_type`` is listed and with the prefix it declares."""
    name, prefix = id_type.__name__, id_type.PREFIX
    listed_in = [list_name for list_name, names in lists.items() if name in names]
    if not listed_in:
        return [f"{name} is in none of {', '.join(lists)}"]
    if len(listed_in) > 1:
        return [f"{name} is in more than one of the lists: {', '.join(listed_in)}"]
    if name in expected:
        return [] if prefix == expected[name] else [f"{name} declares PREFIX {prefix!r}, expected {expected[name]!r}"]
    if prefix is None:
        return []
    hint = "; move it to EXPECTED_PREFIXES" if name in lists["PENDING"] else ""
    return [f"{name} is in {listed_in[0]} but declares PREFIX {prefix!r}{hint}"]


def _shared_prefixes(message: str, prefix_by_name: Mapping[str, str | None]) -> list[str]:
    """Return ``message`` (formatted with the prefix) and the names, for each prefix more than one name has."""
    counts = Counter(prefix_by_name.values())
    return [
        f"{message.format(prefix)}: {', '.join(sorted(n for n, p in prefix_by_name.items() if p == prefix))}"
        for prefix in sorted(p for p, count in counts.items() if count > 1 and p is not None)
    ]


def _import_every_context_module() -> None:
    """Import every module under ``context/`` so every id type is defined."""
    for path in sorted(CONTEXT_ROOT.rglob("*.py")):
        parts = path.relative_to(BACKEND).with_suffix("").parts
        importlib.import_module(".".join(parts[:-1] if parts[-1] == "__init__" else parts))


def _project_id_types() -> list[type[EntityId]]:
    """Return every ``EntityId`` subclass defined in a project package (test stubs excluded)."""
    _import_every_context_module()
    found: list[type[EntityId]] = []
    pending = list(EntityId.__subclasses__())
    while pending:
        id_type = pending.pop()
        pending.extend(id_type.__subclasses__())
        if id_type.__module__.split(".")[0] in PROJECT_PACKAGES:
            found.append(id_type)
    return sorted(found, key=lambda id_type: f"{id_type.__module__}.{id_type.__qualname__}")


def test_every_id_type_declares_its_prefix_decision():
    """Every id type of the project is listed once, with the prefix it declares, and no prefix is used twice."""
    violations = prefix_violations(_project_id_types(), EXPECTED_PREFIXES, UNPREFIXED, PENDING)
    assert violations == [], "\n".join(violations)


def test_the_walk_finds_the_context_id_types():
    """The walk sees id types of the contexts and none of the test stubs."""
    names = {id_type.__name__ for id_type in _project_id_types()}

    assert {"TableId", "CatalogId", "TableMaintenanceRunId"} <= names
    assert all(not id_type.__module__.startswith("tests.") for id_type in _project_id_types())


class _UnlistedId(EntityId):
    """An id type no list names."""


class _ExpectedId(EntityId):
    """An id type declaring the prefix ``ab``."""

    PREFIX: ClassVar[str | None] = "ab"


class _SamePrefixId(EntityId):
    """A second id type declaring the prefix ``ab``."""

    PREFIX: ClassVar[str | None] = "ab"


class _PlainId(EntityId):
    """An id type declaring no prefix."""


def test_an_unlisted_id_type_is_reported():
    """An id type in none of the lists is reported, naming the lists."""
    violations = prefix_violations([_UnlistedId], {}, frozenset(), frozenset())

    assert violations == [
        "_UnlistedId is in none of EXPECTED_PREFIXES, UNPREFIXED, PENDING",
    ]


def test_an_id_type_listed_twice_is_reported():
    """An id type in two lists is reported, naming both."""
    violations = prefix_violations([_PlainId], {}, frozenset({"_PlainId"}), frozenset({"_PlainId"}))

    assert violations == ["_PlainId is in more than one of the lists: UNPREFIXED, PENDING"]


def test_a_prefix_other_than_the_expected_one_is_reported():
    """An expected id type must declare exactly the expected prefix."""
    violations = prefix_violations([_ExpectedId, _PlainId], {"_ExpectedId": "cd", "_PlainId": "ef"}, set(), set())

    assert violations == [
        "_ExpectedId declares PREFIX 'ab', expected 'cd'",
        "_PlainId declares PREFIX None, expected 'ef'",
    ]


def test_an_unprefixed_or_pending_id_type_with_a_prefix_is_reported():
    """An id type listed as unprefixed or pending must not declare a prefix."""
    assert prefix_violations([_ExpectedId], {}, {"_ExpectedId"}, set()) == [
        "_ExpectedId is in UNPREFIXED but declares PREFIX 'ab'",
    ]
    assert prefix_violations([_ExpectedId], {}, set(), {"_ExpectedId"}) == [
        "_ExpectedId is in PENDING but declares PREFIX 'ab'; move it to EXPECTED_PREFIXES",
    ]


def test_a_listed_name_that_does_not_exist_is_reported_unless_pending():
    """A stale name in EXPECTED_PREFIXES or UNPREFIXED is reported; a PENDING name may not exist yet."""
    violations = prefix_violations([], {"_GoneId": "gh"}, {"_LostId"}, {"_FutureId"})

    assert violations == [
        "EXPECTED_PREFIXES names _GoneId, which is no id type",
        "UNPREFIXED names _LostId, which is no id type",
    ]


def test_a_prefix_two_id_types_declare_is_reported():
    """Two id types declaring the same prefix are reported, even when both are expected to."""
    violations = prefix_violations(
        [_ExpectedId, _SamePrefixId], {"_ExpectedId": "ab", "_SamePrefixId": "ab"}, set(), set()
    )

    assert violations == [
        "EXPECTED_PREFIXES gives the prefix 'ab' to more than one id type: _ExpectedId, _SamePrefixId",
        "the prefix 'ab' is declared by more than one id type: _ExpectedId, _SamePrefixId",
    ]


def test_a_clean_set_of_lists_passes():
    """Lists that agree with the id types report nothing."""
    assert prefix_violations([_ExpectedId, _PlainId], {"_ExpectedId": "ab"}, {"_PlainId"}, {"_FutureId"}) == []
