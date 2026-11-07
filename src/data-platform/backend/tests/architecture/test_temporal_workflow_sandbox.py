"""Every workflow the worker registers passes Temporal's sandbox validation.

The sandbox re-imports each workflow's module, with its parent packages, under
its import restrictions; ``prepare_workflow`` is the check the worker runs at
start-up, so a boundary ``__init__`` that pulls a restricted import into a
workflow package fails here instead of at worker start.
"""

from __future__ import annotations

import asyncio
import importlib
from types import ModuleType

import pytest
from temporalio import workflow
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from bootstrap.container import WORKFLOWS
from tests.architecture.contexts import context_dir, context_module, context_names

WORKFLOWS_PACKAGE = ("adapter", "hybrid", "temporal", "inbound", "workflows")


def _workflow_packages() -> list[ModuleType]:
    """Import the Temporal workflows package of every context that has one."""
    return [
        importlib.import_module(".".join((context_module(name), *WORKFLOWS_PACKAGE)))
        for name in context_names()
        if (context_dir(name).joinpath(*WORKFLOWS_PACKAGE) / "__init__.py").is_file()
    ]


def _workflow_definitions_in_package() -> set[type]:
    values = (getattr(package, name) for package in _workflow_packages() for name in package.__all__)
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
