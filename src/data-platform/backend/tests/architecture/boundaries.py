"""Package boundaries of the backend, derived from the directory rules.

A boundary is a package whose ``__init__`` is the only entry point other
packages may import from. Boundaries do not nest: a module belongs to the
innermost boundary that contains it, and a parent's ``__all__`` does not
re-export its child boundaries.
"""

from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]

PROJECT_PACKAGES = ("application", "adapter", "base", "bootstrap")

AGGREGATE_LAYERS = (
    "application/domain/model",
    "application/domain/service",
    "application/port/inbound",
    "application/port/outbound",
    "application/service",
)
KERNEL_BOUNDARIES = (
    "base",
    "application/exceptions",
    "bootstrap/configs",
    "bootstrap/container",
)
HYBRID_SIDES = ("inbound", "outbound", "contracts")


def _packages(directory: Path) -> list[Path]:
    """Return the child packages (directories holding an ``__init__.py``)."""
    if not directory.is_dir():
        return []
    return sorted(
        child
        for child in directory.iterdir()
        if child.is_dir() and (child / "__init__.py").is_file()
    )


def _dotted(path: Path) -> str:
    return ".".join(path.relative_to(BACKEND).parts)


def _with_child_packages(package: Path) -> list[Path]:
    return [package, *_packages(package)]


def boundaries() -> set[str]:
    """Return every boundary as a dotted package name."""
    found: list[Path] = [BACKEND / kernel for kernel in KERNEL_BOUNDARIES]
    for layer in AGGREGATE_LAYERS:
        found.extend(_packages(BACKEND / layer))
    for channel in _packages(BACKEND / "adapter" / "inbound"):
        found.extend(_with_child_packages(channel))
    for aggregate in _packages(BACKEND / "adapter" / "outbound"):
        found.extend(_packages(aggregate))
    for tech in _packages(BACKEND / "adapter" / "hybrid"):
        for side in HYBRID_SIDES:
            if (tech / side / "__init__.py").is_file():
                found.extend(_with_child_packages(tech / side))
    return {_dotted(path) for path in found if (path / "__init__.py").is_file()}


def innermost_boundary(module: str, known: set[str] | None = None) -> str | None:
    """Return the innermost boundary containing ``module``, or None."""
    known = boundaries() if known is None else known
    parts = module.split(".")
    for end in range(len(parts), 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in known:
            return candidate
    return None
