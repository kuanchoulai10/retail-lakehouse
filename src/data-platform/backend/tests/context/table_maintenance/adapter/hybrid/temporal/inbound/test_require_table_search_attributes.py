"""Test require_table_search_attributes against a local Temporal dev server."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from temporalio.common import SearchAttributeKey

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import TableSearchAttribute
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    MissingTableSearchAttributes,
    require_table_search_attributes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
    harness,  # noqa: F401
)

if TYPE_CHECKING:
    from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
        TemporalHarness,
    )


def test_passes_when_every_table_search_attribute_is_registered(harness: TemporalHarness):  # noqa: F811
    """The dev server registers every table attribute, as wave 21 does, so the worker may start."""
    harness.bridge.run(lambda: require_table_search_attributes(harness.client))


def test_names_a_missing_attribute_and_the_wave_that_registers_it(harness: TemporalHarness):  # noqa: F811
    """An attribute the namespace lacks stops the worker with a message that says what to run."""
    missing = SearchAttributeKey.for_keyword_list("NotRegisteredAnywhere")

    with pytest.raises(
        MissingTableSearchAttributes, match=r"NotRegisteredAnywhere.*platform/21-temporal/bootstrap\.sh"
    ):
        harness.bridge.run(lambda: require_table_search_attributes(harness.client, required=(missing,)))


def test_names_an_attribute_registered_with_another_type(harness: TemporalHarness):  # noqa: F811
    """An attribute registered as a keyword where a keyword list is needed is refused too."""
    wrong = SearchAttributeKey.for_keyword_list(TableSearchAttribute.TABLE_UUID)

    with pytest.raises(MissingTableSearchAttributes, match=r"TableUuid \(KeywordList, registered as Keyword\)"):
        harness.bridge.run(lambda: require_table_search_attributes(harness.client, required=(wrong,)))
