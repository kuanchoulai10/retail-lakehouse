"""Define the error_text function."""

from __future__ import annotations

MAX_ERROR_LENGTH = 4096
KEPT_MARKERS = ("OutOfMemoryError", "exit code 52")


def error_text(exc: BaseException) -> str:
    """Return the error a failed run reports, at most ``MAX_ERROR_LENGTH`` long.

    A long error is cut; when the cut drops the line that says the JVM ran out of memory, that
    line replaces the tail, so the control plane can still tell an out-of-memory failure.
    """
    text = f"{type(exc).__name__}: {exc}"
    head = text[:MAX_ERROR_LENGTH]
    if len(text) <= MAX_ERROR_LENGTH or any(marker in head for marker in KEPT_MARKERS):
        return head
    line = next((line for line in text.splitlines() if any(marker in line for marker in KEPT_MARKERS)), None)
    if line is None:
        return head
    kept = _around_marker(line, MAX_ERROR_LENGTH // 2)
    return f"{head[: MAX_ERROR_LENGTH - len(kept) - 1]}\n{kept}"


def _around_marker(line: str, budget: int) -> str:
    if len(line) <= budget:
        return line
    at = min(line.find(marker) for marker in KEPT_MARKERS if marker in line)
    start = max(0, min(at - budget // 2, len(line) - budget))
    return line[start : start + budget]
