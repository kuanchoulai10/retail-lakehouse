from __future__ import annotations

from pathlib import Path

RUNTIME = Path(__file__).parent.parent


def test_image_copies_every_runtime_module():
    copy = next(line for line in (RUNTIME / "Dockerfile").read_text().splitlines() if line.startswith("COPY "))
    copied = set(copy.split()[1:-1])
    assert copied == {path.name for path in RUNTIME.glob("*.py")}
