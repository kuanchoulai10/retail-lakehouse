"""The bounded contexts of the backend, found from the ``context/`` directory."""

from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
CONTEXT_ROOT = BACKEND / "context"


def context_names() -> list[str]:
    """Return the sorted names of the packages under ``context/``."""
    return sorted(
        child.name
        for child in CONTEXT_ROOT.iterdir()
        if child.is_dir() and (child / "__init__.py").is_file()
    )


def context_dir(name: str) -> Path:
    """Return the directory of the context ``name``."""
    return CONTEXT_ROOT / name


def context_module(name: str) -> str:
    """Return the dotted package of the context ``name``."""
    return f"context.{name}"
