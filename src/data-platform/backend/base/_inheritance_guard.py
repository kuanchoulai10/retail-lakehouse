"""Internal helper: enforce a maximum inheritance depth at subclass creation.

Used by base classes whose ``__init_subclass__`` enforces DDD depth limits
(see ``tests/architecture/test_inheritance_depth.py`` for the same contract
applied as a static guard test).
"""

from __future__ import annotations


def _is_parametrization(cls: type) -> bool:
    """Return whether ``cls`` is a Pydantic generic parametrization such as ``Entity[TableId]``.

    Pydantic builds ``Entity[TableId]`` as a real subclass of ``Entity``;
    it is the generic itself with its type argument filled in, not a layer
    of the hierarchy, so it does not count towards the depth.
    """
    metadata = getattr(cls, "__pydantic_generic_metadata__", None)
    return bool(metadata and metadata.get("origin") is not None)


def enforce_max_depth(cls: type, base: type, max_depth: int) -> None:
    """Raise ``TypeError`` if ``cls`` is more than ``max_depth`` layers below ``base``.

    Walks up the first ``base``-relevant parent at each step. ``class B(A)``
    is depth 1 from ``A``; ``class C(B)`` is depth 2 from ``A``. If any
    inheritance path exceeds ``max_depth``, the subclass is rejected — DDD
    base classes do not use multiple inheritance, so a single-path walk is
    sufficient and any deep path indicates an over-engineered hierarchy.
    Pydantic generic parametrizations on the path are not counted.
    """
    depth = 0
    current = cls
    while True:
        relevant = [b for b in current.__bases__ if issubclass(b, base)]
        if not relevant:
            break
        if not _is_parametrization(current):
            depth += 1
        current = relevant[0]
    if depth > max_depth:
        raise TypeError(f"{cls.__qualname__} exceeds {base.__name__} max inheritance depth ({depth} > {max_depth})")
