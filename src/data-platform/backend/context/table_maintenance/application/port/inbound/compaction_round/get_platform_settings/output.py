"""Define the GetPlatformSettingsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetPlatformSettingsUseCaseOutput(UseCaseOutput):
    """Carry every group of platform settings, in the order the console shows them."""

    class Setting(UseCaseOutput):
        """One setting: a stable key, a label, its value and unit, and a description.

        ``unit`` is None for a value that carries its own.
        """

        key: str
        label: str
        value: int | float | str
        unit: str | None
        description: str

    class Group(UseCaseOutput):
        """One theme of settings: a stable key, a title and its items in reading order."""

        key: str
        title: str
        items: tuple[GetPlatformSettingsUseCaseOutput.Setting, ...]

    groups: tuple[Group, ...]
