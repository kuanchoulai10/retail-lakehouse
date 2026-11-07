"""Test the namespace use cases against the in-memory namespaces repo."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.namespace import (
    CreateNamespaceUseCaseInput,
    DeleteNamespaceUseCaseInput,
    GetNamespaceUseCaseInput,
    ListNamespacesUseCaseInput,
    UpdateNamespacePropertiesUseCaseInput,
)
from context.catalog.application.service.namespace import (
    CreateNamespaceService,
    DeleteNamespaceService,
    GetNamespaceService,
    ListNamespacesService,
    UpdateNamespacePropertiesService,
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from tests.context.catalog.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo


def _create(repo: InMemoryNamespacesRepo, namespace: list[str], properties: dict[str, str] | None = None):
    return CreateNamespaceService(repo).execute(
        CreateNamespaceUseCaseInput(catalog="sales", namespace=namespace, properties=properties or {})
    )


def test_create_namespace_with_properties(namespaces_repo: InMemoryNamespacesRepo):
    """Create returns the namespace with the properties it was given."""
    output = _create(namespaces_repo, ["raw"], {"owner": "data-eng"})

    assert (output.catalog, output.namespace, output.properties) == ("sales", ["raw"], {"owner": "data-eng"})
    assert namespaces_repo.items["sales\x1fraw"] == {"owner": "data-eng"}


@pytest.mark.parametrize("parts", [[], [""], ["a", " "]])
def test_namespace_id_from_parts_rejects_empty_or_blank_parts(parts: list[str]):
    """A namespace needs at least one part and none may be blank."""
    with pytest.raises(ValidationError):
        namespace_id_from_parts("sales", parts)


def test_namespace_id_from_parts_rejects_a_part_with_the_unit_separator():
    """U+001F joins the parts in a path, so it cannot be inside one."""
    with pytest.raises(ValidationError, match="U\\+001F"):
        namespace_id_from_parts("sales", ["a\x1fb"])


def test_namespace_id_from_parts_rejects_a_blank_catalog():
    """A blank catalog name is refused."""
    with pytest.raises(ValidationError):
        namespace_id_from_parts(" ", ["a"])


def test_namespace_id_from_parts_keeps_dots_and_spaces():
    """Dots and spaces are ordinary characters of a part."""
    assert namespace_id_from_parts("sales", ["a.b", "c d"]).parts == ("a.b", "c d")


def test_create_namespace_with_invalid_parts_saves_nothing(namespaces_repo: InMemoryNamespacesRepo):
    """A refused form never reaches the repo."""
    with pytest.raises(ValidationError):
        _create(namespaces_repo, [])

    assert namespaces_repo.items == {}


def test_create_existing_namespace_conflicts(namespaces_repo: InMemoryNamespacesRepo):
    """A taken namespace is a ConflictError from the repo."""
    _create(namespaces_repo, ["raw"])

    with pytest.raises(ConflictError):
        _create(namespaces_repo, ["raw"])


def test_namespace_part_with_dot_round_trips(namespaces_repo: InMemoryNamespacesRepo):
    """Create, get and list keep ``a.b`` as one part."""
    created = _create(namespaces_repo, ["a.b"], {"k": "v"})
    fetched = GetNamespaceService(namespaces_repo).execute(GetNamespaceUseCaseInput(catalog="sales", namespace=["a.b"]))
    listed = ListNamespacesService(namespaces_repo).execute(ListNamespacesUseCaseInput(catalog="sales", parent=[]))

    assert created.namespace == ["a.b"]
    assert fetched.namespace == ["a.b"]
    assert fetched.properties == {"k": "v"}
    assert [item.namespace for item in listed.items] == [["a.b"]]


def test_get_unknown_namespace_is_not_found(namespaces_repo: InMemoryNamespacesRepo):
    """Get raises NotFoundError for a namespace the catalog does not hold."""
    with pytest.raises(NotFoundError):
        GetNamespaceService(namespaces_repo).execute(GetNamespaceUseCaseInput(catalog="sales", namespace=["nope"]))


def test_list_namespaces_returns_direct_children(namespaces_repo: InMemoryNamespacesRepo):
    """Listing under a parent returns its children only, not grandchildren or other trees."""
    for namespace in (["a"], ["a", "b"], ["a", "b", "c"], ["z"]):
        _create(namespaces_repo, namespace)
    service = ListNamespacesService(namespaces_repo)

    top = service.execute(ListNamespacesUseCaseInput(catalog="sales", parent=[]))
    under_a = service.execute(ListNamespacesUseCaseInput(catalog="sales", parent=["a"]))

    assert [item.namespace for item in top.items] == [["a"], ["z"]]
    assert [item.namespace for item in under_a.items] == [["a", "b"]]
    assert all(item.catalog == "sales" for item in top.items)


def test_delete_namespace(namespaces_repo: InMemoryNamespacesRepo):
    """Delete removes an empty namespace."""
    _create(namespaces_repo, ["raw"])

    DeleteNamespaceService(namespaces_repo).execute(DeleteNamespaceUseCaseInput(catalog="sales", namespace=["raw"]))

    assert namespaces_repo.items == {}


def test_delete_non_empty_namespace_reports_the_repo_error(namespaces_repo: InMemoryNamespacesRepo):
    """A namespace that still has children is refused with the repo's message and is left alone."""
    _create(namespaces_repo, ["a"])
    _create(namespaces_repo, ["a", "b"])

    with pytest.raises(ConflictError, match="not empty"):
        DeleteNamespaceService(namespaces_repo).execute(DeleteNamespaceUseCaseInput(catalog="sales", namespace=["a"]))

    assert "sales\x1fa" in namespaces_repo.items


