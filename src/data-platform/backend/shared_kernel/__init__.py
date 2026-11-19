"""Shared kernel: code that both ``base`` and Temporal workflow contracts need.

Stdlib only. It imports no other project package and no third-party package, because Temporal workflows
(which may not import ``base`` or Pydantic) and ``base`` itself both use it. See docs/adr/0011.
"""

from __future__ import annotations

from shared_kernel.new_prefixed_id import new_prefixed_id
from shared_kernel.prefixed_id_from_parts import prefixed_id_from_parts
from shared_kernel.prefixed_id_pattern import prefixed_id_pattern

__all__ = ["new_prefixed_id", "prefixed_id_from_parts", "prefixed_id_pattern"]
