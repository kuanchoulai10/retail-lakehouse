"""Define the SettingsBlock base model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SettingsBlock(BaseModel):
    """A group of settings inside a role's settings; a key it does not know is refused, not ignored."""

    model_config = ConfigDict(extra="forbid")
