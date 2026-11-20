"""Test that the API's change kinds are exactly the domain's, and that a mismatch fails loudly."""

from __future__ import annotations

from typing import TYPE_CHECKING, get_args

import pytest

from context.catalog.adapter.inbound.web.table import (
    PartitionChangeCountsApiResponse,
    PartitionFieldComparisonApiResponse,
    SchemaChangeCountsApiResponse,
    SchemaFieldComparisonApiResponse,
)
from context.catalog.application.domain.model.table import PartitionChange, SchemaChange
from context.catalog.application.port.inbound.table import (
    ListTablePartitionSpecVersionsUseCaseOutput,
    ListTableSchemaVersionsUseCaseOutput,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client

if TYPE_CHECKING:
    from pydantic import BaseModel

BASE = "/v1/catalogs/sales/namespaces/retail/tables/orders"


def _literal_values(response: type[BaseModel], field: str) -> list[str]:
    (item,) = get_args(response.model_fields[field].annotation)
    return list(get_args(item))


def test_schema_change_kinds_are_the_domain_enum_in_order():
    """The comparison's change list and the version's counts name every SchemaChange, in enum order."""
    kinds = [kind.value for kind in SchemaChange]
    assert _literal_values(SchemaFieldComparisonApiResponse, "changes") == kinds
    assert list(SchemaChangeCountsApiResponse.model_fields) == kinds


def test_partition_change_kinds_are_the_domain_enum_in_order():
    """The comparison's change list and the version's counts name every PartitionChange, in enum order."""
    kinds = [kind.value for kind in PartitionChange]
    assert _literal_values(PartitionFieldComparisonApiResponse, "changes") == kinds
    assert list(PartitionChangeCountsApiResponse.model_fields) == kinds


SCHEMA_COUNTS = {kind.value: 0 for kind in SchemaChange}
PARTITION_COUNTS = {kind.value: 0 for kind in PartitionChange}


def _schema_versions(changes: dict[str, int]) -> ListTableSchemaVersionsUseCaseOutput:
    return ListTableSchemaVersionsUseCaseOutput(
        current_schema_id=1,
        items=(
            ListTableSchemaVersionsUseCaseOutput.Version(
                schema_id=1, previous_schema_id=0, current=True, column_count=2, changes=changes
            ),
        ),
    )


def _spec_versions(changes: dict[str, int]) -> ListTablePartitionSpecVersionsUseCaseOutput:
    return ListTablePartitionSpecVersionsUseCaseOutput(
        default_spec_id=1,
        items=(
            ListTablePartitionSpecVersionsUseCaseOutput.Version(
                spec_id=1, previous_spec_id=0, default=True, field_count=1, changes=changes
            ),
        ),
    )


@pytest.mark.parametrize(
    "changes",
    [SCHEMA_COUNTS | {"default_changed": 1}, {k: v for k, v in SCHEMA_COUNTS.items() if k != "doc_changed"}],
    ids=["a kind the API lacks", "a kind missing"],
)
def test_schema_version_counts_that_do_not_match_the_api_kinds_fail_loudly(changes: dict[str, int]):
    """A count the response cannot carry, or one it misses, is a server error naming the kind, never dropped."""
    client = build_client(list_table_schema_versions=StubUseCase(_schema_versions(changes)))

    with pytest.raises(TypeError, match="default_changed|doc_changed"):
        client.get(f"{BASE}/schema-versions")


@pytest.mark.parametrize(
    "changes",
    [PARTITION_COUNTS | {"sort_changed": 1}, {k: v for k, v in PARTITION_COUNTS.items() if k != "renamed"}],
    ids=["a kind the API lacks", "a kind missing"],
)
def test_partition_version_counts_that_do_not_match_the_api_kinds_fail_loudly(changes: dict[str, int]):
    """A count the response cannot carry, or one it misses, is a server error naming the kind, never dropped."""
    client = build_client(list_table_partition_spec_versions=StubUseCase(_spec_versions(changes)))

    with pytest.raises(TypeError, match="sort_changed|renamed"):
        client.get(f"{BASE}/partition-spec-versions")


def test_matching_counts_and_the_first_version_still_answer():
    """Counts naming exactly the API's kinds answer as before, and the first version's null counts stay null."""
    first = ListTableSchemaVersionsUseCaseOutput.Version(
        schema_id=0, previous_schema_id=None, current=False, column_count=1, changes=None
    )
    output = ListTableSchemaVersionsUseCaseOutput(
        current_schema_id=1, items=(*_schema_versions(SCHEMA_COUNTS).items, first)
    )

    body = build_client(list_table_schema_versions=StubUseCase(output)).get(f"{BASE}/schema-versions").json()

    assert [version["changes"] for version in body["versions"]] == [SCHEMA_COUNTS, None]
