"""Define the track_calls helper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def track_calls(
    target: object,
    method: str,
    label: str,
    log: list[tuple[str, str]],
    key: Callable[[Any], str],
) -> None:
    """Wrap ``target.method`` so each call appends ``(label, key(arg))`` to ``log``."""
    original = getattr(target, method)

    def wrapper(arg: Any) -> Any:  # noqa: ANN401
        log.append((label, key(arg)))
        return original(arg)

    setattr(target, method, wrapper)
