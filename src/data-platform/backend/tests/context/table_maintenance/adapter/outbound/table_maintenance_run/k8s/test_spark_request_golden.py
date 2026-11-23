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

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    iceberg_procedure_args,
    spark_where_clauses,
)
from context.table_maintenance.application.domain.service.table import group_partitions_by_spec
from context.table_maintenance.application.domain.service.table_maintenance_run import build_maintenance_job_content
from context.table_maintenance.application.service.table_maintenance_run import gateway_job_of
from tests.context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_request_cases import (
    SPARK_REQUEST_CASES,
)

if TYPE_CHECKING:
    from tests.context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_request_cases import (
        SparkRequestCase,
    )

GOLDEN = Path(__file__).with_name("spark_request_golden.json")


def render(case: SparkRequestCase) -> dict[str, Any]:
    """Return the ``where`` and ``procedure_args`` of the request a run of ``case`` sends.

    The path is the one a run takes: the plan groups the partitions and builds the content, the
    submit turns it into the port's job, and the Spark adapter writes the call's two parts.
    """
    partitions = group_partitions_by_spec(case.specs, case.partitions)
    job = gateway_job_of(
        build_maintenance_job_content(case.operation, case.policy, case.properties, case.now, partitions)
    )
    return {"where": spark_where_clauses(case.catalog, job), "procedure_args": iceberg_procedure_args(job)}


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
