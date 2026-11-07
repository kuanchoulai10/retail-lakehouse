"""Build a throwaway context package under a temporary directory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path


def build_fixture_context(root: Path, files: dict[str, str]) -> str:
    """Write ``files`` under ``root/<unique name>/`` and return that package name.

    Each test gets its own top-level name, so no module cached in
    ``sys.modules`` by one test leaks into the next. Every directory on the
    way to a file gets an ``__init__.py``. The caller puts ``root`` on
    ``sys.path`` with ``monkeypatch.syspath_prepend``.
    """
    name = f"fixture_ctx_{uuid4().hex}"
    package = root / name
    for relative, source in files.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        directory = path.parent
        while directory != root:
            init = directory / "__init__.py"
            if not init.exists():
                init.write_text("")
            directory = directory.parent
    return name
