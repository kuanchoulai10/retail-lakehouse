"""Bulk-rewrite imports for the core/api/scheduler restructure.

Usage: python scripts/rewrite_imports.py <phase> [root_dir]
Phases: base, configs, application, outbound, inbound, deps, scheduler
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RULES: dict[str, list[tuple[str, str]]] = {
    "base": [
        (r"\bfrom base\.", "from core.base."),
        (r"\bfrom base import\b", "from core.base import"),
    ],
    "configs": [
        (r"\bfrom configs\.", "from core.configs."),
        (r"\bfrom configs import\b", "from core.configs import"),
    ],
    "application": [
        (r"\bfrom application\.", "from core.application."),
        (r"\bfrom application import\b", "from core.application import"),
    ],
    "outbound": [
        (r"\bfrom adapter\.outbound\.", "from core.adapter.outbound."),
    ],
    "inbound": [
        (r"\bfrom adapter\.inbound\.", "from api.adapter.inbound."),
        (r"\bfrom adapter\.inbound import\b", "from api.adapter.inbound import"),
    ],
    "deps": [
        (r"\bfrom dependencies\.", "from api.dependencies."),
        (r"\bfrom dependencies import\b", "from api.dependencies import"),
    ],
    "scheduler": [
        (r"\bfrom scheduler_loop import\b", "from scheduler.scheduler_loop import"),
    ],
}

SKIP_PARTS = {".venv", "__pycache__", ".ruff_cache", ".pytest_cache"}


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <phase> [root_dir]")
        sys.exit(1)

    phase = sys.argv[1]
    if phase not in RULES:
        print(f"Unknown phase: {phase!r}. Available: {', '.join(RULES)}")
        sys.exit(1)

    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    rules = RULES[phase]
    updated = 0

    for path in sorted(root.rglob("*.py")):
        if SKIP_PARTS & set(path.parts):
            continue
        text = path.read_text()
        original = text
        for pattern, replacement in rules:
            text = re.sub(pattern, replacement, text)
        if text != original:
            path.write_text(text)
            print(f"  updated: {path}")
            updated += 1

    print(f"\n{phase}: {updated} file(s) updated.")


if __name__ == "__main__":
    main()
