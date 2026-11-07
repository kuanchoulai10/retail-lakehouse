"""Neutral Temporal contracts shared by inbound workflows and outbound clients.

Each workflow has its own package holding its type name, ID, input, the signals
it receives, the activities it calls and its static summary; ``shared`` holds
what every workflow uses.
"""

from __future__ import annotations

__all__ = []
