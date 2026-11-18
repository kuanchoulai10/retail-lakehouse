"""The inbound port use cases of the backend, found from each context's ``port/inbound`` directory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.architecture.contexts import context_dir, context_names

if TYPE_CHECKING:
    from pathlib import Path

INBOUND_PORT_ROOTS = ("application", "port", "inbound")


def use_case_dirs() -> dict[str, Path]:
    """Return every use-case directory of every context, keyed ``"<context>/<aggregate>/<use_case>"``."""
    found: dict[str, Path] = {}
    for context in context_names():
        inbound = context_dir(context).joinpath(*INBOUND_PORT_ROOTS)
        for aggregate_dir in sorted(inbound.iterdir()):
            if not aggregate_dir.is_dir() or aggregate_dir.name == "__pycache__":
                continue
            for use_case_dir in sorted(aggregate_dir.iterdir()):
                if use_case_dir.is_dir() and use_case_dir.name != "__pycache__":
                    found[f"{context}/{aggregate_dir.name}/{use_case_dir.name}"] = use_case_dir
    return found