def test_delete_unknown_namespace_is_not_found(namespaces_repo: InMemoryNamespacesRepo):
    """Delete raises NotFoundError for an unknown namespace."""
    with pytest.raises(NotFoundError):
        DeleteNamespaceService(namespaces_repo).execute(DeleteNamespaceUseCaseInput(catalog="sales", namespace=["x"]))


def test_update_namespace_properties_sends_updates_and_removals(namespaces_repo: InMemoryNamespacesRepo):
    """Updates are set, removals are dropped, and the namespace comes back as saved."""
    _create(namespaces_repo, ["raw"], {"owner": "a", "stale": "x"})

    output = UpdateNamespacePropertiesService(namespaces_repo).execute(
        UpdateNamespacePropertiesUseCaseInput(
            catalog="sales", namespace=["raw"], updates={"owner": "b", "tier": "gold"}, removals=["stale"]
        )
    )

    assert output.properties == {"owner": "b", "tier": "gold"}
    assert output.namespace == ["raw"]


def test_update_namespace_properties_rejects_a_key_both_updated_and_removed(namespaces_repo: InMemoryNamespacesRepo):
    """A key in both lists is ambiguous, so it is refused before anything is saved."""
    _create(namespaces_repo, ["raw"], {"owner": "a"})

    with pytest.raises(ValidationError, match="owner"):
        UpdateNamespacePropertiesService(namespaces_repo).execute(
            UpdateNamespacePropertiesUseCaseInput(
                catalog="sales", namespace=["raw"], updates={"owner": "b"}, removals=["owner"]
            )
        )

    assert namespaces_repo.items["sales\x1fraw"] == {"owner": "a"}


def test_update_unknown_namespace_is_not_found(namespaces_repo: InMemoryNamespacesRepo):
    """Update raises NotFoundError for an unknown namespace."""
    with pytest.raises(NotFoundError):
        UpdateNamespacePropertiesService(namespaces_repo).execute(
            UpdateNamespacePropertiesUseCaseInput(catalog="sales", namespace=["x"], updates={"k": "v"})
        )
