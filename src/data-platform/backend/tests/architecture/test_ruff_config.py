"""Guard that the backend ruff configuration stays a thin layer over the root configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel

import base

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
ALLOWED_LINT_SECTIONS = {"isort", "flake8-type-checking"}


def test_backend_ruff_config_only_extends_the_root():
    """The backend ruff table extends the root and adds only the isort and type-checking settings.

    Any other lint key (ignore, select, per-file-ignores, a threshold table such as mccabe or
    pylint) is rejected, so the root `ruff.toml` stays the single source of rules.
    """
    ruff = tomllib.loads(PYPROJECT.read_text())["tool"]["ruff"]

    assert set(ruff) <= {"extend", "lint"}
    assert ruff["extend"] == "../../../ruff.toml"
    lint = ruff.get("lint", {})
    assert set(lint) <= ALLOWED_LINT_SECTIONS
    assert "context" in lint["isort"]["known-first-party"]


def test_every_pydantic_base_is_runtime_evaluated():
    """Every Pydantic model base ``base`` exports is a ruff runtime-evaluated base class.

    Pydantic reads field annotations at runtime, so ruff must not move a field type's import (``datetime``)
    under ``TYPE_CHECKING`` in a subclass.
    """
    lint = tomllib.loads(PYPROJECT.read_text())["tool"]["ruff"]["lint"]
    listed = set(lint["flake8-type-checking"]["runtime-evaluated-base-classes"])
    model_bases = {
        f"base.{name}"
        for name in base.__all__
        if isinstance(getattr(base, name), type) and issubclass(getattr(base, name), BaseModel)
    }
    assert model_bases
    assert model_bases - listed == set()
