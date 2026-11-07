"""Guard that the backend ruff configuration stays a thin layer over the root configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
FORBIDDEN_LINT_KEYS = {
    "ignore",
    "extend-ignore",
    "per-file-ignores",
    "extend-per-file-ignores",
    "select",
    "extend-select",
    "exclude",
    "extend-exclude",
}


def test_backend_ruff_config_only_extends_the_root():
    """The backend ruff table extends the root and neither ignores nor selects any rule."""
    ruff = tomllib.loads(PYPROJECT.read_text())["tool"]["ruff"]

    assert set(ruff) <= {"extend", "lint"}
    assert ruff["extend"] == "../../../ruff.toml"
    lint = ruff.get("lint", {})
    assert FORBIDDEN_LINT_KEYS.isdisjoint(lint)
    assert "context" in lint["isort"]["known-first-party"]
