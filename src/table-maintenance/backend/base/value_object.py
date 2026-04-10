from __future__ import annotations

from abc import ABC

from pydantic import BaseModel


class ValueObject(ABC, BaseModel, frozen=True):
    """Immutable object defined by its attributes, not by identity."""
