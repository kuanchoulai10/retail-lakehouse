"""Define the GetPlatformSettingsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetPlatformSettingsUseCaseOutputItem:
    """One setting: a stable key, a label, its value and unit (none for a value that carries its own), a description."""

    key: str
    label: str
    value: int | float | str
    unit: str | None
    description: str


@dataclass(frozen=True)
class GetPlatformSettingsUseCaseOutputGroup:
    """One theme of settings: a stable key, a title and its items in reading order."""

    key: str
    title: str
    items: list[GetPlatformSettingsUseCaseOutputItem]


@dataclass(frozen=True)
class GetPlatformSettingsUseCaseOutput:
    """Carry every group of platform settings, in the order the console shows them."""

    groups: list[GetPlatformSettingsUseCaseOutputGroup]
