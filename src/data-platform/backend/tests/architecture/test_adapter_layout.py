"""Guard test: adapter/ is split into inbound, outbound and hybrid technologies."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import context_dir, context_names
from tests.architecture.test_aggregate_axis import subdirs

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_DIRECTIONS = {"inbound", "outbound"}
HYBRID_SIDES = {"inbound", "outbound", "contracts"}


def adapter_top_level_violations(context_root: Path) -> list[str]:
    """Return the problems with the direction directories of ``adapter/``; hybrid is optional."""
    found = subdirs(context_root / "adapter")
    allowed = REQUIRED_DIRECTIONS | {"hybrid"}
    return [f"missing {name}" for name in sorted(REQUIRED_DIRECTIONS - found)] + [
        f"unexpected {name}" for name in sorted(found - allowed)
    ]


def hybrid_tech_violations(context_root: Path) -> list[str]:
    """Return each hybrid technology directory that does not hold exactly its three sides."""
    hybrid = context_root / "adapter" / "hybrid"
    if not hybrid.is_dir():
        return []
    return [
        f"{tech}: {sorted(subdirs(hybrid / tech))}"
        for tech in sorted(subdirs(hybrid))
        if subdirs(hybrid / tech) != HYBRID_SIDES
    ]


def _write(root: Path, *relatives: str) -> None:
    for relative in relatives:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")


@pytest.mark.parametrize("context", context_names())
def test_adapter_top_level(context: str):
    """The adapter directory of a context holds inbound and outbound, and hybrid only when it needs one."""
    assert adapter_top_level_violations(context_dir(context)) == []


@pytest.mark.parametrize("context", context_names())
def test_hybrid_tech_has_both_directions(context: str):
    """Each hybrid technology directory splits into an inbound and an outbound side."""
    assert hybrid_tech_violations(context_dir(context)) == []


def test_adapter_without_hybrid_is_allowed(tmp_path: Path):
    """An adapter with only web inbound and outbound passes both layout rules."""
    _write(tmp_path, "adapter/inbound/web/a.py", "adapter/outbound/b.py")
    assert adapter_top_level_violations(tmp_path) == []
    assert hybrid_tech_violations(tmp_path) == []


def test_hybrid_without_temporal_is_allowed(tmp_path: Path):
    """A hybrid technology other than Temporal passes when it holds the three sides."""
    _write(
        tmp_path,
        "adapter/inbound/web/a.py",
        "adapter/outbound/b.py",
        *(f"adapter/hybrid/queue/{side}/c.py" for side in sorted(HYBRID_SIDES)),
    )
    assert adapter_top_level_violations(tmp_path) == []
    assert hybrid_tech_violations(tmp_path) == []


def test_partial_temporal_dir_still_fails(tmp_path: Path):
    """A hybrid/temporal with only an inbound side is reported."""
    _write(tmp_path, "adapter/inbound/web/a.py", "adapter/outbound/b.py", "adapter/hybrid/temporal/inbound/c.py")
    assert hybrid_tech_violations(tmp_path) == ["temporal: ['inbound']"]


def test_missing_outbound_fails(tmp_path: Path):
    """An adapter without an outbound direction is reported."""
    _write(tmp_path, "adapter/inbound/web/a.py")
    assert adapter_top_level_violations(tmp_path) == ["missing outbound"]
