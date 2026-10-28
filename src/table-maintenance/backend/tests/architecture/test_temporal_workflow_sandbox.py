"""Every workflow the worker registers passes Temporal's sandbox validation.

The sandbox re-imports each workflow's module, with its parent packages, under
its import restrictions; ``prepare_workflow`` is the check the worker runs at
start-up, so a boundary ``__init__`` that pulls a restricted import into a
workflow package fails here instead of at worker start.
"""

from __future__ import annotations

import asyncio

import pytest
from temporalio import workflow
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

import adapter.hybrid.temporal.inbound.workflows as workflows_package
from bootstrap.container import WORKFLOWS


def _workflow_definitions_in_package() -> set[type]:
    values = (getattr(workflows_package, name) for name in workflows_package.__all__)
    return {
        value
        for value in values
        if isinstance(value, type) and workflow._Definition.from_class(value)  # noqa: SLF001
    }


def test_worker_registers_every_workflow():
    assert set(WORKFLOWS) == _workflow_definitions_in_package()


@pytest.mark.parametrize("workflow_class", WORKFLOWS, ids=lambda cls: cls.__name__)
def test_workflow_passes_sandbox_validation(workflow_class: type):
    definition = workflow._Definition.must_from_class(workflow_class)  # noqa: SLF001

    async def prepare() -> None:
        # The workflow instance binds to the running loop, as it does in the worker.
        SandboxedWorkflowRunner().prepare_workflow(definition)

    asyncio.run(prepare())
