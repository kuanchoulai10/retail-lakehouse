"""Pin the where clauses and procedure arguments a planned run sends to Spark.

The ``CALL`` the Spark runtime runs is built from exactly these two parts of ``GLAC_REQUEST``, so
they must stay the same, character for character and in their key order (the ``options`` map is
written in that order), whichever layer renders them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from context.table_maintenance.application.domain.service.table import build_partition_filters
from context.table_maintenance.application.service.table_maintenance_run import maintenance_procedure_args
from tests.context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_request_cases import (
    SPARK_REQUEST_CASES,
)

if TYPE_CHECKING:
    from tests.context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_request_cases import (
        SparkRequestCase,
    )

GOLDEN = Path(__file__).with_name("spark_request_golden.json")


def render(case: SparkRequestCase) -> dict[str, Any]:
    """Return the ``where`` and ``procedure_args`` of the request a run of ``case`` sends."""
    where = [f.where for f in build_partition_filters(case.catalog, case.specs, case.partitions)]
    return {
        "where": where,
        "procedure_args": maintenance_procedure_args(case.operation, case.policy, case.properties, case.now),
    }


def _golden() -> dict[str, Any]:
    return json.loads(GOLDEN.read_text())


def test_every_case_has_a_golden_request():
    """The golden file holds exactly the cases, no more and no fewer."""
    assert set(_golden()) == {case.name for case in SPARK_REQUEST_CASES}


@pytest.mark.parametrize("case", SPARK_REQUEST_CASES, ids=lambda case: case.name)
def test_the_request_matches_its_golden_copy(case: SparkRequestCase):
    """The rendered request equals the golden copy, key order of the options map included."""
    rendered = render(case)
    golden = _golden()[case.name]
    assert rendered == golden
    assert json.dumps(rendered) == json.dumps(golden)
