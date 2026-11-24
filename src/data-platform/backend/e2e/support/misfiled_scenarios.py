"""Provide misfiled_scenarios, which finds the scenarios no e2e run would select."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

KINDS = frozenset({"critical", "full"})


def misfiled_scenarios(scenarios: Iterable[tuple[str, set[str]]]) -> list[str]:
    """Name each scenario (``node id``, ``marker names``) that is not exactly one of ``critical`` and ``full``."""
    problems: list[str] = []
    for node_id, markers in scenarios:
        kinds = KINDS & markers
        if not kinds:
            problems.append(f"{node_id} has no kind")
        elif len(kinds) > 1:
            problems.append(f"{node_id} is both critical and full")
    return problems
