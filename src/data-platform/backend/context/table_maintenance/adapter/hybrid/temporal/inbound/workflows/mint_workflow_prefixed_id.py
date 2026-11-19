"""Define mint_workflow_prefixed_id, which mints a prefixed id inside a workflow."""

from __future__ import annotations

from temporalio import workflow

from shared_kernel import prefixed_id_from_parts

_RANDOM_BITS = 74


def mint_workflow_prefixed_id(prefix: str) -> str:
    """Mint a ``<prefix>-`` id (docs/adr/0011) from the workflow clock and random, so replay mints it again."""
    return prefixed_id_from_parts(
        prefix, int(workflow.now().timestamp() * 1000), workflow.random().getrandbits(_RANDOM_BITS)
    )
